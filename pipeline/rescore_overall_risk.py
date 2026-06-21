"""Re-score dữ liệu cũ sau khi sửa Waterfall (fraud không còn ép lên P5).

Bối cảnh: trước đây `calculate_overall_risk` đưa risk_fraud>=8 lên P5, và router
ép mọi P5 về team Safety -> ticket Payment/gian lận bị gắn nhãn Safety sai.
Đã sửa scoring_agent: chỉ risk_safety>=8 mới lên P5. Script này áp lại logic mới
cho DỮ LIỆU CŨ:

  Phase A — feedback: tính lại overall_risk TỪ 5 điểm rủi ro ĐÃ LƯU (không gọi
            LLM, hoàn toàn xác định). Cập nhật row nào lệch.
  Phase B — alerts:  re-route các ticket đang mở bị đẩy nhầm sang team Safety
            (assigned_team='Safety' nhưng topic KHÔNG phải Safety). Hạ severity
            về P4 và định tuyến lại theo topic.

MẶC ĐỊNH chạy dry-run (chỉ in ra thay đổi). Thêm --apply để ghi vào DB.

Cách chạy (trong thư mục pipeline/):
    python rescore_overall_risk.py            # xem trước, không ghi
    python rescore_overall_risk.py --apply    # ghi thật
    python rescore_overall_risk.py --apply --skip-alerts   # chỉ re-score feedback
"""

from __future__ import annotations

import argparse

from ingest import get_supabase
from agents.scoring_agent import calculate_overall_risk
from agents.router_agent import route_ticket

PAGE = 1000
RISK_FIELDS = ("risk_safety", "risk_fraud", "risk_attitude", "risk_vehicle", "risk_compliance")


def _fetch_all(db, table: str, columns: str, build_query):
    """Phân trang qua toàn bộ bảng (Supabase trả tối đa 1000 row/request)."""
    rows: list[dict] = []
    start = 0
    while True:
        q = build_query(db.table(table).select(columns)).range(start, start + PAGE - 1)
        batch = q.execute().data or []
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        start += PAGE
    return rows


def rescore_feedback(db, apply: bool) -> dict:
    """Phase A: tính lại overall_risk cho feedback đã chấm, từ điểm rủi ro đã lưu."""
    cols = "id,overall_risk," + ",".join(RISK_FIELDS)
    rows = _fetch_all(
        db, "feedback", cols,
        lambda q: q.not_.is_("overall_risk", "null"),
    )

    changed = []
    for r in rows:
        new_risk = calculate_overall_risk(
            int(r.get("risk_safety") or 0),
            int(r.get("risk_fraud") or 0),
            int(r.get("risk_attitude") or 0),
            int(r.get("risk_vehicle") or 0),
            int(r.get("risk_compliance") or 0),
        )
        old_risk = int(r.get("overall_risk") or 0)
        if new_risk != old_risk:
            changed.append((r["id"], old_risk, new_risk))

    print(f"\n=== Phase A — feedback ===")
    print(f"Đã chấm: {len(rows)} | cần đổi overall_risk: {len(changed)}")
    demoted_p5 = sum(1 for _, o, n in changed if o == 5 and n < 5)
    print(f"  trong đó P5 -> thấp hơn (chủ yếu fraud): {demoted_p5}")
    for fid, o, n in changed[:10]:
        print(f"    feedback {fid}: P{o} -> P{n}")
    if len(changed) > 10:
        print(f"    ... và {len(changed) - 10} row khác")

    if apply and changed:
        for fid, _o, n in changed:
            db.table("feedback").update({"overall_risk": n}).eq("id", fid).execute()
        print(f"  [APPLIED] cập nhật {len(changed)} feedback.")
    elif changed:
        print("  [DRY-RUN] chưa ghi. Thêm --apply để cập nhật.")

    return {"scored": len(rows), "changed": len(changed), "demoted_p5": demoted_p5}


def reroute_alerts(db, apply: bool) -> dict:
    """Phase B: re-route alert đang mở bị ép nhầm về Safety (topic != Safety)."""
    rows = _fetch_all(
        db, "alerts", "id,title,topic,assigned_team,severity,priority,area,status,ticket_type",
        lambda q: q.in_("status", ["open", "in_progress"]).eq("assigned_team", "Safety"),
    )

    # Bị đẩy nhầm = team Safety nhưng topic không phải Safety (và có topic rõ).
    mislabeled = [r for r in rows if (r.get("topic") or "").strip() not in ("", "Safety")]

    print(f"\n=== Phase B — alerts ===")
    print(f"Alert team=Safety đang mở: {len(rows)} | bị đẩy nhầm (topic != Safety): {len(mislabeled)}")

    changes = []
    for r in mislabeled:
        topic = r["topic"]
        # Topic phi-an-toàn không thể là P5 theo luật mới -> hạ về P4, định tuyến lại theo topic.
        route = route_ticket(topic, "P4", "negative", log_run=False)
        new_team = route["team"]
        new_prio = route.get("priority") or "P4"
        changes.append((r["id"], r.get("title", "")[:40], topic, r.get("assigned_team"),
                        new_team, r.get("severity"), new_prio))

    for cid, title, topic, old_team, new_team, old_sev, new_prio in changes[:15]:
        print(f"    alert {cid} [{topic}] {old_team} {old_sev} -> {new_team} {new_prio} | {title}")
    if len(changes) > 15:
        print(f"    ... và {len(changes) - 15} alert khác")

    if apply and changes:
        for cid, _t, _topic, _ot, new_team, _os, new_prio in changes:
            db.table("alerts").update({
                "assigned_team": new_team,
                "severity": new_prio,
                "priority": new_prio,
            }).eq("id", cid).execute()
        print(f"  [APPLIED] re-route {len(changes)} alert.")
    elif changes:
        print("  [DRY-RUN] chưa ghi. Thêm --apply để cập nhật.")

    return {"safety_open": len(rows), "rerouted": len(changes)}


def main():
    parser = argparse.ArgumentParser(description="Re-score overall_risk + re-route alert cũ sau khi sửa Waterfall.")
    parser.add_argument("--apply", action="store_true", help="Ghi thật vào DB (mặc định dry-run).")
    parser.add_argument("--skip-alerts", action="store_true", help="Chỉ re-score feedback, bỏ qua Phase B.")
    args = parser.parse_args()

    mode = "APPLY (ghi thật)" if args.apply else "DRY-RUN (chỉ xem)"
    print(f"Chế độ: {mode}")

    db = get_supabase()
    a = rescore_feedback(db, args.apply)
    b = {"safety_open": 0, "rerouted": 0}
    if not args.skip_alerts:
        b = reroute_alerts(db, args.apply)

    print("\n=== Tổng kết ===")
    print(f"Feedback đổi overall_risk: {a['changed']} (P5->thấp: {a['demoted_p5']})")
    print(f"Alert re-route khỏi Safety: {b['rerouted']}")
    if not args.apply and (a["changed"] or b["rerouted"]):
        print("\nĐây là DRY-RUN. Chạy lại với --apply để ghi thay đổi.")


if __name__ == "__main__":
    main()

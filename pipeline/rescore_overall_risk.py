"""Re-score dữ liệu cũ sau khi sửa Waterfall (fraud không còn ép lên P5).

Bối cảnh: trước đây `calculate_overall_risk` đưa risk_fraud>=8 lên P5, và router
ép mọi P5 về team Safety -> ticket Payment/gian lận bị gắn nhãn Safety sai.
Đã sửa scoring_agent: chỉ risk_safety>=8 mới lên P5. Script này áp lại logic mới
cho DỮ LIỆU CŨ:

  Phase A — feedback: tính lại overall_risk TỪ 5 điểm rủi ro ĐÃ LƯU (không gọi
            LLM, hoàn toàn xác định). Cập nhật row nào lệch.
  Phase B — alerts:  re-route MỌI ticket đang mở có assigned_team='Safety' sang
            routing mới (không còn team Safety nhận routing tự động).
            - topic != Safety: bị ép nhầm lên P5/Safety -> hạ P4, route theo topic.
            - topic == Safety: sự cố an toàn thật -> giữ severity gốc, P5 override
              chuyển sang team Vận hành (đội phản ứng nhanh).

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


def _effective_severity(row: dict) -> int:
    """Mức severity mà spike_detector THỰC SỰ đọc: overall_risk trước, fallback severity."""
    ov = row.get("overall_risk")
    try:
        ov_int = int(ov)
        if 1 <= ov_int <= 5:
            return ov_int
    except (TypeError, ValueError):
        pass
    try:
        return int(str(row.get("severity") or "P3").upper().lstrip("P"))
    except (TypeError, ValueError):
        return 0


def rescore_feedback(db, apply: bool) -> dict:
    """Phase A: tính lại risk cho MỌI feedback negative ĐÃ CHẤM, từ risk_* đã lưu.

    Ghi lại CẢ overall_risk LẪN severity, vì hai đường nhập lưu khác nhau:
    - ingest.py (seed/bulk): severity='P{overall_risk}' rồi POP overall_risk
      => overall_risk NULL, severity='P5'; spike_detector fallback đúng vào severity.
    - app trực tiếp (main.py): severity=classifier, overall_risk do ml-worker set.
    Nếu chỉ sửa overall_risk (như bản cũ) sẽ BỎ SÓT đám seed severity='P5'.
    """
    cols = "id,sentiment,severity,overall_risk," + ",".join(RISK_FIELDS)
    rows = _fetch_all(
        db, "feedback", cols,
        lambda q: q.eq("sentiment", "negative"),
    )

    changed = []
    for r in rows:
        dims = [int(r.get(f) or 0) for f in RISK_FIELDS]
        # Chỉ đụng row ĐÃ chấm (có overall_risk hoặc ít nhất 1 điểm risk > 0) —
        # tránh ép feedback negative chưa chấm về P1.
        scored = r.get("overall_risk") is not None or any(d > 0 for d in dims)
        if not scored:
            continue
        new_risk = calculate_overall_risk(*dims)
        new_sev = f"P{new_risk}"
        cur_eff = _effective_severity(r)
        cur_sev = str(r.get("severity") or "")
        if new_risk != cur_eff or cur_sev != new_sev:
            changed.append((r["id"], cur_eff, new_risk))

    print("\n=== Phase A — feedback ===")
    print(f"Negative đã chấm: ~{len(rows)} | cần sửa: {len(changed)}")
    demoted_p5 = sum(1 for _, o, n in changed if o == 5 and n < 5)
    print(f"  trong đó P5 -> thấp hơn (chủ yếu fraud): {demoted_p5}")
    for fid, o, n in changed[:10]:
        print(f"    feedback {fid}: P{o} -> P{n} (ghi cả overall_risk + severity)")
    if len(changed) > 10:
        print(f"    ... và {len(changed) - 10} row khác")

    if apply and changed:
        for fid, _o, n in changed:
            db.table("feedback").update(
                {"overall_risk": n, "severity": f"P{n}"}
            ).eq("id", fid).execute()
        print(f"  [APPLIED] cập nhật {len(changed)} feedback (overall_risk + severity).")
    elif changed:
        print("  [DRY-RUN] chưa ghi. Thêm --apply để cập nhật.")

    return {"scored": len(rows), "changed": len(changed), "demoted_p5": demoted_p5}


def reroute_alerts(db, apply: bool) -> dict:
    """Phase B: re-route MỌI alert đang mở có assigned_team='Safety' sang routing mới.

    Chính sách mới: không còn team Safety nhận routing tự động.
    - topic != 'Safety': bị ép nhầm lên P5/Safety trước đây -> hạ về P4 (để vượt
      qua override P5) rồi định tuyến lại theo topic.
    - topic == 'Safety': sự cố an toàn thật -> giữ severity gốc; override P5 đưa
      sang team Vận hành (đội phản ứng nhanh).
    """
    rows = _fetch_all(
        db, "alerts", "id,title,topic,assigned_team,severity,priority,area,status,ticket_type",
        lambda q: q.in_("status", ["open", "in_progress"]).eq("assigned_team", "Safety"),
    )

    print(f"\n=== Phase B — alerts ===")
    print(f"Alert team=Safety đang mở: {len(rows)} (re-route toàn bộ theo routing mới)")

    changes = []
    for r in rows:
        topic = (r.get("topic") or "").strip() or "Other"
        if topic == "Safety":
            # Sự cố an toàn thật: giữ severity gốc, để override quyết định team (-> Vận hành).
            sev_in = r.get("severity") or "P5"
            route = route_ticket(topic, sev_in, "negative", log_run=False)
            new_prio = route.get("priority") or sev_in
        else:
            # Topic phi-an-toàn bị ép nhầm P5/Safety -> hạ về P4, định tuyến lại theo topic.
            route = route_ticket(topic, "P4", "negative", log_run=False)
            new_prio = route.get("priority") or "P4"
        new_team = route["team"]
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

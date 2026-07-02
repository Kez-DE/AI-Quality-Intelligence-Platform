"""Xác thực bearer token cho HTTP MCP server.

Token chỉ là credential gắn với `user_id`. Quyền (role, phòng) được resolve **LIVE** từ
bảng `profiles` mỗi request — nên khi admin nâng quyền / gán phòng cho tài khoản, token cũ
tự phản ánh, KHÔNG cần cấp lại.

Ánh xạ profile → identity MCP:
- role admin                          → (admin, None)      : toàn hệ thống
- role manager/staff + có department  → (role, department) : scoped đúng phòng
- role manager/staff + CHƯA có phòng  → (guest, None)      : chỉ submit_feedback
- role guest                          → (guest, None)      : chỉ submit_feedback
- không tìm thấy profile              → None               : từ chối
"""
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, TypedDict


class Identity(TypedDict):
    role: str
    scope_team: Optional[str]


def hash_token(raw: str) -> str:
    """SHA-256 hex của token thô. Deterministic — dùng để tra và để lưu."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _identity_from_profile(role: Optional[str], department: Optional[str]) -> Identity:
    """Ánh xạ (role, department) của profile → identity MCP. Đóng an toàn:
    ops thiếu phòng KHÔNG được toàn hệ thống mà tụt về guest."""
    role = (role or "").strip().lower()
    dept = (department or "").strip() or None
    if role == "admin":
        return {"role": "admin", "scope_team": None}
    if role in ("manager", "staff") and dept:
        return {"role": role, "scope_team": dept}
    # guest, hoặc nhân viên chưa được gán phòng → chỉ submit_feedback
    return {"role": "guest", "scope_team": None}


def verify_token(raw: str, db=None) -> Optional[Identity]:
    """Trả identity resolve LIVE từ profiles nếu token active + có chủ, ngược lại None."""
    if not raw:
        return None
    if db is None:
        from agents.common import get_db
        db = get_db()
    th = hash_token(raw)
    try:
        rows = (
            db.table("mcp_tokens")
            .select("id,user_id")
            .eq("token_hash", th)
            .eq("active", True)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return None
    if not rows or not rows[0].get("user_id"):
        return None
    token_id = rows[0]["id"]
    user_id = rows[0]["user_id"]

    try:
        profs = (
            db.table("profiles")
            .select("role,department")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return None
    if not profs:
        return None

    ident = _identity_from_profile(profs[0].get("role"), profs[0].get("department"))
    # last_used_at best-effort
    try:
        db.table("mcp_tokens").update(
            {"last_used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", token_id).execute()
    except Exception:
        pass
    return ident


def issue_token(user_id: str, label: str = "", db=None) -> str:
    """Phát token mới gắn với user_id. Trả token THÔ (chỉ hiện một lần). Quyền theo
    profile của user, resolve live khi verify — không lưu role/phòng ở đây."""
    if not user_id:
        raise ValueError("user_id là bắt buộc")
    if db is None:
        from agents.common import get_db
        db = get_db()
    raw = secrets.token_urlsafe(32)
    db.table("mcp_tokens").insert({
        "token_hash": hash_token(raw),
        "user_id": user_id,
        "label": label,
    }).execute()
    return raw


if __name__ == "__main__":
    # CLI phát token cho một user: python mcp_auth.py <user_id> [label]
    import sys
    if len(sys.argv) < 2:
        print("usage: python mcp_auth.py <user_id> [label]")
        raise SystemExit(1)
    print(issue_token(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "cli"))

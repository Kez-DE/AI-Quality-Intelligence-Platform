"""Xác thực bearer token cho HTTP MCP server: token thô → (role, scope_team).

Không lưu token thô — chỉ lưu SHA-256. `verify_token` tra bảng mcp_tokens (service
role), trả identity nếu token active. `issue_token` phát token mới (admin util).
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


def verify_token(raw: str, db=None) -> Optional[Identity]:
    """Trả {role, scope_team} nếu token hợp lệ và active, ngược lại None.

    db: Supabase client (mặc định lấy service-role client). Cho phép inject để test.
    """
    if not raw:
        return None
    if db is None:
        from agents.common import get_db
        db = get_db()
    th = hash_token(raw)
    try:
        rows = (
            db.table("mcp_tokens")
            .select("id,role,scope_team,active")
            .eq("token_hash", th)
            .eq("active", True)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return None
    if not rows:
        return None
    row = rows[0]
    # cập nhật last_used_at best-effort, không chặn nếu lỗi
    try:
        db.table("mcp_tokens").update(
            {"last_used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", row["id"]).execute()
    except Exception:
        pass
    return {"role": row["role"], "scope_team": row.get("scope_team")}


def issue_token(role: str, scope_team: Optional[str], label: str = "", db=None) -> str:
    """Phát token mới, lưu hash + metadata, trả token THÔ (chỉ hiện một lần)."""
    if role not in ("admin", "manager", "staff", "guest"):
        raise ValueError(f"role không hợp lệ: {role}")
    if role in ("staff", "manager") and not scope_team:
        raise ValueError("staff/manager bắt buộc có scope_team")
    if role in ("admin", "guest"):
        scope_team = None
    if db is None:
        from agents.common import get_db
        db = get_db()
    raw = secrets.token_urlsafe(32)
    db.table("mcp_tokens").insert({
        "token_hash": hash_token(raw),
        "label": label,
        "role": role,
        "scope_team": scope_team,
    }).execute()
    return raw


if __name__ == "__main__":
    # CLI phát token: python mcp_auth.py <role> [scope_team] [label]
    import sys
    _role = sys.argv[1] if len(sys.argv) > 1 else "guest"
    _scope = sys.argv[2] if len(sys.argv) > 2 else None
    _label = sys.argv[3] if len(sys.argv) > 3 else "cli"
    print(issue_token(_role, _scope, _label))

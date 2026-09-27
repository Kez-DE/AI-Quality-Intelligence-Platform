"""Xác thực bearer token cho HTTP MCP server.

Token chỉ là credential gắn với `user_id`. Quyền (role, phòng) được resolve **LIVE** từ
bảng `profiles` mỗi request — nên khi admin nâng quyền / gán phòng cho tài khoản, token cũ
tự phản ánh, KHÔNG cần cấp lại.

Ánh xạ profile → identity MCP:
- role admin                          → (admin, None)      : toàn hệ thống
- role manager/staff + có department  → (role, department) : scoped đúng phòng
- role manager/staff + CHƯA có phòng  → (pending, None)    : không tool nào
- role pending / role lạ / rỗng       → (pending, None)    : không tool nào
- không tìm thấy profile              → None               : từ chối

Qua HTTP, SupabaseTokenVerifier từ chối luôn identity pending (401): không có
danh sách tool, không có phiên.

Tầng tool guest (submit_feedback) đã bỏ theo decision 0017: Customer gửi phản hồi
qua Customer web, không qua tài khoản.
"""
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, TypedDict


class Identity(TypedDict):
    role: str
    scope_team: Optional[str]
    # Chủ token/JWT. Không tool nào hiện dùng; giữ để truy vết ai gọi.
    user_id: Optional[str]


def hash_token(raw: str) -> str:
    """SHA-256 hex của token thô. Deterministic — dùng để tra và để lưu."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _identity_from_profile(
    role: Optional[str], department: Optional[str], user_id: Optional[str] = None
) -> Identity:
    """Ánh xạ (role, department) của profile → identity MCP. Đóng an toàn:
    ops thiếu phòng KHÔNG được toàn hệ thống mà tụt về pending (không tool)."""
    role = (role or "").strip().lower()
    dept = (department or "").strip() or None
    if role == "admin":
        return {"role": "admin", "scope_team": None, "user_id": user_id}
    if role in ("manager", "staff") and dept:
        return {"role": role, "scope_team": dept, "user_id": user_id}
    # Pending account, role lạ, hoặc nhân viên chưa được gán phòng → không tool nào.
    return {"role": "pending", "scope_team": None, "user_id": user_id}


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

    ident = _identity_from_profile(
        profs[0].get("role"), profs[0].get("department"), user_id)
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


# ── OAuth Resource Server verifier ─────────────────────────────────────────
# Token đến từ 2 nguồn: (1) JWT Supabase — gồm token do OAuth 2.1 server của
# Supabase phát cho MCP client (sub = user id); (2) bearer bảng mcp_tokens
# (máy-tới-máy, admin cấp qua CLI). Cả hai đều resolve quyền LIVE từ profiles.
from mcp.server.auth.provider import AccessToken, TokenVerifier


class SupabaseTokenVerifier(TokenVerifier):
    def __init__(self, db=None):
        self._db = db

    def _get_db(self):
        if self._db is None:
            from agents.common import get_db
            self._db = get_db()
        return self._db

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None
        db = self._get_db()
        # 1) JWT Supabase (OAuth hoặc session thường) — chỉ get_user() rơi xuống bearer,
        # vì JWT hết hạn/không hợp lệ là lý do DUY NHẤT hợp lệ để thử bearer.
        uid = None
        user = None
        try:
            result = db.auth.get_user(token)
            user = getattr(result, "user", None)
            uid = getattr(user, "id", None)
        except Exception:
            uid = None  # không phải JWT hợp lệ → thử bearer

        if uid:
            # Còn mật khẩu tạm (decision 0017): đổi xong ở Staff web mới dùng MCP được.
            if (getattr(user, "app_metadata", None) or {}).get("must_change_password") is True:
                return None
            # uid đã xác thực hợp lệ: tra profiles PHẢI fail-closed, không được rơi
            # xuống bearer path (lỗi DB tạm thời != JWT invalid).
            try:
                profs = (
                    db.table("profiles").select("role,department")
                    .eq("id", uid).limit(1).execute().data or []
                )
            except Exception:
                return None  # ponytail: fail closed, lỗi DB không phải cửa vào bearer
            if profs:
                ident = _identity_from_profile(
                    profs[0].get("role"), profs[0].get("department"), uid)
                if ident["role"] == "pending":
                    return None  # không quyền → 401, không lộ danh sách tool
                return AccessToken(
                    token=token, client_id=f"supabase-user:{uid}",
                    scopes=[], claims=dict(ident))
            return None  # có JWT nhưng không có profile → từ chối
        # 2) Bearer bảng mcp_tokens
        ident = verify_token(token, db=db)
        if ident and ident["role"] != "pending":
            return AccessToken(token=token, client_id="mcp-bearer-token",
                               scopes=[], claims=dict(ident))
        return None


if __name__ == "__main__":
    # CLI phát token cho một user: python mcp_auth.py <user_id> [label]
    import sys
    if len(sys.argv) < 2:
        print("usage: python mcp_auth.py <user_id> [label]")
        raise SystemExit(1)
    print(issue_token(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "cli"))

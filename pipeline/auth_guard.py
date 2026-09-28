"""Auth guard cho FastAPI: xác thực Supabase JWT + kiểm tra role (RBAC).

Backend chạy bằng SERVICE_ROLE_KEY nên bypass RLS. Vì vậy mọi endpoint ghi/quản trị
PHẢI tự kiểm tra danh tính + quyền ở tầng API, không thể dựa vào RLS của Postgres.

Luồng:
  1. Lấy Bearer token từ header Authorization.
  2. Gọi supabase.auth.get_user(token) để Supabase tự verify chữ ký JWT.
  3. Đọc role từ bảng profiles (qua service-role client) -> trả về AuthUser.
  4. Các dependency require_user / require_ops_staff / require_admin gate theo role.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

from ingest import get_supabase

# pending = Pending account (CONTEXT.md): no access until an admin grants a
# Staff role; every fail-closed fallback lands on 'pending'.
# guest = Customer account (decision 0018): a self sign-up, reaches only
# /api/customer/* (require_customer) and /api/me.
VALID_ROLES = {"admin", "manager", "staff", "pending", "guest"}
OPS_ROLES = {"admin", "manager", "staff"}


@dataclass
class AuthUser:
    id: str
    email: str | None
    role: str
    department: str | None
    # Admin-created account still on its temporary password (decision 0017).
    # Read from app_metadata, which only the service role can write.
    must_change_password: bool = False


def _extract_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Thiếu Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Authorization header phải dạng 'Bearer <token>'")
    return parts[1].strip()


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    """Xác thực JWT và trả về user kèm role. Dùng làm FastAPI dependency."""
    token = _extract_token(authorization)
    db = get_supabase()

    try:
        result = db.auth.get_user(token)
    except Exception as exc:  # token hỏng / hết hạn / lỗi mạng tới Supabase
        raise HTTPException(status_code=401, detail=f"Token không hợp lệ: {str(exc)[:200]}") from exc

    user = getattr(result, "user", None)
    if not user or not getattr(user, "id", None):
        raise HTTPException(status_code=401, detail="Không xác thực được người dùng")

    profile = db.table("profiles").select("role,email,department").eq("id", user.id).limit(1).execute().data or []
    role = (profile[0].get("role") if profile else None) or "pending"
    department = profile[0].get("department") if profile else None
    if role not in VALID_ROLES:
        role = "pending"

    app_meta = getattr(user, "app_metadata", None) or {}
    return AuthUser(
        id=user.id,
        email=getattr(user, "email", None),
        role=role,
        department=department,
        must_change_password=app_meta.get("must_change_password") is True,
    )


def _require_password_changed(user: AuthUser) -> None:
    # Only /api/me and POST /api/me/password skip this: every role guard calls it.
    if user.must_change_password:
        raise HTTPException(status_code=403, detail="Bạn cần đổi mật khẩu tạm trước khi tiếp tục")


def require_ops_staff(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role not in OPS_ROLES:
        raise HTTPException(status_code=403, detail="Yêu cầu quyền staff/manager/admin")
    _require_password_changed(user)
    return user


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Yêu cầu quyền admin")
    _require_password_changed(user)
    return user


def require_manager(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="Yêu cầu quyền manager hoặc admin")
    _require_password_changed(user)
    return user


def require_customer(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != "guest":
        raise HTTPException(status_code=403, detail="Chỉ dành cho tài khoản khách hàng")
    _require_password_changed(user)
    return user


def can_view_team(user: AuthUser, team: str) -> bool:
    """Kiểm tra user có quyền xem dữ liệu của một phòng ban cụ thể không.

    - admin: xem mọi phòng.
    - ops (manager/staff) đã được gán phòng: chỉ xem đúng phòng của mình.
    - ops chưa được gán phòng: không xem được phòng nào.
    """
    if user.role == "admin":
        return True
    if not user.department:
        return False
    return user.department == team


def scoped_team(user: AuthUser, requested_team: str | None) -> str | None:
    """Trả về team mà query NÊN lọc theo, dựa trên quyền của user.

    - admin: tôn trọng requested_team (None = xem tất cả các phòng).
    - ops đã gán phòng: luôn ép về phòng của user (bỏ qua requested_team).
    - ops chưa gán phòng: raise 403 kèm hướng dẫn liên hệ admin.
    """
    if user.role == "admin":
        return requested_team
    if not user.department:
        raise HTTPException(
            status_code=403,
            detail="Bạn chưa được gán phòng ban. Vui lòng liên hệ admin.",
        )
    return user.department

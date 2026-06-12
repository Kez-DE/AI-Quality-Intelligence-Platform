"""User-management endpoints (chỉ admin) — CRUD trên bảng profiles + auth.users.

Backend dùng SERVICE_ROLE_KEY nên truy cập được admin API của Supabase
(db.auth.admin.*) để liệt kê/xoá tài khoản auth. Mọi route ở đây đều
đứng sau require_admin.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth_guard import AuthUser, VALID_ROLES, require_admin
from ingest import get_supabase

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
def list_users(_: AuthUser = Depends(require_admin)):
    """Liệt kê toàn bộ profiles kèm role (admin only)."""
    db = get_supabase()
    try:
        rows = db.table("profiles") \
            .select("id,email,full_name,role,created_at") \
            .order("created_at", desc=False) \
            .execute() \
            .data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read profiles: {str(exc)[:300]}") from exc
    return {"status": "success", "data": rows}


@router.patch("/{user_id}/role")
def update_user_role(user_id: str, payload: dict, admin: AuthUser = Depends(require_admin)):
    """Đổi role của một user. Chặn admin tự hạ quyền chính mình để tránh khoá hệ thống."""
    new_role = payload.get("role")
    if new_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role phải thuộc {sorted(VALID_ROLES)}")
    if user_id == admin.id and new_role != "admin":
        raise HTTPException(status_code=400, detail="Không thể tự hạ quyền admin của chính mình")

    db = get_supabase()
    try:
        data = db.table("profiles") \
            .update({"role": new_role}) \
            .eq("id", user_id) \
            .execute() \
            .data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot update role: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success", "data": data[0]}


@router.delete("/{user_id}")
def delete_user(user_id: str, admin: AuthUser = Depends(require_admin)):
    """Xoá tài khoản auth (profiles xoá theo cascade). Chặn admin tự xoá chính mình."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Không thể tự xoá tài khoản admin đang đăng nhập")

    db = get_supabase()
    try:
        db.auth.admin.delete_user(user_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot delete user: {str(exc)[:300]}") from exc
    return {"status": "success", "data": {"id": user_id, "deleted": True}}

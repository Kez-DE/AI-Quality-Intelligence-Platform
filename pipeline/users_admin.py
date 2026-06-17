"""User-management endpoints (chỉ admin) — CRUD trên bảng profiles + auth.users.

Backend dùng SERVICE_ROLE_KEY nên truy cập được admin API của Supabase
(db.auth.admin.*) để liệt kê/xoá tài khoản auth. Mọi route ở đây đều
đứng sau require_admin.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Query

from auth_guard import AuthUser, VALID_ROLES, require_admin
from ingest import get_supabase

router = APIRouter(prefix="/api/users", tags=["users"])
audit_router = APIRouter(tags=["audit"])


@router.get("")
def list_users(_: AuthUser = Depends(require_admin)):
    """Liệt kê toàn bộ profiles kèm role (admin only)."""
    db = get_supabase()
    try:
        rows = db.table("profiles") \
            .select("id,email,full_name,role,department,created_at") \
            .order("created_at", desc=False) \
            .execute() \
            .data or []
    except Exception as exc:
        # Fallback: nếu cột department chưa tồn tại (migration chưa apply)
        if "department" in str(exc):
            rows = db.table("profiles") \
                .select("id,email,full_name,role,created_at") \
                .order("created_at", desc=False) \
                .execute() \
                .data or []
            # Thêm department=None cho tương thích frontend
            for row in rows:
                row["department"] = None
        else:
            raise HTTPException(status_code=503, detail=f"Cannot read profiles: {str(exc)[:300]}") from exc
    return {"status": "success", "data": rows}


@router.patch("/{user_id}/role")
def update_user_role(user_id: str, payload: dict, user: AuthUser = Depends(require_admin)):
    """Đổi role của một user. Chặn admin tự thay đổi quyền chính mình."""
    new_role = payload.get("role")
    if new_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role phải thuộc {sorted(VALID_ROLES)}")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Không thể thay đổi quyền của chính mình")

    db = get_supabase()

    # Read old profile before updating
    try:
        old_profile = db.table("profiles").select("role,email").eq("id", user_id).limit(1).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read profile: {str(exc)[:300]}") from exc
    if not old_profile:
        raise HTTPException(status_code=404, detail="User not found")
    old_role = old_profile[0].get("role", "guest")
    target_email = old_profile[0].get("email")

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

    # Audit log
    try:
        db.table("audit_logs").insert({
            "actor_id": user.id,
            "actor_email": user.email,
            "action": "role_change",
            "target_id": user_id,
            "target_email": target_email,
            "details": {"old_role": old_role, "new_role": new_role}
        }).execute()
    except Exception:
        pass  # Non-critical: don't fail the request if audit insert fails

    return {"status": "success", "data": data[0]}


@router.patch("/{user_id}/department")
def update_user_department(user_id: str, payload: dict, user: AuthUser = Depends(require_admin)):
    """Gán phòng ban cho user. Admin only."""
    department = payload.get("department")
    valid_departments = [None, "IT", "Safety", "CSKH", "Vận hành", "Pricing", "Marketing"]
    if department not in valid_departments:
        raise HTTPException(status_code=400, detail=f"department phải thuộc {valid_departments}")

    db = get_supabase()
    try:
        data = db.table("profiles").update({"department": department}).eq("id", user_id).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot update department: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    # Audit log
    try:
        db.table("audit_logs").insert({
            "actor_id": user.id,
            "actor_email": user.email,
            "action": "department_change",
            "target_id": user_id,
            "details": {"department": department}
        }).execute()
    except Exception:
        pass

    return {"status": "success", "data": data[0]}


@router.delete("/{user_id}")
def delete_user(user_id: str, user: AuthUser = Depends(require_admin)):
    """Xoá tài khoản auth (profiles xoá theo cascade). Chặn admin tự xoá chính mình."""
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Không thể tự xoá tài khoản admin đang đăng nhập")

    db = get_supabase()

    # Read profile email before deleting
    try:
        old_profile = db.table("profiles").select("email").eq("id", user_id).limit(1).execute().data or []
    except Exception:
        old_profile = []
    deleted_email = old_profile[0].get("email") if old_profile else None

    try:
        db.auth.admin.delete_user(user_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot delete user: {str(exc)[:300]}") from exc

    # Audit log
    try:
        db.table("audit_logs").insert({
            "actor_id": user.id,
            "actor_email": user.email,
            "action": "user_delete",
            "target_id": user_id,
            "target_email": deleted_email,
            "details": {"deleted_email": deleted_email}
        }).execute()
    except Exception:
        pass  # Non-critical

    return {"status": "success", "data": {"id": user_id, "deleted": True}}


@router.post("/bulk-approve")
def bulk_approve_users(payload: dict, user: AuthUser = Depends(require_admin)):
    """Duyệt hàng loạt user từ guest sang staff/manager."""
    user_ids = payload.get("user_ids", [])
    target_role = payload.get("role", "staff")
    if target_role not in ("staff", "manager"):
        raise HTTPException(status_code=400, detail="Chỉ có thể duyệt thành staff hoặc manager")
    if not user_ids or len(user_ids) > 50:
        raise HTTPException(status_code=400, detail="Cần 1-50 user_ids")

    db = get_supabase()
    results = []
    for uid in user_ids:
        try:
            data = db.table("profiles").update({"role": target_role}).eq("id", uid).eq("role", "guest").execute().data or []
            if data:
                results.append(uid)
                # audit log
                db.table("audit_logs").insert({
                    "actor_id": user.id,
                    "actor_email": user.email,
                    "action": "bulk_approve",
                    "target_id": uid,
                    "details": {"old_role": "guest", "new_role": target_role}
                }).execute()
        except Exception:
            pass
    return {"status": "success", "data": {"approved_count": len(results), "approved_ids": results}}


@audit_router.get("/api/audit-logs")
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    _: AuthUser = Depends(require_admin),
):
    """Lịch sử thay đổi quyền / xoá user. Admin only."""
    db = get_supabase()
    try:
        rows = db.table("audit_logs") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute() \
            .data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read audit logs: {str(exc)[:300]}") from exc
    return {"status": "success", "data": rows}

"""User-management endpoints (chỉ admin) — CRUD trên bảng profiles + auth.users.

Backend dùng SERVICE_ROLE_KEY nên truy cập được admin API của Supabase
(db.auth.admin.*) để tạo/liệt kê/xoá tài khoản auth. Mọi route ở đây đều
đứng sau require_admin. Từ decision 0017, admin là người DUY NHẤT tạo tài khoản
(POST /api/admin/users); không còn tự đăng ký.
"""

from __future__ import annotations

import logging
import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError, field_validator

from auth_guard import AuthUser, VALID_ROLES, get_current_user, require_admin
from departments import DEPARTMENTS
from ingest import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])
audit_router = APIRouter(tags=["audit"])
admin_router = APIRouter(prefix="/api/admin", tags=["users"])
# Own-account routes. Open to a flagged or pending account: no role guard.
me_router = APIRouter(prefix="/api/me", tags=["users"])


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
    old_role = old_profile[0].get("role", "pending")
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
    valid_departments = [None, *DEPARTMENTS]
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
    """Duyệt hàng loạt Pending account sang staff/manager."""
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
            data = db.table("profiles").update({"role": target_role}).eq("id", uid).eq("role", "pending").execute().data or []
            if data:
                results.append(uid)
                # audit log
                db.table("audit_logs").insert({
                    "actor_id": user.id,
                    "actor_email": user.email,
                    "action": "bulk_approve",
                    "target_id": uid,
                    "details": {"old_role": "pending", "new_role": target_role}
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


# ── Admin tạo tài khoản (decision 0017) ────────────────────────────────────────

# Same five checks the old sign-up form showed (app/src/routes/auth.tsx
# validatePassword), so an admin-set temporary password is no weaker than a
# self-chosen one used to be.
_PASSWORD_CRITERIA = (
    ("Ít nhất 8 ký tự", lambda pw: len(pw) >= 8),
    ("Chữ hoa (A–Z)", lambda pw: re.search(r"[A-Z]", pw) is not None),
    ("Chữ thường (a–z)", lambda pw: re.search(r"[a-z]", pw) is not None),
    ("Số (0–9)", lambda pw: re.search(r"[0-9]", pw) is not None),
    ("Ký tự đặc biệt (!@#…)", lambda pw: re.search(r"[^A-Za-z0-9]", pw) is not None),
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def password_problems(password: str) -> list[str]:
    """Labels of the criteria `password` fails. Empty list = acceptable."""
    return [label for label, ok in _PASSWORD_CRITERIA if not ok(password)]


class CreateUserReq(BaseModel):
    email: str = Field(..., max_length=254)
    full_name: str = Field(..., max_length=120)
    # A created account gets a real Staff role; 'pending' is what the sign-up
    # trigger assigns, never something an admin picks.
    role: Literal["admin", "manager", "staff"]
    department: Optional[str] = None
    temp_password: str = Field(..., max_length=72)  # bcrypt ignores bytes past 72

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("empty")
        return v

    @field_validator("department")
    @classmethod
    def _department(cls, v: Optional[str]) -> Optional[str]:
        v = (v or "").strip() or None
        if v is not None and v not in DEPARTMENTS:
            raise ValueError("unknown department")
        return v


def _is_duplicate_email(exc: Exception) -> bool:
    if getattr(exc, "code", None) in {"email_exists", "user_already_exists"}:
        return True
    return bool(re.search(r"already (been )?registered|already exists", str(exc), re.I))


@admin_router.post("/users", status_code=201)
def create_user(payload: dict, user: AuthUser = Depends(require_admin)):
    """Admin tạo Staff account với mật khẩu tạm; người dùng phải đổi ở lần đăng nhập đầu.

    Body lấy dạng dict rồi validate trong hàm, KHÔNG để FastAPI validate: lỗi 422
    mặc định trả lại `input` — với lỗi thiếu field, input là cả body, tức là mật
    khẩu tạm. Ở đây lỗi chỉ nêu tên field. Mật khẩu không bao giờ được log, trả
    về, hay ghi vào audit.
    """
    try:
        req = CreateUserReq.model_validate(payload)
    except ValidationError as exc:
        fields = sorted({str(err["loc"][0]) for err in exc.errors() if err.get("loc")})
        raise HTTPException(status_code=400, detail=f"Dữ liệu không hợp lệ: {', '.join(fields) or 'body'}") from None

    problems = password_problems(req.temp_password)
    if problems:
        raise HTTPException(status_code=400, detail=f"Mật khẩu tạm chưa đạt: {'; '.join(problems)}")

    db = get_supabase()
    try:
        created = db.auth.admin.create_user({
            "email": req.email,
            "password": req.temp_password,
            "email_confirm": True,
            "user_metadata": {"full_name": req.full_name},
            # app_metadata, not user_metadata: the user cannot clear it with
            # auth.updateUser. Cleared only by POST /api/me/password.
            "app_metadata": {"must_change_password": True},
        })
    except Exception as exc:
        if _is_duplicate_email(exc):
            raise HTTPException(status_code=409, detail="Email này đã có tài khoản") from None
        # Error code only: never forward the provider message verbatim here.
        code = getattr(exc, "code", None) or type(exc).__name__
        raise HTTPException(status_code=503, detail=f"Không tạo được tài khoản ({code})") from None

    new_id = created.user.id
    # handle_new_user already inserted the profile as 'pending'; grant the role.
    try:
        updated = db.table("profiles").update(
            {"role": req.role, "department": req.department}
        ).eq("id", new_id).execute().data or []
    except Exception as exc:
        logger.error("admin create_user: role grant failed for %s: %s", new_id, type(exc).__name__)
        updated = []
    if not updated:
        # A confirmed login whose role was never set is a half-made account;
        # remove it so the admin can simply retry.
        try:
            db.auth.admin.delete_user(new_id)
        except Exception as exc:
            logger.error("admin create_user: rollback delete failed for %s: %s", new_id, type(exc).__name__)
            # The account survives as pending (no access). Say so, or the admin
            # retries and gets a confusing 409.
            raise HTTPException(
                status_code=503,
                detail=f"Không gán được quyền và không huỷ được tài khoản {req.email}: tài khoản vẫn tồn tại "
                "ở trạng thái Chờ cấp quyền. Cấp quyền hoặc xoá nó trong danh sách người dùng.",
            ) from None
        raise HTTPException(status_code=503, detail="Không gán được quyền cho tài khoản mới, đã huỷ tạo")

    try:
        db.table("audit_logs").insert({
            "actor_id": user.id,
            "actor_email": user.email,
            "action": "user_create",
            "target_id": new_id,
            "target_email": req.email,
            "details": {"role": req.role, "department": req.department},
        }).execute()
    except Exception as exc:
        # Non-critical, same as the other admin actions, but an account created
        # with no audit row must at least leave a trace in the logs.
        logger.error("admin create_user: audit insert failed for %s: %s", new_id, type(exc).__name__)

    return {"status": "success", "data": {
        "id": new_id, "email": req.email, "role": req.role, "department": req.department,
    }}


@me_router.post("/password")
def change_own_password(payload: dict, user: AuthUser = Depends(get_current_user)):
    """Đổi mật khẩu của chính mình và xoá cờ must_change_password (decision 0017).

    Đi qua backend, không qua supabase.auth.updateUser, vì cờ nằm trong
    app_metadata mà chỉ service role ghi được. Mật khẩu không bao giờ được log
    hay trả về.
    """
    new_password = payload.get("new_password") if isinstance(payload, dict) else None
    if not isinstance(new_password, str) or len(new_password) > 72:  # bcrypt ignores bytes past 72
        raise HTTPException(status_code=400, detail="Dữ liệu không hợp lệ: new_password")
    problems = password_problems(new_password)
    if problems:
        raise HTTPException(status_code=400, detail=f"Mật khẩu mới chưa đạt: {'; '.join(problems)}")

    try:
        get_supabase().auth.admin.update_user_by_id(user.id, {
            "password": new_password,
            "app_metadata": {"must_change_password": False},  # GoTrue merges app_metadata keys
        })
    except Exception as exc:
        code = getattr(exc, "code", None) or type(exc).__name__
        logger.error("change_own_password failed for %s: %s", user.id, code)
        raise HTTPException(status_code=503, detail=f"Không đổi được mật khẩu ({code})") from None

    return {"status": "success", "data": {"must_change_password": False}}

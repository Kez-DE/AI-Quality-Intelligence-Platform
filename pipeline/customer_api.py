"""Customer account routes (US-078 / decision 0018).

A Customer account is a self sign-up (role `guest`). It reaches three routes and
nothing else: send feedback as itself, list its own feedback, and the customer
assistant. The same two rules as `public_intake.py` hold here:

1. Nothing trusts the caller. Labels come from the classifier, the reference is
   server-generated, the owner is the JWT's user id, and the body is never logged.
2. Nothing leaks. Responses are allowlists; topic, sentiment and severity stay
   internal (decision 0017).
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_guard import AuthUser, require_customer
from env_config import get_settings
from ingest import get_supabase
from public_intake import MAX_PUBLIC_TEXT, PUBLIC_REF_BYTES, classified_fields, derive_status
from rate_limiter import RateLimiter, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customer", tags=["customer"])

_s = get_settings()

# Keyed by account id, not IP. Same budgets as the anonymous routes: an account
# is a free self sign-up, so it earns no more than a stranger does.
customer_intake_limit = RateLimiter(
    max_requests=_s.rate_limit_public_intake, window_seconds=3600, scope="customer_intake"
)
customer_chat_limit = RateLimiter(
    max_requests=_s.rate_limit_chat_public, window_seconds=3600, scope="customer_chat"
)

HISTORY_LIMIT = 100


class CustomerFeedbackReq(BaseModel):
    """Same shape as PublicFeedbackReq; labels are absent on purpose."""

    text: str = Field(..., min_length=1, max_length=MAX_PUBLIC_TEXT)
    channel: str = Field(default="web", max_length=40)
    area: Optional[str] = Field(default=None, max_length=80)
    # Honeypot, as on the public form. Uncapped so a bot cannot probe with 422s.
    website: Optional[str] = None


class CustomerChatMessage(BaseModel):
    role: str
    content: str = Field(..., max_length=15000)


class CustomerChatReq(BaseModel):
    messages: list[CustomerChatMessage] = Field(..., max_length=60)


def create_customer_feedback(user: AuthUser, text: str, channel: str = "web", area: str | None = None) -> dict:
    """The one write path for a Customer account: the form and the chat tool both
    land here, so both are classified and both spend the same rate limit."""
    check_rate_limit(customer_intake_limit, user.id)

    from regions import region_code

    labels = classified_fields(text)
    public_ref = secrets.token_urlsafe(PUBLIC_REF_BYTES)
    row = {
        # Owned row: no IP hash and no anonymous retention clock; the account
        # holder reads it back from their history (decision 0018).
        "user_id": user.id,
        "public_ref": public_ref,
        "source": "customer",
        "channel": (channel or "web").strip() or "web",
        "area": region_code((area or "").strip()),
        **labels,
    }
    try:
        data = get_supabase().table("feedback").insert(row).execute().data or []
    except Exception as exc:
        logger.error("customer feedback insert failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Không lưu được phản hồi, vui lòng thử lại"
        ) from exc

    created = data[0] if data else row
    return {
        "public_ref": public_ref,
        "status": derive_status(created),
        "created_at": created.get("created_at"),
    }


@router.post("/feedback")
def submit_customer_feedback(payload: CustomerFeedbackReq, user: AuthUser = Depends(require_customer)):
    if (payload.website or "").strip():
        # Spend a request first, so a bot learns nothing by retrying.
        check_rate_limit(customer_intake_limit, user.id)
        raise HTTPException(status_code=400, detail="Invalid submission")
    data = create_customer_feedback(user, payload.text, payload.channel, payload.area)
    return {"status": "success", "data": data}


@router.get("/feedback")
def list_customer_feedback(user: AuthUser = Depends(require_customer)):
    try:
        rows = (
            get_supabase()
            .table("feedback")
            .select("public_ref,created_at,text,needs_review,reviewed")
            .eq("user_id", user.id)
            # Only what this account filed here. Other writers stamp user_id too
            # (dataset ingest, staff chat/manual), and those rows have no public_ref.
            .eq("source", "customer")
            .order("created_at", desc=True)
            .limit(HISTORY_LIMIT)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.error("customer history read failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Không tải được lịch sử, vui lòng thử lại") from exc

    return {"status": "success", "data": [
        {
            "public_ref": r.get("public_ref"),
            "status": derive_status(r),
            "created_at": r.get("created_at"),
            "text": r.get("text"),
        }
        for r in rows
    ]}


def _submit_tool(user: AuthUser, name: str, args: dict) -> str:
    """submit_feedback for the customer assistant. Any label the model passes is
    ignored: only `content` is read, and the classifier decides the rest."""
    if name != "submit_feedback":
        return f"Error: Public tool '{name}' not found"
    try:
        out = create_customer_feedback(user, str(args.get("content", ""))[:MAX_PUBLIC_TEXT], channel="chat")
    except HTTPException as exc:
        return f"Không gửi được phản hồi: {exc.detail}"
    except Exception as exc:
        # Same as the staff public tier: never hand internal error text to the caller.
        logger.error("customer chat submit failed: %s", type(exc).__name__)
        return "Không gửi được phản hồi, vui lòng thử lại."
    return f"Đã ghi nhận phản hồi. Mã tra cứu: {out['public_ref']}"


@router.post("/chat")
def customer_chat(payload: CustomerChatReq, user: AuthUser = Depends(require_customer)):
    check_rate_limit(customer_chat_limit, user.id)
    # main imports this module, so the shared public tier is imported at call time.
    from main import run_public_chat

    out = run_public_chat(
        payload.messages, lambda name, args: _submit_tool(user, name, args), log_team="customer"
    )
    # Allowlist: provider, model, usage and tool metadata stay internal.
    return {"status": "success", "data": {"content": out["data"].get("content")}}

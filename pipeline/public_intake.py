"""Anonymous public feedback intake — the only unauthenticated write surface.

US-076 / decision 0016. A xanhSM rider who has just had an incident reports it
from the street, on a phone, with no account. Every other path into
`public.feedback` requires a Supabase JWT; these two routes deliberately require
nothing, so everything they do is written to be safe without an identity.

Two rules hold this file together:

1. Nothing here trusts the caller. Classification is server-side, the tracking
   reference is server-generated, and the request body is never logged.
2. Nothing here leaks. The status response is an explicit allowlist of fields,
   not a row dump, because possession of a reference is the only authorization.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from clean import clean_text
from env_config import get_settings
from ingest import get_supabase
from rate_limiter import RateLimiter, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["public"])

_s = get_settings()

# 9 bytes -> 12 url-safe characters, 72 bits of entropy. Unguessable, and short
# enough to read off a phone screen.
PUBLIC_REF_BYTES = 9

# Hard ceiling on stored text. The authenticated path has no cap; an open route
# needs one so a single request cannot be used as free storage.
MAX_PUBLIC_TEXT = 4000

# How long an anonymous report's personal text is kept. The backend-worker
# redacts it once this passes (services/retention.py, decision 0017).
RETENTION_DAYS = 180

# Salt for the stored IP hash. A random per-process salt is the fail-safe
# default: rate limiting still works, and stored hashes stop being linkable
# across restarts.
_FINGERPRINT_SALT = _s.public_fingerprint_salt or secrets.token_hex(16)

public_intake_limit = RateLimiter(
    max_requests=_s.rate_limit_public_intake, window_seconds=3600, scope="public_intake"
)
public_status_limit = RateLimiter(
    max_requests=_s.rate_limit_public_status, window_seconds=3600, scope="public_status"
)


class PublicFeedbackReq(BaseModel):
    """What an anonymous reporter is allowed to say.

    Topic, sentiment, severity and confidence are absent on purpose: the same
    rule as the authenticated path (`main.submit_feedback`). Letting a submitter
    self-assign severity would corrupt the label set the classifier is trained
    against, and on an unauthenticated route it would also be a free priority
    escalation.
    """

    text: str = Field(..., min_length=1, max_length=MAX_PUBLIC_TEXT)
    channel: str = Field(default="web", max_length=40)
    area: Optional[str] = Field(default=None, max_length=80)
    # Honeypot (decision 0017). The Customer web renders this input hidden and
    # unfocusable, so a person leaves it empty and a form-filling bot does not.
    # Uncapped on purpose: a length error would be a 422 raised before the rate
    # limiter runs, and a bot must not get a way to probe for free.
    website: Optional[str] = None


def client_ip(request: Request) -> str:
    """Resolve the caller's address behind Railway's edge proxy.

    The rightmost `X-Forwarded-For` entry, not the leftmost. Each proxy appends
    the peer address it actually saw, so with one trusted proxy in front the last
    entry is the real client and a forged leading entry cannot move the
    rate-limit bucket. With no header at all (local, direct) fall back to the
    socket peer.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        if hops:
            return hops[-1]
    return request.client.host if request.client else "unknown"


def fingerprint(request: Request) -> str:
    """Salted hash of the client IP — the abuse-control key, not an identity.

    Two reporters behind one NAT share a fingerprint and that is accepted: this
    exists to make bulk submission tedious, not to tell people apart.
    """
    ip = client_ip(request)
    return hashlib.sha256(f"{_FINGERPRINT_SALT}:{ip}".encode()).hexdigest()[:32]


def derive_status(row: dict) -> str:
    """Public-facing progress of one report, derived rather than stored.

    Only what the feedback row itself knows. Deliberately not joined to alerts or
    tasks: those carry internal routing the holder of a reference has no claim to.
    """
    # "reviewed" = staff checked the AI label, not that the problem is fixed
    # (CONTEXT.md: Feedback status). The old "resolved" promised more than that.
    if row.get("reviewed"):
        return "reviewed"
    if row.get("needs_review"):
        return "under_review"
    return "received"


@router.post("/feedback")
def submit_public_feedback(payload: PublicFeedbackReq, request: Request):
    """Accept a report from someone with no account.

    Returns a tracking reference. That reference is the submitter's only way back
    to this report, and the only credential for it.
    """
    check_rate_limit(public_intake_limit, fingerprint(request))

    # After the limiter on purpose: a tripped honeypot still spends a request, so
    # a bot learns nothing by retrying. Nothing is stored or logged.
    if (payload.website or "").strip():
        raise HTTPException(status_code=400, detail="Invalid submission")

    from classifier import predict_feedback
    from regions import region_code

    # clean_text masks phone, email and plate before anything else touches the
    # string — the classifier, the database and any future LLM all see the masked
    # form. The raw body is never stored and never logged.
    cleaned = clean_text(payload.text)
    if not cleaned.strip():
        raise HTTPException(status_code=400, detail="Thiếu nội dung phản hồi")

    prediction = predict_feedback(cleaned)
    severity = prediction["severity"]
    severity_value = (
        severity
        if isinstance(severity, str) and severity.upper().startswith("P")
        else f"P{int(severity)}"
    )

    public_ref = secrets.token_urlsafe(PUBLIC_REF_BYTES)
    row = {
        # No account. The CHECK constraint feedback_identity_chk accepts this row
        # because public_ref is present.
        "user_id": None,
        "public_ref": public_ref,
        "submitter_hash": fingerprint(request),
        "retention_until": (
            datetime.now(timezone.utc) + timedelta(days=RETENTION_DAYS)
        ).isoformat(),
        "source": "public",
        "channel": (payload.channel or "web").strip() or "web",
        "text": cleaned,
        "topic": prediction["topic"],
        "sentiment": prediction["sentiment"],
        "severity": severity_value,
        "confidence": prediction["confidence"],
        "area": region_code((payload.area or "").strip()),
        "needs_review": prediction.get("needs_review", False),
        "review_reason": prediction.get("review_reason"),
    }

    try:
        data = get_supabase().table("feedback").insert(row).execute().data or []
    except Exception as exc:
        # Log the failure shape, never the submission: the body is not
        # interpolated into this message or any other.
        logger.error("public feedback insert failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Không lưu được phản hồi, vui lòng thử lại"
        ) from exc

    created = data[0] if data else row
    return {
        "status": "success",
        "data": {
            "public_ref": public_ref,
            "status": derive_status(created),
            "created_at": created.get("created_at"),
        },
    }


@router.get("/feedback/{public_ref}")
def get_public_feedback_status(public_ref: str, request: Request):
    """Progress of one report, for whoever holds its reference.

    The response is an allowlist of three fields. Everything else is withheld,
    the AI labels included (decision 0017): a Customer never sees topic,
    sentiment or severity, and a reference that leaks into browser history or a
    screenshot must not hand over the body or the internal scoring.
    """
    check_rate_limit(public_status_limit, fingerprint(request))

    try:
        rows = (
            get_supabase()
            .table("feedback")
            .select("public_ref,created_at,needs_review,reviewed")
            .eq("public_ref", public_ref)
            # Expired or redacted rows are filtered here, so they fall into the
            # same 404 as unknown codes. Checked at read time, not left to the
            # 03:00 job, so a row is gone the moment its deadline passes.
            .gt("retention_until", datetime.now(timezone.utc).isoformat())
            .is_("redacted_at", "null")
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.error("public status lookup failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Không tra cứu được, vui lòng thử lại"
        ) from exc

    if not rows:
        # Same response for "never existed", "expired" and "redacted", so this is
        # not an oracle telling an enumerator which references are real.
        raise HTTPException(status_code=404, detail="Không tìm thấy phản hồi với mã này")

    row = rows[0]
    return {
        "status": "success",
        "data": {
            "public_ref": row.get("public_ref"),
            "status": derive_status(row),
            "created_at": row.get("created_at"),
        },
    }

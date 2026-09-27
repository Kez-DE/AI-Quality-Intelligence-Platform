"""US-076: anonymous public feedback intake.

The risk in this story is not that the happy path breaks — it is that an
unauthenticated route becomes a hole. So most of these assert absence: no account
required, no account created, no internal field returned, no unbounded write.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

import public_intake
from main import app
from tests._fakedb import FakeDB

IP_A = "203.0.113.10"  # TEST-NET-3, never routable
IP_B = "203.0.113.11"

PREDICTION = {
    "topic": "Safety",
    "sentiment": "negative",
    "severity": "P5",
    "confidence": 0.91,
    "needs_review": True,
    "review_reason": "safety_grid",
}


@pytest.fixture
def db(monkeypatch):
    """In-memory Supabase double, with the classifier stubbed.

    Assertions here are about which columns get written, not about model output,
    so a fixed prediction keeps them deterministic.
    """
    fake = FakeDB(feedback=[])
    monkeypatch.setattr(public_intake, "get_supabase", lambda: fake)

    import classifier

    monkeypatch.setattr(classifier, "predict_feedback", lambda _text: dict(PREDICTION))

    # The limiters hold process-global state and would otherwise leak counts
    # between tests.
    public_intake.public_intake_limit._requests.clear()
    public_intake.public_status_limit._requests.clear()
    return fake


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def submit(
    c: AsyncClient,
    text: str = "Tài xế phóng ẩu suýt gây tai nạn",
    ip: str = IP_A,
    **extra,
):
    body = {"text": text, **extra}
    return await c.post("/api/public/feedback", json=body, headers={"x-forwarded-for": ip})


# ---------------------------------------------------------------------------
# A stranger can write
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_without_any_authorization_header(db):
    async with client() as c:
        res = await submit(c)

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "under_review"
    assert len(data["public_ref"]) >= 12


@pytest.mark.asyncio
async def test_stored_row_is_anonymous_and_stamped(db):
    async with client() as c:
        res = await submit(c, channel="hotline", area="HN")

    ref = res.json()["data"]["public_ref"]
    row = next(r for r in db.tables["feedback"] if r["public_ref"] == ref)

    assert row["user_id"] is None, "an anonymous report must not invent an account"
    assert row["source"] == "public"
    assert row["channel"] == "hotline"
    assert row["submitter_hash"]
    assert row["retention_until"], "PII rows carry a retention deadline (decision 0016)"
    # Server-side classification, exactly as on the authenticated path.
    assert row["severity"] == "P5"
    assert row["topic"] == "Safety"


@pytest.mark.asyncio
async def test_client_cannot_self_assign_severity(db):
    """A submitter who sends severity/topic gets them ignored, not honored.

    On an open route, accepting these would be a free priority escalation.
    """
    async with client() as c:
        res = await c.post(
            "/api/public/feedback",
            json={"text": "xe bẩn", "severity": "P1", "topic": "Pricing", "user_id": "attacker"},
            headers={"x-forwarded-for": IP_A},
        )

    assert res.status_code == 200
    row = db.tables["feedback"][0]
    assert row["severity"] == "P5"
    assert row["topic"] == "Safety"
    assert row["user_id"] is None


@pytest.mark.asyncio
async def test_pii_is_masked_before_storage(db):
    async with client() as c:
        await submit(c, text="Tài xế biển 29A-12345 gọi 0912345678, mail toi@gmail.com chửi tôi")

    stored = db.tables["feedback"][0]["text"]
    assert "0912345678" not in stored
    assert "toi@gmail.com" not in stored
    assert "29A-12345" not in stored
    assert "[SĐT_ĐÃ_ẨN]" in stored


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "x" * (public_intake.MAX_PUBLIC_TEXT + 1)])
async def test_text_bounds_rejected(db, text):
    async with client() as c:
        res = await submit(c, text=text)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_whitespace_only_text_rejected(db):
    """Passes pydantic's min_length but has no content once cleaned."""
    async with client() as c:
        res = await submit(c, text="   \n\t  ")
    assert res.status_code == 400
    assert db.tables["feedback"] == []


@pytest.mark.asyncio
async def test_honeypot_filled_is_rejected_and_nothing_stored(db):
    """The `website` field is hidden from humans; only a bot fills it (decision 0017)."""
    async with client() as c:
        res = await submit(c, website="http://spam.example")

    assert res.status_code == 400
    assert res.json()["error"]["message"] == "Invalid submission"
    assert db.tables["feedback"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("website", ["", "   ", None])
async def test_honeypot_left_empty_is_accepted(db, website):
    async with client() as c:
        res = await submit(c, website=website)
    assert res.status_code == 200
    assert len(db.tables["feedback"]) == 1


@pytest.mark.asyncio
async def test_honeypot_hit_still_counts_against_the_rate_limit(db, monkeypatch):
    """A bot that trips the honeypot must not get free retries."""
    monkeypatch.setattr(public_intake.public_intake_limit, "max_requests", 2)

    async with client() as c:
        for _ in range(2):
            assert (await submit(c, website="x")).status_code == 400
        blocked = await submit(c)

    assert blocked.status_code == 429
    assert db.tables["feedback"] == []


# ---------------------------------------------------------------------------
# Abuse control without an account to key on
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_applies_per_ip(db, monkeypatch):
    monkeypatch.setattr(public_intake.public_intake_limit, "max_requests", 3)

    async with client() as c:
        for _ in range(3):
            assert (await submit(c, ip=IP_A)).status_code == 200

        blocked = await submit(c, ip=IP_A)
        assert blocked.status_code == 429
        assert blocked.headers["Retry-After"]

        # A different address is a different bucket.
        assert (await submit(c, ip=IP_B)).status_code == 200


@pytest.mark.asyncio
async def test_forged_forwarded_for_cannot_move_the_bucket(db, monkeypatch):
    """Railway's edge appends the address it saw, so the rightmost hop is real.

    A caller prepending fake addresses keeps landing in the same bucket.
    """
    monkeypatch.setattr(public_intake.public_intake_limit, "max_requests", 2)

    async with client() as c:
        for forged in ("1.1.1.1", "2.2.2.2"):
            res = await c.post(
                "/api/public/feedback",
                json={"text": "spam"},
                headers={"x-forwarded-for": f"{forged}, {IP_A}"},
            )
            assert res.status_code == 200

        res = await c.post(
            "/api/public/feedback",
            json={"text": "spam"},
            headers={"x-forwarded-for": f"9.9.9.9, {IP_A}"},
        )
        assert res.status_code == 429


def test_client_ip_prefers_rightmost_hop():
    class _Req:
        def __init__(self, xff):
            self.headers = {"x-forwarded-for": xff} if xff else {}
            self.client = type("C", (), {"host": "127.0.0.1"})()

    assert public_intake.client_ip(_Req("1.1.1.1, 203.0.113.10")) == "203.0.113.10"
    assert public_intake.client_ip(_Req("203.0.113.10")) == "203.0.113.10"
    assert public_intake.client_ip(_Req(None)) == "127.0.0.1"


def test_public_ref_is_unguessable_and_unique():
    import secrets

    refs = {secrets.token_urlsafe(public_intake.PUBLIC_REF_BYTES) for _ in range(2000)}
    assert len(refs) == 2000
    assert all(len(r) >= 12 for r in refs)


# ---------------------------------------------------------------------------
# A stranger can read only their own report, and only part of it
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_lookup_returns_only_allowlisted_fields(db):
    async with client() as c:
        ref = (await submit(c)).json()["data"]["public_ref"]
        res = await c.get(f"/api/public/feedback/{ref}", headers={"x-forwarded-for": IP_A})

    assert res.status_code == 200
    data = res.json()["data"]
    # Decision 0017: a Customer never sees the AI labels, so topic and severity
    # left the allowlist along with everything else internal.
    assert set(data) == {"public_ref", "status", "created_at"}
    for leaked in (
        "user_id", "submitter_hash", "retention_until", "text", "confidence",
        "topic", "severity", "sentiment", "redacted_at",
    ):
        assert leaked not in data


@pytest.mark.asyncio
async def test_status_reflects_review_progress(db):
    async with client() as c:
        ref = (await submit(c)).json()["data"]["public_ref"]
        row = db.tables["feedback"][0]

        got = await c.get(f"/api/public/feedback/{ref}")
        assert got.json()["data"]["status"] == "under_review"

        row["needs_review"] = False
        got = await c.get(f"/api/public/feedback/{ref}")
        assert got.json()["data"]["status"] == "received"

        row["reviewed"] = True
        got = await c.get(f"/api/public/feedback/{ref}")
        assert got.json()["data"]["status"] == "reviewed"


@pytest.mark.asyncio
async def test_unknown_reference_is_404(db):
    async with client() as c:
        res = await c.get("/api/public/feedback/does-not-exist", headers={"x-forwarded-for": IP_A})
    assert res.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "gone",
    [
        {"retention_until": "2000-01-01T00:00:00+00:00"},  # past its retention deadline
        {"redacted_at": "2026-09-27T03:00:00+00:00"},       # text already wiped
    ],
)
async def test_expired_or_redacted_reference_is_404_like_unknown(db, gone):
    """Same answer as a code that never existed, so the endpoint is not an oracle."""
    async with client() as c:
        ref = (await submit(c)).json()["data"]["public_ref"]
        db.tables["feedback"][0].update(gone)
        res = await c.get(f"/api/public/feedback/{ref}")
        unknown = await c.get("/api/public/feedback/never-issued")

    assert res.status_code == 404
    assert res.json() == unknown.json()


@pytest.mark.asyncio
async def test_one_reference_never_reveals_another(db):
    async with client() as c:
        first = (await submit(c, text="phản hồi thứ nhất")).json()["data"]["public_ref"]
        second = (await submit(c, text="phản hồi thứ hai")).json()["data"]["public_ref"]

        res = await c.get(f"/api/public/feedback/{first}")

    assert res.json()["data"]["public_ref"] == first
    assert second not in res.text


@pytest.mark.asyncio
async def test_status_lookup_is_rate_limited(db, monkeypatch):
    """Enumeration guard: the reference space is large, but not a free oracle."""
    monkeypatch.setattr(public_intake.public_status_limit, "max_requests", 2)

    async with client() as c:
        for _ in range(2):
            await c.get("/api/public/feedback/nope", headers={"x-forwarded-for": IP_A})
        res = await c.get("/api/public/feedback/nope", headers={"x-forwarded-for": IP_A})

    assert res.status_code == 429


def test_derive_status_mapping():
    # "reviewed" means staff checked the AI label, not that the problem is fixed
    # (CONTEXT.md: Feedback status). The old "resolved" over-promised.
    assert public_intake.derive_status({"reviewed": True, "needs_review": True}) == "reviewed"
    assert public_intake.derive_status({"needs_review": True}) == "under_review"
    assert public_intake.derive_status({}) == "received"


# ---------------------------------------------------------------------------
# Opening the door did not open it wider than intended
# ---------------------------------------------------------------------------


GUARDS = {"get_current_user", "require_admin", "require_manager", "require_ops_staff"}


def iter_api_routes(node):
    """Walk every APIRoute, including ones behind an included router.

    FastAPI nests an included router as a single `_IncludedRouter` entry in
    `app.routes` rather than flattening it, so a shallow scan silently misses
    every routed module — exactly the routes this test exists to check.
    """
    for route in getattr(node, "routes", []):
        if hasattr(route, "dependant"):
            yield route
        elif hasattr(route, "original_router"):
            yield from iter_api_routes(route.original_router)


def test_public_routes_are_the_only_new_unguarded_ones():
    """`/` and `/health` were already unauthenticated status probes.

    Anything else showing up here means a guard was dropped by accident.
    """
    unguarded = set()
    for route in iter_api_routes(app):
        names = {
            d.call.__name__ for d in route.dependant.dependencies if getattr(d, "call", None)
        }
        if not names & GUARDS:
            unguarded.add(route.path)

    assert "/api/public/feedback" in unguarded
    assert "/api/public/feedback/{public_ref}" in unguarded
    # Sanity: the walker really does reach included routers.
    assert any(r.path.startswith("/api/users") for r in iter_api_routes(app))
    assert unguarded <= {
        "/",
        "/health",
        "/api/public/feedback",
        "/api/public/feedback/{public_ref}",
    }


ROLE_GUARDS = GUARDS - {"get_current_user"}


def test_only_api_me_accepts_any_authenticated_role():
    """Decision 0017: a Pending account reaches nothing but `/api/me` and changing
    its own password (`/api/me/password`, also the only way out of a temporary one).

    `get_current_user` alone only proves a valid JWT; a Pending account passes
    it. Every other authenticated route must sit behind a role guard, so a new
    route written with bare `get_current_user` fails here instead of quietly
    serving Pending accounts.
    """
    identity_only = set()
    for route in iter_api_routes(app):
        names = {
            d.call.__name__ for d in route.dependant.dependencies if getattr(d, "call", None)
        }
        if "get_current_user" in names and not names & ROLE_GUARDS:
            identity_only.add(route.path)

    assert identity_only == {"/api/me", "/api/me/password"}

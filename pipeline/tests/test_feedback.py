import pytest
from httpx import AsyncClient, ASGITransport

import classifier
import main
from main import app
from auth_guard import get_current_user, AuthUser
from tests._fakedb import FakeDB

# Decision 0017: submitting through the authenticated route is a Staff account
# action (the old guest tier is gone; Customers use the Customer web).
STAFF = AuthUser(id="test_user", email="test@test.com", role="staff", department="CSKH")


@pytest.fixture
def as_staff(monkeypatch):
    # In-memory DB: this test used to reach the real Supabase from the root .env.
    fake = FakeDB(feedback=[])
    monkeypatch.setattr(main, "get_supabase", lambda: fake)
    monkeypatch.setattr(classifier, "predict_feedback", lambda _t: {
        "topic": "Driver Behavior", "sentiment": "positive", "severity": "P1", "confidence": 0.9,
    })
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: STAFF
    yield fake
    if prev is None:
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides[get_current_user] = prev


@pytest.mark.asyncio
async def test_feedback_submit(as_staff):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "text": "Tài xế lái xe rất an toàn và thân thiện",
            "channel": "app",
            "area": "HN-Cầu Giấy"
        }
        response = await client.post("/api/feedback/submit", json=payload)
        assert response.status_code == 200
        row = as_staff.tables["feedback"][0]
        assert row["user_id"] == "test_user"
        assert row["source"] == "manual"

        # Missing text
        response_bad = await client.post("/api/feedback/submit", json={"channel": "app"})
        assert response_bad.status_code == 400

import pytest
from httpx import AsyncClient, ASGITransport

import main
from main import app


@pytest.fixture(autouse=True)
def _clear_health_db_cache():
    main._health_db_cache = (0.0, False, None)
    yield
    main._health_db_cache = (0.0, False, None)


class _OkDb:
    def table(self, _name):
        return self

    def select(self, *_a, **_kw):
        return self

    def limit(self, _n):
        return self

    def execute(self):
        return type("R", (), {"data": []})()


@pytest.mark.asyncio
async def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(main, "get_supabase", lambda: _OkDb())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data
        assert data["routing_taxonomy_loaded"] is True
        assert data["routing_routes"] == 7
        assert data["database"]["status"] == "ok"
        assert isinstance(data["database"]["latency_ms"], int)


@pytest.mark.asyncio
async def test_health_reports_degraded_when_supabase_down(monkeypatch):
    def _boom():
        raise RuntimeError("postgresql://user:secret@db.example.co:5432 unreachable")

    monkeypatch.setattr(main, "get_supabase", _boom)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        # Still 200 — Railway must not restart the container over a DB outage.
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == {"status": "error", "latency_ms": None}
        # The driver error may carry the DSN; /health is public, so it must not leak.
        assert "secret" not in response.text


@pytest.mark.asyncio
async def test_health_db_probe_is_cached(monkeypatch):
    calls = []

    def _counting():
        calls.append(1)
        return _OkDb()

    monkeypatch.setattr(main, "get_supabase", _counting)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/health")
        await client.get("/health")
    assert len(calls) == 1

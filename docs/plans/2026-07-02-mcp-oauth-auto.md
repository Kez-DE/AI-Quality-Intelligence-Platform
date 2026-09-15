# MCP OAuth tự động theo tài khoản — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Nhân viên kết nối MCP bằng đăng nhập tài khoản xanhSM qua browser (OAuth), không tạo/copy token; xóa trang self-service token.

**Architecture:** Supabase project bật OAuth 2.1 Server làm Authorization Server; `mcp_http.py` chuyển từ AuthMiddleware tự chế sang mô hình Resource Server chuẩn của MCP SDK (`token_verifier` + `AuthSettings`) — SDK tự lo 401/WWW-Authenticate/discovery metadata để Claude client tự mở browser đăng nhập. Verifier thử JWT Supabase trước (OAuth token là JWT Supabase chuẩn, `sub`=user id), fallback bảng `mcp_tokens` (máy-tới-máy). Quyền vẫn resolve LIVE từ `profiles` qua `_identity_from_profile` sẵn có.

**Tech Stack:** Python 3.12, `mcp` SDK 1.28.1 (FastMCP, `mcp.server.auth`), Supabase (Auth + OAuth 2.1 Server), Railway.

**Spec:** `docs/superpowers/specs/2026-07-02-mcp-oauth-auto-design.md`
**Nhánh:** `feat/mcp-server-and-improvements` (PR #18 — làm tiếp trên đây).

Đã xác minh trước (không cần kiểm lại): `FastMCP.custom_route` tồn tại; `AuthSettings` bắt buộc `issuer_url`+`resource_server_url`; `AccessToken` bắt buộc `token`+`client_id`+`scopes`, có field `claims`; `get_access_token()` import từ `mcp.server.auth.middleware.auth_context`.

---

## Task 0: Bật OAuth 2.1 Server trên Supabase project

**Không sửa code.** Project ref: `fkopgtacyuejfzzfgtau`.

**Step 1:** Thử qua CLI/Management API:

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform
supabase config --help          # xem có push config auth không
# Nếu CLI hỗ trợ: thêm vào supabase/config.toml mục oauth server rồi `supabase config push`
# Song song: thử Management API
curl -s -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  https://api.supabase.com/v1/projects/fkopgtacyuejfzzfgtau/config/auth | head -c 2000
# (SUPABASE_ACCESS_TOKEN: `supabase login` đã có sẵn — lấy từ `supabase projects list` hoạt động được)
```

**Step 2:** Nếu config có field OAuth server → bật `enabled` + `dynamic client registration` qua PATCH. Nếu KHÔNG có đường API → DỪNG task, báo người vận hành bấm dashboard: **Authentication → OAuth Server → Enable + bật Dynamic Client Registration**, rồi mới làm tiếp.

**Step 3:** Verify discovery của Supabase:

```bash
curl -s https://fkopgtacyuejfzzfgtau.supabase.co/.well-known/oauth-authorization-server/auth/v1 | python3 -m json.tool | head -20
```
Expected: JSON có `issuer`, `authorization_endpoint`, `token_endpoint`, `registration_endpoint`.

**Không commit gì (task hạ tầng).**

---

## Task 1: `SupabaseTokenVerifier` trong `mcp_auth.py` (TDD)

**Files:**
- Modify: `pipeline/mcp_auth.py`
- Test: `pipeline/tests/test_mcp_auth.py` (thêm class test mới, giữ test cũ)

**Step 1: Viết test thất bại** — thêm vào cuối `pipeline/tests/test_mcp_auth.py`:

```python
# ── SupabaseTokenVerifier: JWT Supabase trước, fallback bearer mcp_tokens ──
import asyncio


class _FakeAuthResult:
    def __init__(self, uid):
        class U: id = uid
        self.user = U() if uid else None


class _JwtDB(_DB):
    """Fake db có .auth.get_user: jwt hợp lệ 'jwt-good' → user u1."""
    def __init__(self, by_table, jwt_uid=None):
        super().__init__(by_table)
        outer = self
        class Auth:
            def get_user(self, token):
                if token == "jwt-good" and jwt_uid:
                    return _FakeAuthResult(jwt_uid)
                raise ValueError("bad jwt")
        self.auth = Auth()


def _verify(verifier, token):
    return asyncio.run(verifier.verify_token(token))


def test_verifier_supabase_jwt_maps_profile():
    db = _JwtDB({"profiles": [{"role": "staff", "department": "CSKH"}]}, jwt_uid="u1")
    v = a.SupabaseTokenVerifier(db=db)
    at = _verify(v, "jwt-good")
    assert at is not None
    assert at.claims == {"role": "staff", "scope_team": "CSKH"}
    assert at.client_id == "supabase-user:u1"


def test_verifier_falls_back_to_bearer_table():
    db = _JwtDB({
        "mcp_tokens": [{"id": "t1", "user_id": "u1"}],
        "profiles": [{"role": "admin", "department": None}],
    })  # jwt_uid=None → get_user luôn raise → rơi xuống bearer
    v = a.SupabaseTokenVerifier(db=db)
    at = _verify(v, "raw-bearer")
    assert at is not None and at.claims == {"role": "admin", "scope_team": None}


def test_verifier_rejects_garbage():
    v = a.SupabaseTokenVerifier(db=_JwtDB({}, jwt_uid=None))
    assert _verify(v, "garbage") is None
    assert _verify(v, "") is None
```

**Step 2:** Run: `cd pipeline && .venv/bin/python -m pytest tests/test_mcp_auth.py -q`
Expected: FAIL — `mcp_auth` chưa có `SupabaseTokenVerifier`.

**Step 3: Implement** — thêm vào cuối `pipeline/mcp_auth.py`:

```python
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
        # 1) JWT Supabase (OAuth hoặc session thường)
        try:
            result = db.auth.get_user(token)
            user = getattr(result, "user", None)
            uid = getattr(user, "id", None)
            if uid:
                profs = (
                    db.table("profiles").select("role,department")
                    .eq("id", uid).limit(1).execute().data or []
                )
                if profs:
                    ident = _identity_from_profile(
                        profs[0].get("role"), profs[0].get("department"))
                    return AccessToken(
                        token=token, client_id=f"supabase-user:{uid}",
                        scopes=[], claims=dict(ident))
                return None  # có JWT nhưng không có profile → từ chối
        except Exception:
            pass  # không phải JWT hợp lệ → thử bearer
        # 2) Bearer bảng mcp_tokens
        ident = verify_token(token, db=db)
        if ident:
            return AccessToken(token=token, client_id="mcp-bearer-token",
                               scopes=[], claims=dict(ident))
        return None
```

**Step 4:** Run: `cd pipeline && .venv/bin/python -m pytest tests/test_mcp_auth.py -q`
Expected: PASS (13 test).

**Step 5: Commit**

```bash
git add pipeline/mcp_auth.py pipeline/tests/test_mcp_auth.py
git commit -m "feat(mcp): SupabaseTokenVerifier — JWT Supabase (OAuth) + fallback bearer"
```

---

## Task 2: Rewire `mcp_http.py` sang SDK auth

**Files:**
- Rewrite: `pipeline/mcp_http.py`
- Test: `pipeline/tests/test_mcp_http.py` (viết lại — bỏ test AuthMiddleware cũ)

**Step 1: Viết lại test** — thay toàn bộ nội dung `pipeline/tests/test_mcp_http.py`:

```python
"""Test HTTP MCP (SDK auth): identity từ auth context + role gate + app build."""
import mcp_http
import mcp_server as m


def test_identity_reads_sdk_access_token(monkeypatch):
    class _AT:
        claims = {"role": "manager", "scope_team": "CSKH"}
    monkeypatch.setattr(mcp_http, "get_access_token", lambda: _AT())
    assert mcp_http._current_identity() == ("manager", "CSKH")


def test_identity_none_when_no_token(monkeypatch):
    monkeypatch.setattr(mcp_http, "get_access_token", lambda: None)
    assert mcp_http._current_identity() == (None, None)


def test_build_app_returns_asgi_app():
    app = mcp_http.build_app()
    assert callable(app)


def test_role_gate_blocks_disallowed_tool():
    out = m.call_tool("staff", "CSKH", "get_feedback_summary", {"days": 7})
    assert "không có quyền" in out


def test_unknown_role_has_no_tools():
    assert m.registered_tool_names(None) == []
    assert m.registered_tool_names("__hacker__") == []
```

**Step 2:** Run: `cd pipeline && .venv/bin/python -m pytest tests/test_mcp_http.py -q`
Expected: FAIL — `mcp_http` chưa có `get_access_token`/`_current_identity` dạng mới.

**Step 3: Viết lại `pipeline/mcp_http.py`:**

```python
"""HTTP MCP server — OAuth Resource Server (Supabase là Authorization Server).

Client kết nối KHÔNG cần token cấu hình sẵn:
  claude mcp add --transport http xanhsm <URL>/mcp
Lần đầu dùng → SDK trả 401 + WWW-Authenticate → client mở browser đăng nhập
tài khoản Supabase (xanhSM) → token OAuth (JWT Supabase) → verifier resolve
quyền LIVE từ profiles. Bearer bảng mcp_tokens vẫn nhận (máy-tới-máy).

Chạy: `PORT=8000 .venv/bin/python mcp_http.py` → MCP tại /mcp, health tại /health.
"""
import os

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_auth import SupabaseTokenVerifier
from mcp_server import make_tool_handlers, _description_for

SUPABASE_ISSUER = (os.environ.get("SUPABASE_URL", "").rstrip("/") or
                   "https://fkopgtacyuejfzzfgtau.supabase.co") + "/auth/v1"
PUBLIC_URL = os.environ.get(
    "MCP_PUBLIC_URL", "https://mcp-http-production-ffd0.up.railway.app/mcp")

_ALL_TOOLS = [
    "get_feedback_summary", "get_hot_areas", "get_sla_tickets",
    "get_team_priority_tasks", "search_knowledge_base", "submit_feedback",
]


def _current_identity():
    at = get_access_token()
    if at is None or not getattr(at, "claims", None):
        return (None, None)
    return (at.claims.get("role"), at.claims.get("scope_team"))


def build_app():
    server = FastMCP(
        "xanhsm-quality",
        stateless_http=True,
        json_response=True,
        token_verifier=SupabaseTokenVerifier(),
        auth=AuthSettings(issuer_url=SUPABASE_ISSUER,
                          resource_server_url=PUBLIC_URL),
    )

    @server.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    handlers = make_tool_handlers(_current_identity)
    for name in _ALL_TOOLS:
        server.add_tool(handlers[name], name=name, description=_description_for(name))
    return server.streamable_http_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(build_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
```

> Lưu ý khi implement: nếu `AuthSettings` từ chối URL không có path chuẩn hoặc `custom_route` bị auth chặn, chạy thử `build_app()` ngay để phát hiện; `/health` phải trả 200 KHÔNG cần token (nếu SDK auth chặn custom_route → bọc lại bằng wrapper 5 dòng chỉ cho /health như bản cũ).

**Step 4:** Run:
```bash
cd pipeline && .venv/bin/python -m pytest tests/test_mcp_http.py tests/test_mcp_server.py -q
.venv/bin/python -c "import mcp_http; app = mcp_http.build_app(); print('OK', type(app).__name__)"
```
Expected: PASS + in `OK`.

**Step 5: Smoke local** — chạy server + kiểm 3 điều:

```bash
cd pipeline && PORT=8899 .venv/bin/python mcp_http.py &  # nhớ kill sau
sleep 3
curl -s -o /dev/null -w "health %{http_code}\n" http://127.0.0.1:8899/health         # 200
curl -s -o /dev/null -w "mcp-noauth %{http_code}\n" -X POST http://127.0.0.1:8899/mcp # 401
curl -si -X POST http://127.0.0.1:8899/mcp | grep -i "www-authenticate"               # có resource_metadata
curl -s http://127.0.0.1:8899/.well-known/oauth-protected-resource/mcp | head -c 300  # JSON trỏ issuer Supabase (path có thể là /.well-known/oauth-protected-resource — thử cả hai)
kill %1
```

**Step 6: E2E local bằng JWT thật** (password-grant demo admin — mô phỏng đúng token OAuth vì cùng là JWT Supabase):

```bash
cd pipeline
# lấy JWT: dùng đoạn python login password-grant như đã làm (manhnguyn1912@gmail.com / 12345678)
# rồi client mcp streamablehttp_client với header Authorization: Bearer <JWT>
# Expected: list_tools ra 6 tool; get_hot_areas trả dữ liệu; JWT của staff bị chặn tool cấp điều hành
```

**Step 7: Commit**

```bash
git add pipeline/mcp_http.py pipeline/tests/test_mcp_http.py
git commit -m "feat(mcp): mcp_http chuyển sang OAuth Resource Server (SDK auth), Supabase là AS"
```

---

## Task 3: Xóa luồng token self-service

**Files:**
- Delete: `app/src/routes/_authenticated/mcp-connect.tsx`
- Modify: `app/src/components/AppShell.tsx` (bỏ nav item + import `Plug`)
- Modify: `pipeline/main.py` (bỏ endpoint `POST /api/mcp/token`)
- `app/src/routeTree.gen.ts` tự regen khi chạy tsc/vite (nếu không, xóa entry mcp-connect thủ công theo pattern)

**Step 1:** `rm app/src/routes/_authenticated/mcp-connect.tsx`

**Step 2:** Trong `AppShell.tsx` xóa dòng `{ to: "/mcp-connect", ... }` và `Plug,` trong import lucide.

**Step 3:** Trong `pipeline/main.py` xóa nguyên hàm `create_my_mcp_token` (từ `@app.post("/api/mcp/token")` tới trước `@app.get("/")`).

**Step 4:** Verify:
```bash
cd app && npx tsc --noEmit          # exit 0, routeTree tự regen bỏ mcp-connect
cd ../pipeline && .venv/bin/python -m pytest -q   # full suite xanh
grep -rn "mcp-connect\|/api/mcp/token" ../app/src ../pipeline --include="*.py" --include="*.tsx" | grep -v routeTree  # rỗng
```

**Step 5: Commit**

```bash
git add -A app/src pipeline/main.py
git commit -m "feat(mcp)!: bỏ luồng token self-service — OAuth thay thế (UI + endpoint)"
```

---

## Task 4: Deploy Railway + E2E remote

**Step 1:** `cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && railway up --service mcp-http --ci`
(Biến env đã có sẵn trên service; `MCP_PUBLIC_URL` mặc định trong code đã đúng URL production.)

**Step 2:** Verify remote:
```bash
URL=https://mcp-http-production-ffd0.up.railway.app
curl -s -o /dev/null -w "health %{http_code}\n" $URL/health        # 200
curl -si -X POST $URL/mcp | grep -iE "^HTTP|www-authenticate"      # 401 + resource metadata
# E2E: JWT password-grant demo → streamablehttp_client → list tools + call get_hot_areas
# Staff JWT → tool cấp điều hành bị chặn
```

**Step 3:** Đăng ký lại kết nối Claude của repo này theo kiểu OAuth (không header):
```bash
claude mcp remove xanhsm-quality-remote
claude mcp add --transport http xanhsm-quality-remote https://mcp-http-production-ffd0.up.railway.app/mcp
claude mcp list   # kỳ vọng: hiện trạng thái cần authenticate (⚠/needs auth) — bước login browser do người dùng làm
```

**Không commit (task hạ tầng).**

---

## Task 5: Docs + harness

**Files:**
- Modify: `docs/project/mcp-server.md` — viết lại mục "Lấy token"/"Cấu hình client" thành luồng OAuth (một lệnh, browser login); bearer chỉ còn máy-tới-máy do admin cấp CLI.
- Create: `docs/harness/decisions/0011-mcp-oauth-supabase.md` (theo template; context/decision/alternatives: giữ bearer-only, OAuth AS tự viết — loại; consequences: bước browser 1 lần, phụ thuộc feature OAuth server Supabase).
- Modify: `WORKLOG.md` — mục mới 2026-07-02 (OAuth flow, xóa self-service UI, verify gì).
- Run: `./scripts/bin/harness-cli decision add --id 0011 --title "MCP OAuth qua Supabase OAuth 2.1 Server" --status accepted --doc docs/harness/decisions/0011-mcp-oauth-supabase.md --verify "<kết quả e2e>"`

**Commit:**
```bash
git add docs WORKLOG.md
git commit -m "docs(mcp): OAuth flow — decision 0011, hướng dẫn kết nối mới, WORKLOG"
```

---

## Task 6: Cập nhật PR #18

```bash
git push
gh pr edit 18 --body "<bổ sung mục OAuth: luồng mới, xóa self-service UI, verify>"
cd pipeline && .venv/bin/python -m pytest -q   # xanh lần cuối
cd ../app && npx tsc --noEmit
```

## Thứ tự & phụ thuộc

Task 0 (Supabase) → Task 1 → Task 2 → Task 3 (song song được với 2 sau khi 1 xong) → Task 4 → Task 5 → Task 6.
Task 0 có thể BLOCK nếu OAuth Server bắt buộc bật qua dashboard — khi đó dừng, báo người vận hành, làm Task 1–3 trước trong lúc chờ.

## Verify tổng

- Full pytest xanh; tsc xanh.
- Remote: 401 + WWW-Authenticate đúng; JWT thật gọi tool đúng scope; staff bị role gate.
- `claude mcp add` không header nhận diện OAuth.
- Không còn tham chiếu `mcp-connect`/`/api/mcp/token` trong code.

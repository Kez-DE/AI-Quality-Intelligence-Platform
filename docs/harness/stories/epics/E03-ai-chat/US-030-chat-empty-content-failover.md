# US-030 Chat agent never surfaces an empty AI reply

## Status

implemented

## Lane

normal

## Product Contract

`POST /api/agent/chat` must always return a non-empty `content` (or route the
turn through provider failover / mock) instead of silently succeeding with an
empty reply. Users must never see "AI không trả về nội dung." for a normal,
non-error follow-up turn.

## Relevant Product Docs

- None dedicated to AI Chat yet; behavior lives in `pipeline/agent/model_router.py`
  and `pipeline/agent/chat_agent.py`.

## Acceptance Criteria

- `chat_completion` treats an LLM message with no `content` and no `tool_calls`
  as a failure (raises), instead of returning `""` as a successful reply.
- `chat_completion` treats an OpenRouter-embedded `choices[0].error` (HTTP 200
  with an upstream/rate-limit error inside the payload) as a failure the same way.
- Both failure modes retry the same provider (bounded) before falling over to
  the next provider in the chain, ending at `mock` which never fails.

## Design Notes

- Root cause: reasoning-capable models routed through OpenRouter
  (`google/gemini-2.5-flash-lite`) can spend their entire completion on hidden
  reasoning tokens and stop (`finish_reason: "stop"`) without ever emitting
  visible `content` or a `tool_calls` entry. Reproduced live: ~25% empty-reply
  rate on a realistic 2-turn admin chat ("Tổng quan..." → "chi tiết tổng quan
  hệ thống"), confirmed via raw OpenRouter response showing
  `reasoning_tokens: 302`, `content: null`, `tool_calls: null`.
- Fix applied at the single shared choke point all agent LLM calls already
  route through (`_extract_chat_response` in `pipeline/agent/model_router.py`),
  not in the individual callers (chat route, chat_agent, insight_agent, etc.),
  so every caller of `chat_completion` gets the guard for free.
- Commands: none (backend service logic only).
- Queries: none.
- API: `POST /api/agent/chat` (no shape change — failure now fails over
  instead of returning an empty 200 payload).
- Tables: none.
- Domain rules: n/a.
- UI surfaces: `app/src/routes/_authenticated/chat.tsx` (no change needed —
  it already surfaces `reply.data.content` correctly; the bug was upstream).

## Harness Delta

None — existing retry/failover machinery in `model_router.py` was reused as-is.

## Validation

`scripts/bin/harness-cli story update --id US-030 --unit 1 --integration 0 --e2e 0 --platform 0`

| Layer | Expected proof |
| --- | --- |
| Unit | `pipeline/tests/test_model_router_empty_response.py` (new) + `pipeline/tests/test_model_router_privacy.py` (regression) |
| Integration | Manual: live 2-turn admin chat repro against OpenRouter, 5/5 trials returned non-empty content after the fix (previously ~25% empty) |
| E2E | Skipped — no browser harness for this story |
| Platform | n/a |

## Evidence

- `cd pipeline && source .venv/bin/activate && python3 -m pytest tests/ -q` → `136 passed, 3 skipped, 2 xfailed`
- Live repro script (2-turn admin chat, temperature=0.4, 5 trials post-fix): all 5 returned non-empty `content` (previously reproduced a `content: ""` failure on the same input pre-fix).

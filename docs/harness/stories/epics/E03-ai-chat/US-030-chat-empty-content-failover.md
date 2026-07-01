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
- Retrying an empty-content failure must not add exponential backoff sleep —
  it's a stochastic generation fluke, not server throttling, so waiting only
  burns time toward the frontend's request timeout for no benefit.
- The OpenRouter call caps hidden reasoning tokens so a single call can't burn
  its whole budget "thinking" with nothing left to emit — this bounds latency
  and independently reduces how often the empty-reply case happens at all.
- The chat request from the frontend gets a longer abort timeout than the
  default, since an agentic multi-tool-call turn can legitimately take longer
  than a plain API call.

## Design Notes

- Root cause 1 (bug report): reasoning-capable models routed through
  OpenRouter (`google/gemini-2.5-flash-lite`) can spend their entire completion
  on hidden reasoning tokens and stop (`finish_reason: "stop"`) without ever
  emitting visible `content` or a `tool_calls` entry. Reproduced live: ~25%
  empty-reply rate on a realistic 2-turn admin chat ("Tổng quan..." → "chi
  tiết tổng quan hệ thống"), confirmed via raw OpenRouter response showing
  `reasoning_tokens: 302`, `content: null`, `tool_calls: null`.
- Root cause 2 (regression found while verifying fix 1): the first fix added
  exponential-backoff retries (1s/2s/4s) on empty-content failures. Reasoning
  calls that fail this way, or just run long, can legitimately take 8-13s+ on
  their own; stacking a second full attempt plus backoff sleep pushed total
  latency to 12-30s in testing, past the frontend's 15s `AbortController`
  timeout in `app/src/lib/api.ts`, producing a client-side "signal is aborted
  without reason" instead of the original empty-content error. Fixed by (a)
  dropping the backoff sleep for this specific failure (immediate retry only),
  (b) capping `reasoning.max_tokens` to 400 on the OpenRouter call so calls are
  both faster and less likely to come back empty in the first place (0/8 empty
  and ~3s/call across spaced-out live trials), and (c) raising the frontend
  timeout for the chat endpoint specifically to 45s as defense-in-depth, since
  a multi-tool-call ReAct loop can legitimately need more than 15s regardless.
- Fix applied at the single shared choke point all agent LLM calls already
  route through (`_extract_chat_response` / `_call_provider` in
  `pipeline/agent/model_router.py`), not in the individual callers (chat
  route, chat_agent, insight_agent, etc.), so every caller of
  `chat_completion` gets the guard for free.
- Commands: none (backend service logic only).
- Queries: none.
- API: `POST /api/agent/chat` (no shape change — failure now fails over
  instead of returning an empty 200 payload).
- Tables: none.
- Domain rules: n/a.
- UI surfaces: `app/src/routes/_authenticated/chat.tsx` (added an explicit
  45s timeout to the `apiFetch` call for this endpoint via a new optional
  `timeoutMs` param on `apiFetch` in `app/src/lib/api.ts`, default unchanged
  at 15s for every other call site).

## Harness Delta

None — existing retry/failover machinery in `model_router.py` was reused as-is.

## Validation

`scripts/bin/harness-cli story update --id US-030 --unit 1 --integration 0 --e2e 0 --platform 0`

| Layer | Expected proof |
| --- | --- |
| Unit | `pipeline/tests/test_model_router_empty_response.py` (new) + `pipeline/tests/test_model_router_privacy.py` (regression) + `tsc --noEmit` clean on `app/` |
| Integration | Manual: live 2-turn admin chat repro against OpenRouter, 10/10 trials returned non-empty content post-fix (previously ~25% empty), worst-case latency 12.5s (previously up to 29.9s with the interim retry-only fix) |
| E2E | Skipped — no browser harness for this story |
| Platform | n/a |

## Evidence

- `cd pipeline && source .venv/bin/activate && python3 -m pytest tests/ -q` → `136 passed, 3 skipped, 2 xfailed`
- `cd app && npx tsc --noEmit` → clean
- Live repro script (2-turn admin chat, temperature=0.4): pre-fix ~25% empty
  rate; interim fix (retry only, no reasoning cap) still hit 12.4-29.9s
  latency spikes; final fix (reasoning cap + no backoff on this retry path)
  gave 10/10 non-empty replies, worst case 12.5s, typical 3-10s.

---
description: "AI usage logging is local-only and fully automatic — do NOT call any log_* script manually"
activation: always-on
---

# AI Usage Logging — Tự động, CHỈ LƯU LOCAL

Log prompt vào `.ai-log/session.jsonl` được **tự động hoá hoàn toàn** qua hook của từng
AI client. **Không có bất kỳ đường đẩy dữ liệu nào ra server bên ngoài** — phần
submit ra ngoài (`scripts/submit_log.py`, pre-push hook, `AI_LOG_SERVER`,
`AI_LOG_API_KEY`) đã bị gỡ bỏ.

## Cơ chế

Hook của Claude Code (`.claude/settings.json`), Gemini CLI (`.gemini/settings.json`),
Cursor (`.cursor/hooks.json`), Codex (`.codex/hooks.json`) và Copilot
(`.github/hooks/hooks.json`) gọi `scripts/log_hook.py`, ghi append một dòng JSON
vào `.ai-log/session.jsonl`. Hết. Không POST, không network.

Prompt từ Antigravity IDE có thể sweep thủ công từ transcript trên disk bằng
`bash scripts/_pyrun.sh scripts/log_antigravity.py --auto` — cũng chỉ ghi local.

## Không làm những việc sau

- ❌ **KHÔNG** gọi `scripts/log_antigravity.py "<summary>" "<model>"` sau mỗi task —
  sẽ tạo entry giả mạo dạng "TaskComplete", không phải prompt thật của user.
- ❌ **KHÔNG** cài lại pre-push hook hay tái tạo `scripts/submit_log.py`.
- ❌ **KHÔNG** set `AI_LOG_SERVER` / `AI_LOG_API_KEY` trong `.env`.

## Dọn log

`.ai-log/*.jsonl` và `.ai-log/archive/` đã nằm trong `.gitignore` — không bao giờ
được commit. Muốn xoá thì xoá trực tiếp, không còn script nào quản lý chúng.

# WORKLOG — C2-App-116

Nhật ký quyết định kỹ thuật, phân công và bug quan trọng của team 116.

## 2026-05-31

### Đề tài & stack
Chưa chốt. Team chưa thống nhất sản phẩm App-116 sẽ xây và ngôn ngữ/framework dùng.
TODO: ghi lại quyết định + lý do khi nhóm chốt (why approach này thay vì cái khác).

### Phân công
Chưa phân công. TODO: ai làm module nào, deadline nội bộ.

### Quy ước đang áp dụng (đề xuất của Kez, chờ nhóm xác nhận)
- Đặt tên branch theo dạng `<tên>/<task>`, mỗi branch một việc, xóa sau khi merge.
  Ví dụ: `kez/fix-codex-hooks`, `kez/init-docs`.
- Không push thẳng `main`. Mỗi thay đổi đi qua branch → PR → review → merge.
  (`main` hiện chưa bật branch protection; cần admin repo bật để ép luật này.)
- AI logging gắn theo từng cá nhân: mỗi thành viên tự `cp .env.example .env`
  + `bash scripts/setup_hooks.sh` trên máy mình và tự push phần của mình.
  Log stamp theo email git của từng người — nếu một người push hộ cả nhóm
  thì chỉ usage của người đó được ghi nhận.

### Bug quan trọng — `.codex/hooks.json` thiếu field `type`
- Triệu chứng: chạy `codex` trong repo báo lỗi
  `failed to parse hooks config .codex/hooks.json: missing field type`.
- Root cause: mỗi hook handler trong `.codex/hooks.json` chỉ có
  `{name, command, timeout}`, thiếu field bắt buộc `type`. Đối chiếu
  `.claude/settings.json` (chạy bình thường) thì mỗi handler đều có `"type": "command"`.
- Fix: thêm `"type": "command"` vào cả 2 handler (`log-prompt`, `log-stop`),
  theo schema chính thức tại developers.openai.com/codex/hooks → PR #1.
- Ghi chú: BTC đã cho phép team chủ động sửa scripts.

# Spec: Trích dẫn [Nguồn N] bấm được trong AI Chat

**Date:** 2026-07-03
**Lane:** Normal (frontend UI; không schema/auth/quyền/backend cho ops/admin)

## Bối cảnh & nguyên nhân

Trong AI Chat (ops/admin), câu trả lời có trích dẫn `[Nguồn N]` nhưng là **text thường,
không bấm được**. Dữ liệu đã sẵn: backend trả `sources` kèm **full `content`** cho mỗi nguồn
(đường agent `/api/agent/chat` → `chat_tools.search_knowledge_base sources_out`, key
`{index, title, heading, department, content}`). Frontend đã lưu `sources` theo từng tin nhắn.

Đây gần như thuần frontend (`app/src/routes/_authenticated/chat.tsx`).

**Bug đang tồn (sửa luôn):** panel "Nguồn tài liệu tham khảo" đọc `s.document_title` +
`s.similarity` (shape đường RAG), nhưng đường agent trả `title`/`content` (không có
`document_title`/`similarity`) → hiện "undefined" + "NaN%". Chuẩn hóa để đọc đúng cả hai shape.

## Thiết kế

Biến mỗi `[Nguồn N]` trong câu trả lời assistant thành **nút bấm** → mở **Popover** (Radix,
`components/ui/popover.tsx` đã có) hiển thị nguồn N: `title › heading`, phòng ban, và **full
content** (cuộn được nếu dài). Bấm ra ngoài để đóng.

- **Nguồn theo từng tin nhắn:** dùng `message.sources` của đúng tin nhắn chứa trích dẫn (bấm
  ở tin cũ vẫn ra đúng nguồn của tin đó), không phụ thuộc tin cuối.
- **Chuẩn hóa shape:** helper `srcTitle(s) = s.title || s.document_title || "Tài liệu nội bộ"`;
  `srcContent(s) = s.content || ""`; similarity chỉ hiện khi có (`typeof s.similarity === "number"`).
- **Map index → source:** `[Nguồn N]` khớp `sources.find(x => x.index === N)`, fallback
  `sources[N-1]`.
- **Panel bên phải:** giữ, sửa shape để hiện đúng title/content; bỏ NaN% khi thiếu similarity;
  mỗi thẻ cũng bấm mở popover/full content (đồng bộ với inline).

## Phạm vi
- Áp cho **ops/admin** (đường agent có structured sources).
- **Guest KHÔNG trong phạm vi lần này:** đường công khai chỉ chèn KB dạng text, backend chưa
  trả `sources` có cấu trúc cho guest → muốn khách bấm được cần sửa backend riêng (follow-up).

## Files
- Modify: `app/src/routes/_authenticated/chat.tsx` (render câu trả lời: parse `[Nguồn N]` →
  nút + Popover; helper chuẩn hóa; panel đọc đúng shape).
- Có thể tách 1 component nhỏ `SourceCitations`/`SourcePopover` trong cùng thư mục nếu chat.tsx
  phình — theo phán đoán khi implement (giữ file gọn).

## Validation
- `tsc --noEmit` sạch; `vitest` (nếu có test chat) pass.
- Render thủ công (dev server): hỏi câu có tra KB → câu trả lời có `[Nguồn 1]`... bấm được →
  popover hiện đúng title + full content của nguồn đó.
- Bấm `[Nguồn N]` ở tin nhắn CŨ (đã cuộn lên) → ra đúng nguồn của tin đó.
- Panel bên phải hiện đúng title (không "undefined"), không "NaN%".
- Guest: câu trả lời không có nút nguồn (không có structured sources) — không lỗi.
- Nếu `[Nguồn N]` mà không có source tương ứng → render text thường, không crash.

## Không đổi
- Backend ops/admin, schema, quyền, guest path, RAG engine.

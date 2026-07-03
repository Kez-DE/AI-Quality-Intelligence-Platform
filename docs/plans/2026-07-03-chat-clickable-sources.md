# Trích dẫn [Nguồn N] bấm được — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Biến `[Nguồn N]` trong câu trả lời AI Chat thành nút bấm → Popover hiện toàn văn nguồn; sửa shape panel nguồn.

**Architecture:** Frontend-only. `MarkdownContent` (react-markdown) nhận `components` override. Transform `[Nguồn N]` → link `[Nguồn N](#src-N)`; override `a` renderer bắt `#src-N` → Radix Popover hiện source N (title/heading/department/content). Thread `sources` từ `Msg` xuống. Chuẩn hóa key (`title||document_title`, similarity optional).

**Tech Stack:** React 19, react-markdown + remark-gfm, Radix Popover (`components/ui/popover.tsx`).

**Spec:** `docs/superpowers/specs/2026-07-03-chat-clickable-sources-design.md`
**Nhánh:** `feat/chat-clickable-sources` (off main).

Đã xác minh: `MarkdownContent({children, className, components})` merge components với default; `AssistantResponse` render block qua MarkdownContent; sources đường agent = `{index,title,heading,department,content}`; Popover & Dialog components có sẵn.

---

## Task 1: Citation bấm được + Popover + chuẩn hóa shape

**Files:**
- Create: `app/src/components/SourceCitation.tsx` (helper transform + `a`-renderer + Popover)
- Modify: `app/src/routes/_authenticated/chat.tsx` (thread `sources` xuống AssistantResponse/MarkdownContent; sửa panel shape)

**Step 1: Helper chuẩn hóa + transform** trong `SourceCitation.tsx`:
```tsx
export type ChatSource = {
  index?: number; title?: string; document_title?: string;
  heading?: string; department?: string; content?: string; similarity?: number;
};
export const srcTitle = (s: ChatSource) => s.title || s.document_title || "Tài liệu nội bộ";
export const srcContent = (s: ChatSource) => s.content || "";
/** [Nguồn 3] -> [Nguồn 3](#src-3) để react-markdown render thành link bắt được. */
export function linkifyCitations(md: string): string {
  return md.replace(/\[\s*Nguồn\s*(\d+)\s*\]/gi, (_m, n) => `[Nguồn ${n}](#src-${n})`);
}
```

**Step 2: `a`-renderer + Popover** — factory nhận `sources`, trả `components.a`:
```tsx
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
export function makeCitationComponents(sources: ChatSource[] | undefined) {
  return {
    a: ({ href, children }: any) => {
      const m = typeof href === "string" && href.match(/^#src-(\d+)$/);
      if (!m || !sources?.length) return <a href={href}>{children}</a>;
      const n = Number(m[1]);
      const s = sources.find((x) => x.index === n) || sources[n - 1];
      if (!s) return <>{children}</>;
      return (
        <Popover>
          <PopoverTrigger asChild>
            <button type="button" className="mx-0.5 inline-flex items-center rounded bg-xanh-green/15 px-1.5 text-xs font-semibold text-xanh-deep hover:bg-xanh-green/30 align-baseline">
              {children}
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-96 max-h-80 overflow-y-auto text-sm">
            <div className="font-semibold text-xanh-deep mb-0.5">{srcTitle(s)}{s.heading ? ` › ${s.heading}` : ""}</div>
            {s.department && <div className="text-xs text-muted-foreground mb-2">Phòng: {s.department}</div>}
            <p className="whitespace-pre-wrap text-foreground/85 text-xs leading-6">{srcContent(s)}</p>
          </PopoverContent>
        </Popover>
      );
    },
  };
}
```

**Step 3: Thread sources trong chat.tsx**
- `Bubble` và `AssistantResponse` nhận thêm prop `sources?: ChatSource[]` (từ `Msg.sources`). Truyền từ nơi render `<Bubble ... sources={m.sources} />`.
- Chỗ render nội dung qua `MarkdownContent`: đổi thành
  `<MarkdownContent components={makeCitationComponents(sources)}>{linkifyCitations(block.body)}</MarkdownContent>`
  (giữ nguyên các block khác; chỉ bọc phần body chứa citation).

**Step 4: Sửa panel nguồn (dòng ~512-517)** dùng helper:
- `{srcTitle(s)}{s.heading ? " - " + s.heading : ""}` thay `{s.document_title} - {s.heading}`.
- Chỉ hiện "Độ tương đồng" khi `typeof s.similarity === "number"` (bỏ NaN%).
- `{srcContent(s)}` thay `{s.content}`.

**Step 5: Verify**
```bash
cd app && npx tsc --noEmit    # exit 0
npx vitest run 2>&1 | tail -5 # 2 test cũ vẫn pass (smoke fail pre-existing không tính)
```

**Step 6: Manual (dev server)** — hỏi câu tra KB (vd "quy trình khiếu nại") → trả lời có `[Nguồn 1]` bấm được → popover hiện title + full content; bấm ở tin cũ vẫn đúng; panel hết "undefined"/"NaN%".

**Step 7: Commit**
```bash
git add app/src/components/SourceCitation.tsx app/src/routes/_authenticated/chat.tsx
git commit -m "feat(chat): trích dẫn [Nguồn N] bấm được (popover full content) + sửa shape panel nguồn"
```

---

## Task 2: Push + PR
```bash
git push -u origin feat/chat-clickable-sources
gh pr create --base main --title "feat(chat): trích dẫn [Nguồn N] bấm được trong AI Chat" --body "<nguyên nhân, popover, sửa panel shape, phạm vi ops/admin, verify tsc + manual>"
```

## Verify tổng
- `tsc` sạch; citation `[Nguồn N]` bấm ra popover đúng nguồn (theo từng tin nhắn).
- Panel nguồn hiện đúng title/content, không NaN%.
- `[Nguồn N]` thiếu source tương ứng → không crash (render text/label thường).
- Guest: không có nút nguồn (không structured sources) — không lỗi.

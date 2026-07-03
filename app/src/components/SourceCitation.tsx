import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

/** Nguồn trích dẫn trả về từ AI Chat. Đường agent dùng `title`, đường RAG dùng
 * `document_title`/`similarity` → chuẩn hóa qua helper để hiển thị đúng cả hai. */
export type ChatSource = {
  index?: number;
  title?: string;
  document_title?: string;
  heading?: string;
  department?: string;
  content?: string;
  similarity?: number;
};

export const srcTitle = (s: ChatSource) =>
  s.title || s.document_title || "Tài liệu nội bộ";
export const srcContent = (s: ChatSource) => s.content || "";

/** `[Nguồn 3]` -> `[Nguồn 3](#src-3)` để react-markdown render thành link bắt được. */
export function linkifyCitations(md: string): string {
  return md.replace(/\[\s*Nguồn\s*(\d+)\s*\]/gi, (_m, n) => `[Nguồn ${n}](#src-${n})`);
}

/** Trả về `components.a` cho MarkdownContent: link `#src-N` -> nút bấm mở Popover
 * hiện toàn văn nguồn N. Link khác giữ nguyên. Không có sources -> render text thường. */
export function makeCitationComponents(sources: ChatSource[] | undefined) {
  return {
    a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
      const m = typeof href === "string" ? href.match(/^#src-(\d+)$/) : null;
      if (!m || !sources?.length) {
        return href ? <a href={href}>{children}</a> : <>{children}</>;
      }
      const n = Number(m[1]);
      const s = sources.find((x) => x.index === n) || sources[n - 1];
      if (!s) return <>{children}</>;
      return (
        <Popover>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="mx-0.5 inline-flex items-center rounded bg-xanh-green/15 px-1.5 align-baseline text-xs font-semibold text-xanh-deep transition-colors hover:bg-xanh-green/30"
            >
              {children}
            </button>
          </PopoverTrigger>
          <PopoverContent className="max-h-80 w-96 overflow-y-auto text-sm">
            <div className="mb-0.5 font-semibold text-xanh-deep">
              {srcTitle(s)}
              {s.heading ? ` › ${s.heading}` : ""}
            </div>
            {s.department && (
              <div className="mb-2 text-xs text-muted-foreground">Phòng: {s.department}</div>
            )}
            <p className="whitespace-pre-wrap text-xs leading-6 text-foreground/85">
              {srcContent(s)}
            </p>
          </PopoverContent>
        </Popover>
      );
    },
  };
}

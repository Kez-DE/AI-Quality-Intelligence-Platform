import ReactMarkdown from "react-markdown";
import type { ComponentProps } from "react";
import remarkGfm from "remark-gfm";

type Components = NonNullable<ComponentProps<typeof ReactMarkdown>["components"]>;

const defaultComponents: Components = {
  h1: ({ children }) => (
    <h1 className="mb-4 text-xl font-bold text-xanh-deep sm:text-2xl">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-3 mt-7 border-b border-border pb-2 text-lg font-semibold text-xanh-deep">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-2 mt-5 text-base font-semibold text-foreground">{children}</h3>
  ),
  p: ({ children }) => <p className="my-3 leading-7 text-foreground/85">{children}</p>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1 pl-6">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1 pl-6">{children}</ol>,
  li: ({ children }) => <li className="leading-6 text-foreground/85">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-4 border-xanh-green bg-muted/40 px-4 py-2 text-sm text-muted-foreground">
      {children}
    </blockquote>
  ),
  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
      <table className="min-w-full border-collapse text-left text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-muted/70">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-border">{children}</tbody>,
  tr: ({ children }) => <tr className="divide-x divide-border align-top">{children}</tr>,
  th: ({ children }) => (
    <th className="whitespace-nowrap px-3 py-2 font-semibold text-xanh-deep">{children}</th>
  ),
  td: ({ children }) => <td className="min-w-32 px-3 py-2 text-foreground/90">{children}</td>,
};

function stripListPrefix(line: string): string {
  return line.replace(/^(\s*)(?:[-*+]\s+|\d+[.)]\s+)(?=\|)/, "$1");
}

function normalizePipeGlyphs(line: string): string {
  return line.replace(/\uFF5C/g, "|");
}

function isPipeRow(line: string): boolean {
  const trimmed = stripListPrefix(normalizePipeGlyphs(line)).trim();
  if (!trimmed.includes("|")) return false;
  const cells = trimmed.split("|").filter((cell) => cell.trim().length > 0);
  return cells.length >= 2;
}

function normalizePipeRow(line: string): string {
  const indent = line.match(/^\s*/)?.[0] ?? "";
  const trimmed = stripListPrefix(normalizePipeGlyphs(line)).trim();
  if (!isPipeRow(trimmed)) return line;

  const withStart = trimmed.startsWith("|") ? trimmed : `| ${trimmed}`;
  return indent + (withStart.endsWith("|") ? withStart : `${withStart} |`);
}

function tableCells(row: string): string[] {
  return normalizePipeRow(row)
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isSeparatorRow(row: string): boolean {
  const cells = tableCells(row);
  return cells.length >= 2 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
}

function separatorFor(row: string): string {
  const columnCount = tableCells(row).length;
  return `| ${Array.from({ length: columnCount }, () => "---").join(" | ")} |`;
}

function unwrapFencedTables(markdown: string): string {
  return markdown.replace(/```(?:markdown|md|text)?[ \t]*\n([\s\S]*?)\n```/gi, (match, body) => {
    const pipeRows = body.split("\n").filter(isPipeRow);
    return pipeRows.length >= 2 ? body.trim() : match;
  });
}

export function normalizeMarkdownForRendering(markdown: string): string {
  const lines = unwrapFencedTables(markdown).split("\n");
  const output: string[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];

    if (!isPipeRow(line)) {
      output.push(normalizePipeGlyphs(line));
      continue;
    }

    const rows: string[] = [];
    while (index < lines.length && isPipeRow(lines[index])) {
      rows.push(normalizePipeRow(lines[index]));
      index += 1;
    }
    index -= 1;

    if (rows.length < 2) {
      output.push(...rows);
      continue;
    }

    if (output.length > 0 && output[output.length - 1].trim() !== "") {
      output.push("");
    }

    output.push(rows[0]);
    if (!isSeparatorRow(rows[1])) {
      output.push(separatorFor(rows[0]));
    }
    output.push(...rows.slice(1));

    if (index + 1 < lines.length && lines[index + 1].trim() !== "") {
      output.push("");
    }
  }

  return output
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function MarkdownContent({
  children,
  className,
  components,
}: {
  children?: string | null;
  className?: string;
  components?: Components;
}) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{ ...defaultComponents, ...components }}
      >
        {normalizeMarkdownForRendering(children ?? "")}
      </ReactMarkdown>
    </div>
  );
}

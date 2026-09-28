// Splits an assistant answer into the cards the staff chat shows (chat.tsx).
// Card titles render as plain text, so inline markdown is stripped from them.

export const MAX_ASSISTANT_BLOCKS = 6;

export type AssistantBlock = {
  title?: string;
  body: string;
};

/** Titles render as plain text: drop emphasis markers the model wraps them in. */
function cleanTitle(title: string): string {
  return title.replace(/\*\*|__/g, "").replace(/^[*_`]+|[*_`]+$/g, "").trim();
}
export function matchBlockTitle(line: string): string | null {
  const trimmed = line.trim();
  const markdownHeading = trimmed.match(/^#{1,6}\s+(.{2,90})$/);
  if (markdownHeading) return cleanTitle(markdownHeading[1]);

  const boldHeading = trimmed.match(/^\*\*([^*]{2,90})\*\*:?\s*$/);
  if (boldHeading) return cleanTitle(boldHeading[1]);

  const numberedHeading = trimmed.match(/^\d+\.\s+(.{2,90})$/);
  if (numberedHeading && !/[.!?]$/.test(numberedHeading[1].trim())) {
    return cleanTitle(numberedHeading[1]);
  }

  return null;
}

export function splitAssistantBlocks(content: string): AssistantBlock[] {
  const normalized = content.trim().replace(/\r\n/g, "\n");
  if (!normalized) return [];

  let blocks: AssistantBlock[] = [];
  let currentTitle: string | undefined;
  let currentLines: string[] = [];

  const pushCurrent = () => {
    const body = currentLines.join("\n").trim();
    if (!body && !currentTitle) return;
    blocks.push(body ? { title: currentTitle, body } : { body: currentTitle ?? "" });
    currentTitle = undefined;
    currentLines = [];
  };

  for (const rawLine of normalized.split("\n")) {
    const title = matchBlockTitle(rawLine);
    if (title) {
      pushCurrent();
      currentTitle = title;
    } else {
      currentLines.push(rawLine);
    }
  }
  pushCurrent();

  if (blocks.length <= 1) {
    const paragraphs = normalized
      .split(/\n{2,}/)
      .map((part) => part.trim())
      .filter(Boolean);
    if (paragraphs.length > 1) {
      blocks = paragraphs.map((body) => ({ body }));
    }
  }

  if (blocks.length <= 1 && normalized.length > 420) {
    const sentences =
      normalized
        .match(/[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$/g)
        ?.map((part) => part.trim())
        .filter(Boolean) ?? [];
    const chunks: string[] = [];
    let chunk = "";
    for (const sentence of sentences) {
      const next = chunk ? `${chunk} ${sentence}` : sentence;
      if (next.length > 360 && chunk) {
        chunks.push(chunk);
        chunk = sentence;
      } else {
        chunk = next;
      }
    }
    if (chunk) chunks.push(chunk);
    if (chunks.length > 1) {
      blocks = chunks.map((body) => ({ body }));
    }
  }

  if (blocks.length > MAX_ASSISTANT_BLOCKS) {
    const visible = blocks.slice(0, MAX_ASSISTANT_BLOCKS - 1);
    const rest = blocks.slice(MAX_ASSISTANT_BLOCKS - 1);
    blocks = [
      ...visible,
      {
        title: "Chi tiết bổ sung",
        body: rest
          .map((block) => [block.title, block.body].filter(Boolean).join("\n"))
          .join("\n\n"),
      },
    ];
  }

  return blocks.length ? blocks : [{ body: normalized }];
}

const MAX_TITLE = 48;

/**
 * Derive a plain-text sidebar title from the user's first question.
 * Markdown markers are stripped throughout, not just at the start, so a
 * question like `**Refund me** please` can't leave a lopsided `Refund me**`.
 */
export function titleFromQuestion(question: string): string {
  const cleaned = question
    .replace(/`+/g, '')            // code ticks
    .replace(/\*+/g, '')           // bold / italic
    .replace(/_{2,}/g, '')         // __bold__
    .replace(/^[\s"'“”>#\-–—]+/, '') // leading quotes, blockquote and heading marks
    .replace(/\s+/g, ' ')
    .trim();

  if (!cleaned) return 'New conversation';
  if (cleaned.length <= MAX_TITLE) return cleaned;

  // Prefer cutting at a word boundary.
  const cut = cleaned.slice(0, MAX_TITLE);
  const lastSpace = cut.lastIndexOf(' ');
  const base = lastSpace > MAX_TITLE * 0.5 ? cut.slice(0, lastSpace) : cut;
  return `${base.replace(/[.,;:!?\s]+$/, '')}…`;
}

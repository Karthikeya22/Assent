export type Span = { key: string; start: number; end: number };
export type Run = { text: string; key: string | null };

/**
 * Split `text` into runs, each either plain or belonging to one criterion's clause.
 * Spans are applied in order; a later span that overlaps an earlier one is clipped, never merged,
 * so every character belongs to at most one criterion.
 */
export function clauseRuns(text: string, spans: Span[]): Run[] {
  const owner: (string | null)[] = new Array(text.length).fill(null);
  for (const s of spans) {
    for (let i = Math.max(0, s.start); i < Math.min(text.length, s.end); i++) {
      if (owner[i] === null) owner[i] = s.key;
    }
  }
  const runs: Run[] = [];
  let start = 0;
  for (let i = 1; i <= text.length; i++) {
    if (i === text.length || owner[i] !== owner[start]) {
      runs.push({ text: text.slice(start, i), key: owner[start] });
      start = i;
    }
  }
  return runs;
}

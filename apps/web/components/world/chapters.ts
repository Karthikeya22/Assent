/**
 * The landing's scroll chapters (docs/design/storyboard.md). Pure: scroll offset + measured chapter
 * ranges -> which chapter is on screen and how far through it we are. The world reads `t`
 * (index + local) every frame; the DOM only re-renders when `index` changes.
 */
export const CHAPTERS = [
  "hero",
  "problem",
  "policy",
  "chart",
  "prove",
  "verify",
  "argue",
  "packet",
  "use",
  "proof",
  "close",
] as const;
export type ChapterId = (typeof CHAPTERS)[number];

/** Scroll offset (px) at which each chapter starts; the last chapter ends at `end`. */
export type Ranges = { starts: number[]; end: number };

export type Place = { index: number; local: number; t: number };

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

export function locate(y: number, r: Ranges): Place {
  const n = r.starts.length;
  if (n === 0) return { index: 0, local: 0, t: 0 };
  let i = 0;
  while (i < n - 1 && y >= r.starts[i + 1]) i++;
  const a = r.starts[i];
  const b = i < n - 1 ? r.starts[i + 1] : r.end;
  const local = b > a ? clamp01((y - a) / (b - a)) : 0;
  return { index: i, local, t: i + local };
}

/**
 * Chapter i begins when its section's top reaches the middle of the viewport, so the world turns
 * to a chapter just as its text arrives. The first chapter starts at 0.
 */
export function measure(tops: number[], viewport: number, docHeight: number): Ranges {
  const starts = tops.map((top, i) => (i === 0 ? 0 : Math.max(0, top - viewport * 0.5)));
  for (let i = 1; i < starts.length; i++) starts[i] = Math.max(starts[i], starts[i - 1] + 1);
  return { starts, end: Math.max(starts[starts.length - 1] + 1, docHeight - viewport) };
}

import { describe, expect, it } from "vitest";
import { clauseRuns } from "./runs";

describe("clauseRuns", () => {
  it("splits around spans and preserves the full text", () => {
    const text = "aa BBB cc DD e";
    const runs = clauseRuns(text, [
      { key: "x", start: 3, end: 6 },
      { key: "y", start: 10, end: 12 },
    ]);
    expect(runs).toEqual([
      { text: "aa ", key: null },
      { text: "BBB", key: "x" },
      { text: " cc ", key: null },
      { text: "DD", key: "y" },
      { text: " e", key: null },
    ]);
    expect(runs.map((r) => r.text).join("")).toBe(text);
  });

  it("clips overlaps instead of merging them", () => {
    const runs = clauseRuns("abcdef", [
      { key: "x", start: 0, end: 4 },
      { key: "y", start: 2, end: 6 },
    ]);
    expect(runs).toEqual([
      { text: "abcd", key: "x" },
      { text: "ef", key: "y" },
    ]);
  });

  it("handles no spans and out-of-range spans", () => {
    expect(clauseRuns("abc", [])).toEqual([{ text: "abc", key: null }]);
    expect(clauseRuns("abc", [{ key: "x", start: 2, end: 99 }])).toEqual([
      { text: "ab", key: null },
      { text: "c", key: "x" },
    ]);
  });
});

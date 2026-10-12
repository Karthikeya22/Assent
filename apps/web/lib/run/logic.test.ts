import { describe, expect, it } from "vitest";
import type { components } from "@/lib/api/schema";
import { evaluateTree, gapKeys } from "./logic";

type C = components["schemas"]["CriterionOut"];
const leaf = (key: string): C => ({
  id: key, key, kind: "LEAF", label: key, n_required: null, evidence_type: "diagnosis",
  threshold: null, lookback_days: null, span: null, children: [],
});
const node = (key: string, kind: string, children: C[], n: number | null = null): C => ({
  ...leaf(key), kind, evidence_type: null, n_required: n, children,
});

describe("evaluateTree mirrors the server logic engine", () => {
  const tree = node("root", "AND", [node("o", "OR", [leaf("a"), leaf("b")]), node("k", "N_OF_M", [leaf("c"), leaf("d"), leaf("e")], 2)]);

  it("combines three-valued states", () => {
    const s = evaluateTree(tree, { a: "not_met", b: "met", c: "met", d: "insufficient", e: "met" });
    expect(s).toMatchObject({ o: "met", k: "met", root: "met" });
  });

  it("gaps exclude unchosen alternatives under a satisfied OR", () => {
    const s = evaluateTree(tree, { a: "insufficient", b: "met", c: "met", d: "not_met", e: "insufficient" });
    // OR "o" is met via b, so a is not a gap; N_OF_M "k" needs 2 of c,d,e and has only c.
    expect(gapKeys(tree, s)).toEqual(["d", "e"]);
  });

  it("missing leaves are insufficient and N_OF_M fails when unreachable", () => {
    const s = evaluateTree(tree, { a: "met", c: "not_met", d: "not_met" });
    expect(s.b).toBe("insufficient");
    expect(s.k).toBe("not_met");
    expect(s.root).toBe("not_met");
  });
});

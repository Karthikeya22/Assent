import { describe, expect, it } from "vitest";
import { GRAPH_X, children, layout } from "./layout";

describe("lattice layout", () => {
  const nodes = layout();

  it("lays out the real L39240 tree: 18 nodes, 12 leaves, one root", () => {
    expect(nodes).toHaveLength(18);
    expect(nodes.filter((n) => n.kind === "LEAF")).toHaveLength(12);
    expect(nodes.filter((n) => n.parent === null).map((n) => n.key)).toEqual(["esi"]);
  });

  it("puts parents above and between their children", () => {
    for (const n of nodes.filter((x) => x.kind !== "LEAF")) {
      const kids = children(nodes, n.key);
      expect(kids.every((k) => k.pos[1] < n.pos[1])).toBe(true);
      const xs = kids.map((k) => k.pos[0]);
      expect(n.pos[0]).toBeGreaterThanOrEqual(Math.min(...xs) - 1e-9);
      expect(n.pos[0]).toBeLessThanOrEqual(Math.max(...xs) + 1e-9);
    }
  });

  it("centres the leaves on the graph column", () => {
    const xs = nodes.filter((n) => n.kind === "LEAF").map((n) => n.pos[0]);
    expect((Math.min(...xs) + Math.max(...xs)) / 2).toBeCloseTo(GRAPH_X);
  });
});

import { describe, expect, it } from "vitest";
import { layout } from "./layout";
import { DEFENDED, HERO_TARGET, WEAK, heroFrame, ringFill, storyFrame } from "./timeline";

const nodes = layout();

describe("hero loop", () => {
  it("proves the target criterion after its ribbon lands, then resets", () => {
    expect(heroFrame(nodes, 0.3).leaves[HERO_TARGET]).toBe("wire");
    expect(heroFrame(nodes, 0.3).ribbons).toHaveLength(1);
    expect(heroFrame(nodes, 0.6).leaves[HERO_TARGET]).toBe("met");
    expect(heroFrame(nodes, 0.99).leaves[HERO_TARGET]).toBe("wire");
  });

  it("the adversary sweeps to the insufficient criterion", () => {
    const f = heroFrame(nodes, 0.85);
    expect(f.leaves[WEAK]).toBe("amber");
    expect(f.rays[0]).toMatchObject({ to: WEAK, color: "adversary" });
  });
});

describe("story", () => {
  it("builds the tree, fans the pages, then proves criteria in parallel", () => {
    expect(storyFrame(nodes, 0.1).build).toBeGreaterThan(0);
    expect(storyFrame(nodes, 0.3).fan).toBeGreaterThan(0);
    expect(storyFrame(nodes, 0.5).ribbons.length).toBeGreaterThan(1);
  });

  it("the verifier downgrades one criterion and step 5 turns it into a gap task", () => {
    const end = storyFrame(nodes, 1);
    expect(end.leaves[WEAK]).toBe("amber");
    expect(end.leaves[DEFENDED]).toBe("met");
    expect(end.gapCard).toBe(1);
  });
});

describe("ring fill", () => {
  it("AND averages its children, OR takes the best one", () => {
    const f = storyFrame(nodes, 1).leaves;
    expect(ringFill(nodes, f, "sev")).toBeCloseTo(0.5); // impact met, baseline amber
    expect(ringFill(nodes, f, "dur")).toBe(1); // dur.standard fully met
  });
});

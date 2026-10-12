/**
 * What the lattice shows at a moment: a pure function of hero time or story scroll progress.
 * Motion = system state (FRONTEND §1): evidence travels, a criterion resolves, logic fills
 * upward, the verifier rejects a quote, the payer adversary probes the weak spot.
 */
import type { LNode } from "./layout";

export type LeafState = "wire" | "met" | "amber";
export type Ribbon = { to: string; page: number; head: number; color: "signal" | "fail"; flicker: boolean };
export type Ray = { to: string; amt: number; color: "adversary" | "signal" };
export type Frame = {
  build: number; // 0..1 nodes/edges revealed (story step 1)
  fan: number; // 0..1 pages fanned into a timeline (story step 2)
  pageHi: { page: number; amt: number };
  ribbons: Ribbon[];
  leaves: Record<string, LeafState>;
  pulse: Record<string, number>; // 0..1 landing ring pulse
  rays: Ray[];
  label: { key: string; text: string; amt: number } | null;
  pullBack: number; // 0..1 camera pulls back (story step 5)
  gapCard: number; // 0..1 the conceded objection becomes a gap task (DOM card)
};

const clamp = (x: number) => Math.min(1, Math.max(0, x));
/** 0 before a, 1 after b, smooth between. */
export const span = (t: number, a: number, b: number) => {
  const x = clamp((t - a) / (b - a));
  return x * x * (3 - 2 * x);
};

// Leaves already proven when the hero loop starts (the run is mid-flight).
const BASE_MET = ["dx.radic", "dx.imaging", "sev.impact", "dur.conservative", "rehab", "contra", "freq"];
export const HERO_TARGET = "dur.pain"; // the criterion we watch get proven
export const WEAK = "sev.baseline"; // never receives evidence: insufficient
export const DEFENDED = "dur.conservative"; // story step 5: the adversary's objection is rebutted

function base(nodes: LNode[]): Record<string, LeafState> {
  return Object.fromEntries(
    nodes.filter((n) => n.kind === "LEAF").map((n) => [n.key, BASE_MET.includes(n.key) ? "met" : "wire"]),
  );
}

/** Hero: a 10 s loop, `t` in [0, 1). */
export function heroFrame(nodes: LNode[], t: number): Frame {
  const leaves = base(nodes);
  const landed = t >= 0.45 && t < 0.95;
  if (landed) leaves[HERO_TARGET] = "met";
  if (t >= 0.55 && t < 0.95) leaves[WEAK] = "amber";
  const sweep = span(t, 0.7, 0.86) * (1 - span(t, 0.9, 0.97));
  return {
    build: 1,
    fan: 0,
    pageHi: { page: 7, amt: span(t, 0.02, 0.1) * (1 - span(t, 0.4, 0.5)) },
    ribbons: t >= 0.1 && t < 0.5 ? [{ to: HERO_TARGET, page: 7, head: span(t, 0.12, 0.46), color: "signal", flicker: false }] : [],
    leaves,
    pulse: { [HERO_TARGET]: landed ? 1 - span(t, 0.45, 0.6) : 0 },
    rays: sweep > 0 ? [{ to: WEAK, amt: sweep, color: "adversary" }] : [],
    label: { key: WEAK, text: "insufficient · baseline pain scale", amt: span(t, 0.56, 0.62) * (1 - span(t, 0.92, 0.96)) },
    pullBack: 0,
    gapCard: 0,
  };
}

const STORY_RIBBONS = ["dx.radic", "dx.imaging", "sev.impact", "dur.pain", "dur.conservative", "rehab", "contra", "freq"];

/** Story: scroll progress `p` in [0, 1] across five steps of 0.2 each. */
export function storyFrame(nodes: LNode[], p: number): Frame {
  const s = (i: number) => clamp((p - i * 0.2) / 0.2); // progress inside step i (0-based)
  const leaves: Record<string, LeafState> = Object.fromEntries(
    nodes.filter((n) => n.kind === "LEAF").map((n) => [n.key, "wire" as LeafState]),
  );
  const ribbons: Ribbon[] = [];
  const pulse: Record<string, number> = {};
  // Step 3: parallel fan-out. Each ribbon starts a little later and lands with a verdict.
  STORY_RIBBONS.forEach((key, i) => {
    const head = span(s(2), i * 0.06, 0.45 + i * 0.06);
    if (head >= 1) {
      leaves[key] = "met";
      pulse[key] = 1 - span(s(2), 0.45 + i * 0.06, 0.7 + i * 0.06);
    } else if (head > 0) ribbons.push({ to: key, page: (i * 3) % 12, head, color: "signal", flicker: false });
  });
  // Step 4: the verifier rejects one quote. The ribbon reaches out, flickers red and snaps back.
  const v = s(3);
  if (v > 0 && v < 0.75) {
    const head = v < 0.45 ? span(v, 0, 0.45) * 0.85 : 0.85 * (1 - span(v, 0.5, 0.75));
    ribbons.push({ to: WEAK, page: 5, head, color: v > 0.35 ? "fail" : "signal", flicker: v > 0.35 && v < 0.55 });
  }
  if (v >= 0.6) leaves[WEAK] = "amber";
  // Step 5: two adversary rays. One is answered with a teal counter-ray, one is conceded.
  const a = s(4);
  const rays: Ray[] = [];
  if (a > 0) {
    const hit = span(a, 0.05, 0.3);
    rays.push({ to: DEFENDED, amt: hit * (1 - span(a, 0.55, 0.75)), color: "adversary" });
    rays.push({ to: WEAK, amt: hit, color: "adversary" });
    rays.push({ to: DEFENDED, amt: span(a, 0.35, 0.55) * (1 - span(a, 0.8, 0.95)), color: "signal" });
  }
  return {
    build: span(s(0), 0, 0.9),
    fan: span(s(1), 0, 0.85),
    pageHi: { page: 5, amt: span(v, 0, 0.2) * (1 - span(v, 0.6, 0.8)) },
    ribbons,
    leaves,
    pulse,
    rays,
    label: v >= 0.6 ? { key: WEAK, text: "quote not found verbatim · downgraded", amt: span(v, 0.6, 0.7) * (1 - span(a, 0.5, 0.7)) } : null,
    pullBack: span(a, 0, 0.4),
    gapCard: span(a, 0.65, 0.85),
  };
}

/** Ring fill for a logic node: AND = share of children satisfied, OR = any child satisfied. */
export function ringFill(nodes: LNode[], leaves: Record<string, LeafState>, key: string): number {
  const node = nodes.find((n) => n.key === key)!;
  if (node.kind === "LEAF") return leaves[key] === "met" ? 1 : 0;
  const kids = nodes.filter((n) => n.parent === key).map((c) => ringFill(nodes, leaves, c.key));
  return node.kind === "OR" ? Math.max(...kids) : kids.reduce((s, x) => s + x, 0) / kids.length;
}

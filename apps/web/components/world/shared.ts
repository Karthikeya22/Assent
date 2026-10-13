import * as THREE from "three";

/** Smoothstep window: 0 before a, 1 after b. Re-exported so scenes read like the timeline. */
export { span } from "@/components/lattice/timeline";

/** Design tokens read from CSS so 3D colour always matches the page (DESIGN.md). */
export type Palette = Record<"ink3" | "rule" | "paper" | "signal" | "gap" | "fail" | "adversary", THREE.Color>;

export function readPalette(): Palette {
  const css = getComputedStyle(document.documentElement);
  const c = (v: string, fallback: string) => new THREE.Color(css.getPropertyValue(v).trim() || fallback);
  return {
    ink3: c("--ink-3", "#5f6a66"),
    rule: c("--rule", "#dbe1de"),
    paper: c("--paper-raised", "#fbfcfc"),
    signal: c("--signal", "#0f6e5c"),
    gap: c("--gap-fill", "#e8a33d"),
    fail: c("--fail", "#b3261e"),
    adversary: c("--adversary", "#5b3fa8"),
  };
}

/** Is chapter coordinate t inside [a, b]? Scenes skip work and rendering outside their window. */
export const within = (t: number, a: number, b: number) => t >= a && t <= b;

export const FLOOR_Y = 0;

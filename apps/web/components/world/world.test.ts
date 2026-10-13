import { describe, expect, it } from "vitest";
import { POSES, TEXT_SIDE, filmShift, poseAt, travel } from "./camera";
import { CHAPTERS, locate, measure } from "./chapters";
import { damp } from "./pointer";

describe("chapters", () => {
  const r = measure([0, 900, 1800, 2700], 800, 3600);
  it("starts a chapter when its top reaches mid-viewport", () => {
    expect(r.starts).toEqual([0, 500, 1400, 2300]);
    expect(r.end).toBe(2800);
  });
  it("locates scroll offsets", () => {
    expect(locate(0, r)).toEqual({ index: 0, local: 0, t: 0 });
    expect(locate(250, r).local).toBeCloseTo(0.5);
    expect(locate(500, r).index).toBe(1);
    expect(locate(5000, r)).toEqual({ index: 3, local: 1, t: 4 });
  });
  it("keeps starts strictly increasing for tiny sections", () => {
    const m = measure([0, 10, 10], 800, 900);
    expect(m.starts[1]).toBeLessThan(m.starts[2]);
  });
  it("has one camera pose per chapter", () => {
    expect(POSES).toHaveLength(CHAPTERS.length);
  });
});

describe("camera", () => {
  it("holds while a chapter is read, then glides", () => {
    expect(travel(0)).toBe(0);
    expect(travel(0.5)).toBe(0);
    expect(travel(1)).toBe(1);
    expect(poseAt(2.3)).toEqual(POSES[2]);
  });
  it("is continuous across chapter boundaries", () => {
    const a = poseAt(3 - 1e-6).pos;
    const b = poseAt(3).pos;
    a.forEach((v, i) => expect(v).toBeCloseTo(b[i], 3));
  });
  it("frames the subject opposite the text, one side per chapter", () => {
    expect(TEXT_SIDE).toHaveLength(POSES.length);
    // three.js filmOffset > 0 slides the image left, so text on the left needs a negative offset.
    expect(filmShift(0.2)).toBeLessThan(0);
    expect(filmShift(3.2)).toBeGreaterThan(0);
    expect(filmShift(1.2)).toBe(0);
  });
  it("clamps outside the story", () => {
    expect(poseAt(-2)).toEqual(POSES[0]);
    expect(poseAt(99)).toEqual(POSES[POSES.length - 1]);
  });
});

describe("pointer damping", () => {
  it("approaches the target without overshoot and independent of frame rate", () => {
    const one = damp(0, 1, 4, 0.5);
    let two = 0;
    for (let i = 0; i < 2; i++) two = damp(two, 1, 4, 0.25);
    expect(one).toBeGreaterThan(0);
    expect(one).toBeLessThan(1);
    expect(two).toBeCloseTo(one, 10);
  });
});

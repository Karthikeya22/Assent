import { describe, expect, it } from "vitest";
import { initialRunState, reduce, replay, type RunEvent } from "./reducer";

const EVENTS: RunEvent[] = [
  { type: "run_started", leaves: ["dur.pain", "contra"] },
  { type: "node_finished", node: "deidentify_and_index", chunks: 42, latency_ms: 900 },
  { type: "node_started", node: "evidence_agent", criterion_id: "dur.pain" },
  { type: "retrieval", criterion_id: "dur.pain", chunks: [{ id: "a", score: 1 }, { id: "b", score: 0.5 }] },
  { type: "retrieval", criterion_id: "dur.pain", chunks: [{ id: "b", score: 1 }, { id: "c", score: 0.4 }] },
  {
    type: "verdict",
    criterion_id: "dur.pain",
    verdict: "met",
    confidence: 0.9,
    rationale: "16 weeks",
    downgraded: null,
    citations: [{ chunk_id: "a", start: 0, end: 10, quote: "16 weeks", verified: true }],
  },
  { type: "logic_update", node_id: "dur", state: "met" },
  { type: "run_finished", state: "insufficient", readiness: 0.5 },
];

describe("run reducer", () => {
  it("builds normalized state from the event contract", () => {
    const s = replay(EVENTS);
    expect(s.status).toBe("finished");
    expect(s.indexed).toEqual({ chunks: 42, latencyMs: 900 });
    expect(s.leaves["dur.pain"]).toMatchObject({ status: "done", verdict: "met", retrieved: ["a", "b", "c"] });
    expect(s.leaves["contra"]).toMatchObject({ status: "idle" });
    expect(s.logic).toEqual({ dur: "met" });
    expect(s).toMatchObject({ decision: "insufficient", readiness: 0.5, seen: EVENTS.length });
  });

  it("is deterministic: replaying twice gives identical state (Review Focus 5)", () => {
    expect(replay(EVENTS)).toEqual(replay(EVENTS));
  });

  it("never mutates the previous state", () => {
    const before = replay(EVENTS.slice(0, 3));
    const snapshot = JSON.stringify(before);
    reduce(before, EVENTS[3]);
    expect(JSON.stringify(before)).toBe(snapshot);
  });

  it("surfaces failures instead of spinning", () => {
    const s = replay([{ type: "run_started", leaves: ["x"] }, { type: "run_failed", error: "boom" }]);
    expect(s).toMatchObject({ status: "failed", error: "boom" });
  });

  it("ignores unknown event types", () => {
    const s = reduce(initialRunState, { type: "future_thing" } as unknown as RunEvent);
    expect(s.seen).toBe(1);
  });
});

// One reducer turns run events (ARCHITECTURE §5) into normalized state. The live stream, recorded
// fixtures, Storybook and Playwright all replay through it, so the UI can't drift between them.

export type Verdict = "met" | "not_met" | "insufficient";
export type LogicState = Verdict;

export type CitationRef = {
  chunk_id: string;
  start: number | null;
  end: number | null;
  quote: string;
  verified: boolean;
};

export type LeafState = {
  status: "idle" | "running" | "done";
  verdict?: Verdict;
  confidence?: number;
  rationale?: string;
  downgraded?: string | null;
  citations: CitationRef[];
  retrieved: string[]; // chunk ids surfaced by retrieval, newest search last
  latencyMs?: number;
};

export type RunState = {
  status: "idle" | "running" | "finished" | "failed";
  leaves: Record<string, LeafState>;
  logic: Record<string, LogicState>;
  readiness: number | null;
  decision: LogicState | null;
  indexed: { chunks: number; latencyMs: number } | null;
  error: string | null;
  seen: number; // events applied
};

export type RunEvent =
  | { type: "run_started"; leaves: string[] }
  | { type: "node_started"; node: string; criterion_id?: string }
  | { type: "node_finished"; node: string; criterion_id?: string; latency_ms?: number; chunks?: number }
  | { type: "retrieval"; criterion_id: string; chunks: { id: string; score: number }[] }
  | {
      type: "verdict";
      criterion_id: string;
      verdict: Verdict;
      confidence: number;
      rationale: string;
      downgraded: string | null;
      citations: CitationRef[];
    }
  | { type: "logic_update"; node_id: string; state: LogicState }
  | { type: "run_finished"; state: LogicState; readiness: number }
  | { type: "run_failed"; error: string };

export const initialRunState: RunState = {
  status: "idle",
  leaves: {},
  logic: {},
  readiness: null,
  decision: null,
  indexed: null,
  error: null,
  seen: 0,
};

const blankLeaf: LeafState = { status: "idle", citations: [], retrieved: [] };

function leaf(s: RunState, key: string, patch: Partial<LeafState>): RunState {
  const prev = s.leaves[key] ?? blankLeaf;
  return { ...s, leaves: { ...s.leaves, [key]: { ...prev, ...patch } } };
}

export function reduce(state: RunState, e: RunEvent): RunState {
  const s = { ...state, seen: state.seen + 1, status: state.status === "idle" ? "running" : state.status } as RunState;
  switch (e.type) {
    case "run_started":
      return { ...s, leaves: Object.fromEntries(e.leaves.map((k) => [k, blankLeaf])) };
    case "node_started":
      return e.criterion_id ? leaf(s, e.criterion_id, { status: "running" }) : s;
    case "node_finished":
      if (e.node === "deidentify_and_index") {
        return { ...s, indexed: { chunks: e.chunks ?? 0, latencyMs: e.latency_ms ?? 0 } };
      }
      return e.criterion_id ? leaf(s, e.criterion_id, { latencyMs: e.latency_ms }) : s;
    case "retrieval": {
      const prev = s.leaves[e.criterion_id]?.retrieved ?? [];
      const ids = e.chunks.map((c) => c.id).filter((id) => !prev.includes(id));
      return leaf(s, e.criterion_id, { retrieved: [...prev, ...ids] });
    }
    case "verdict":
      return leaf(s, e.criterion_id, {
        status: "done",
        verdict: e.verdict,
        confidence: e.confidence,
        rationale: e.rationale,
        downgraded: e.downgraded,
        citations: e.citations,
      });
    case "logic_update":
      return { ...s, logic: { ...s.logic, [e.node_id]: e.state } };
    case "run_finished":
      return { ...s, status: "finished", decision: e.state, readiness: e.readiness };
    case "run_failed":
      return { ...s, status: "failed", error: e.error };
    default:
      return s; // unknown future event types are ignored, not fatal
  }
}

export function replay(events: RunEvent[], from: RunState = initialRunState): RunState {
  return events.reduce(reduce, from);
}

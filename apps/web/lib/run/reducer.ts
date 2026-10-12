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
  verdictId?: string; // DB id once persisted (needed to override)
  overridden?: boolean;
  overrideReason?: string | null;
};

export type ObjectionState = {
  id: string;
  criterion_id: string | null;
  text: string;
  severity: "high" | "medium" | "low";
  status: "open" | "rebutted" | "conceded";
  rebuttal: string;
};

export type GapState = { criterion_id: string | null; title: string; detail: string; assignee_role: string; id?: string; status?: string };

export type RunState = {
  status: "idle" | "running" | "finished" | "failed";
  leaves: Record<string, LeafState>;
  logic: Record<string, LogicState>;
  readiness: number | null;
  decision: LogicState | null;
  indexed: { chunks: number; latencyMs: number } | null;
  error: string | null;
  objections: Record<string, ObjectionState>;
  gaps: GapState[];
  denialRisk: number | null;
  riskFactors: string[];
  reviewError: string | null;
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
  | { type: "objection"; id: string; criterion_id: string; text: string; severity: ObjectionState["severity"] }
  | { type: "objection_update"; id: string; status: ObjectionState["status"]; rebuttal: string }
  | { type: "gap"; criterion_id: string; title: string; detail: string; assignee_role: string }
  | { type: "node_failed"; node: string; error: string }
  | { type: "run_finished"; state: LogicState; readiness: number; denial_risk?: number | null; risk_factors?: string[] }
  | { type: "run_failed"; error: string };

export const initialRunState: RunState = {
  status: "idle",
  leaves: {},
  logic: {},
  readiness: null,
  decision: null,
  indexed: null,
  error: null,
  objections: {},
  gaps: [],
  denialRisk: null,
  riskFactors: [],
  reviewError: null,
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
    case "objection":
      return {
        ...s,
        objections: {
          ...s.objections,
          [e.id]: { id: e.id, criterion_id: e.criterion_id, text: e.text, severity: e.severity, status: "open", rebuttal: "" },
        },
      };
    case "objection_update": {
      const prev = s.objections[e.id];
      if (!prev) return s; // update for an objection we never saw: ignore, don't invent it
      return { ...s, objections: { ...s.objections, [e.id]: { ...prev, status: e.status, rebuttal: e.rebuttal } } };
    }
    case "gap":
      return { ...s, gaps: [...s.gaps, { criterion_id: e.criterion_id, title: e.title, detail: e.detail, assignee_role: e.assignee_role }] };
    case "node_failed":
      return { ...s, reviewError: e.error };
    case "run_finished":
      return {
        ...s,
        status: "finished",
        decision: e.state,
        readiness: e.readiness,
        denialRisk: e.denial_risk ?? null,
        riskFactors: e.risk_factors ?? [],
      };
    case "run_failed":
      return { ...s, status: "failed", error: e.error };
    default:
      return s; // unknown future event types are ignored, not fatal
  }
}

export function replay(events: RunEvent[], from: RunState = initialRunState): RunState {
  return events.reduce(reduce, from);
}

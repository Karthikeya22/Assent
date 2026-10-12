"use client";

import { Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";
import { startRun } from "@/app/(app)/app/cases/[id]/actions";
import { CriteriaGraph2D } from "@/components/graph/CriteriaGraph2D";
import { MonoChip } from "@/components/ui/MonoChip";
import type { components } from "@/lib/api/schema";
import { evaluateTree, leavesOf } from "@/lib/run/logic";
import { initialRunState, type RunState, type Verdict } from "@/lib/run/reducer";
import { useRunStore } from "@/lib/run/store";
import { useRunStream } from "@/lib/run/useRunStream";
import { ChartPane, groupDocs } from "./ChartPane";
import { DecisionPane } from "./DecisionPane";
import { TraceStepper } from "./TraceStepper";

type S = components["schemas"];

export type Review = {
  objections: S["ObjectionOut"][];
  gaps: S["GapOut"][];
  riskFactors: string[];
  error: string | null;
};

function fromDb(root: S["CriterionOut"], verdicts: S["VerdictOut"][], detail: S["CaseDetail"], review: Review): RunState {
  const leaves: RunState["leaves"] = {};
  for (const v of verdicts) {
    leaves[v.criterion_key] = {
      status: "done", verdict: v.verdict as Verdict, confidence: v.confidence, rationale: v.rationale,
      downgraded: null, retrieved: [], verdictId: v.id, overridden: v.overridden, overrideReason: v.override_reason,
      citations: v.citations.map((c) => ({ chunk_id: c.chunk_id, start: c.start, end: c.end, quote: c.quote, verified: c.verified })),
    };
  }
  const logic = evaluateTree(root, Object.fromEntries(verdicts.map((v) => [v.criterion_key, v.verdict as Verdict])));
  return {
    ...initialRunState,
    status: "finished",
    leaves,
    logic,
    readiness: detail.readiness_score,
    decision: logic[root.key] ?? null,
    denialRisk: detail.denial_risk,
    riskFactors: review.riskFactors,
    reviewError: review.error,
    objections: Object.fromEntries(
      review.objections.map((o) => [
        o.id,
        { id: o.id, criterion_id: o.criterion_key, text: o.text, severity: o.severity as "high" | "medium" | "low", status: o.status as "open" | "rebutted" | "conceded", rebuttal: o.rebuttal ?? "" },
      ]),
    ),
    gaps: review.gaps.map((g) => ({ id: g.id, criterion_id: g.criterion_key, title: g.title, detail: g.detail, assignee_role: g.assignee_role, status: g.status })),
    seen: 0,
  };
}

const SEG: Record<string, string> = { met: "bg-signal", not_met: "bg-fail", insufficient: "bg-gap" };

export function CaseWorkspace({
  detail,
  root,
  policy,
  chunks,
  verdicts,
  review,
  packets,
}: {
  detail: S["CaseDetail"];
  root: S["CriterionOut"];
  policy: { sourceId: string; version: string; title: string };
  chunks: S["ChunkOut"][];
  verdicts: S["VerdictOut"][];
  review: Review;
  packets: S["PacketOut"][];
}) {
  const router = useRouter();
  const leaves = useMemo(() => leavesOf(root), [root]);
  const docs = useMemo(() => groupDocs(chunks), [chunks]);
  const run = useRunStore((s) => s.run);
  const [liveRun, setLiveRun] = useState<string | null>(
    detail.latest_run && ["queued", "running"].includes(detail.latest_run.status) ? detail.latest_run.id : null,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [doc, setDoc] = useState<string | null>(null);
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  // Finished runs load from the DB; live runs stream (the server replays their full log).
  useEffect(() => {
    if (liveRun) return;
    if (detail.latest_run?.status === "failed") {
      useRunStore.getState().reset({ ...initialRunState, status: "failed", error: "the last run failed. Re-run to retry." });
    } else {
      useRunStore.getState().reset(verdicts.length ? fromDb(root, verdicts, detail, review) : initialRunState);
    }
  }, [liveRun, verdicts, root, detail, review]);
  useRunStream(liveRun);

  // Pull fresh server data (timeline, case header) when the chart is indexed and when the run ends.
  useEffect(() => {
    if (liveRun && (run.indexed || run.status === "finished" || run.status === "failed")) router.refresh();
  }, [liveRun, run.indexed, run.status, router]);

  const cited = useMemo(
    () => Object.entries(run.leaves).flatMap(([key, l]) => l.citations.map((c) => ({ ...c, key }))),
    [run.leaves],
  );

  function select(key: string) {
    setSelected(key);
    setFocusKey(key);
    const c = run.leaves[key]?.citations[0];
    const d = c && docs.find((x) => x.chunks.some((k) => k.id === c.chunk_id));
    if (d) setDoc(d.resourceId);
  }

  function cite(chunkId: string, key: string) {
    const d = docs.find((x) => x.chunks.some((k) => k.id === chunkId));
    if (d) setDoc(d.resourceId);
    setFocusKey(key);
  }

  function onRun() {
    setError(null);
    startTransition(async () => {
      const r = await startRun(detail.id);
      if (r.error) setError(r.error);
      else if (r.runId) {
        useRunStore.getState().reset();
        setSelected(null);
        setLiveRun(r.runId);
      }
    });
  }

  const age = new Date().getFullYear() - detail.patient.birth_year;
  const running = run.status === "running" || pending;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-rule px-5 py-3">
        <div className="min-w-0">
          <h1 className="display text-2xl leading-tight">{detail.patient.name}</h1>
          <p className="text-sm text-ink-2">
            {age} · {detail.patient.sex}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <MonoChip>{detail.service_family.toUpperCase()}</MonoChip>
          <MonoChip>CPT {detail.cpt_codes.join(", ")}</MonoChip>
          <MonoChip>ICD-10 {detail.icd10_codes.join(", ")}</MonoChip>
          <MonoChip>LCD {policy.sourceId}</MonoChip>
        </div>
        <div className="flex items-center gap-2" aria-label="Readiness by criterion">
          <div className="flex h-2.5 gap-[2px]">
            {leaves.map((l) => (
              <span
                key={l.key}
                title={`${l.label}: ${run.leaves[l.key]?.verdict ?? "not checked"}`}
                className={`w-2.5 rounded-[1px] transition-colors duration-[var(--dur-3)] ${SEG[run.leaves[l.key]?.verdict ?? ""] ?? "bg-rule"}`}
              />
            ))}
          </div>
          <span className="font-mono text-sm tabular">{run.readiness == null ? "—" : `${Math.round(run.readiness * 100)}%`}</span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {error && <span role="alert" className="text-sm text-fail">{error}</span>}
          <button
            type="button"
            onClick={onRun}
            disabled={running}
            className="inline-flex h-9 items-center gap-2 rounded-[var(--radius-control)] bg-signal px-3.5 font-medium text-paper disabled:opacity-50"
          >
            <Play size={14} strokeWidth={2} aria-hidden="true" />
            {running ? "Running…" : verdicts.length || run.status === "finished" ? "Re-run" : "Run"}
          </button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(280px,0.9fr)_minmax(0,1.7fr)_minmax(280px,340px)]">
        <section className="min-h-0 border-r border-rule" aria-label="Chart">
          <ChartPane docs={docs} cited={cited} selectedDoc={doc} onSelectDoc={setDoc} focusKey={focusKey} />
        </section>
        <section className="relative min-h-0 bg-paper" aria-label="Criteria graph">
          <span className="absolute top-3 left-4 z-10 text-xs tracking-wide text-ink-3 uppercase">Criteria · {policy.sourceId} v{policy.version}</span>
          <CriteriaGraph2D root={root} sourceId={policy.sourceId} title={policy.title} selected={selected} onSelect={select} />
        </section>
        <section className="min-h-0 border-l border-rule" aria-label="Decision">
          <DecisionPane caseId={detail.id} runId={detail.latest_run?.status === "finished" ? detail.latest_run.id : null} caseStatus={detail.status} root={root} leaves={leaves} selected={selected} onSelect={select} onCite={cite} packets={packets} />
        </section>
      </div>
      <TraceStepper total={leaves.length} />
    </div>
  );
}

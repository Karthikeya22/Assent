"use client";

import { Play } from "lucide-react";
import { useMemo, useState } from "react";
import { ChartPane, groupDocs } from "@/components/case/ChartPane";
import { DecisionPane } from "@/components/case/DecisionPane";
import { TraceStepper } from "@/components/case/TraceStepper";
import { CriteriaGraph2D } from "@/components/graph/CriteriaGraph2D";
import { MonoChip } from "@/components/ui/MonoChip";
import type { components } from "@/lib/api/schema";
import { leavesOf } from "@/lib/run/logic";
import type { RunEvent } from "@/lib/run/reducer";
import { useRunStore } from "@/lib/run/store";
import { useRunReplay } from "@/lib/run/useRunStream";

type S = components["schemas"];
export type DemoBundle = {
  patient: { name: string; sex: string; birth_year: number };
  service_family: string;
  cpt_codes: string[];
  icd10_codes: string[];
  policy: { sourceId: string; version: string; title: string };
  root: S["CriterionOut"];
  chunks: S["ChunkOut"][];
  events: RunEvent[];
};

const SEG: Record<string, string> = { met: "bg-signal", not_met: "bg-fail", insufficient: "bg-gap" };

/** The Case Workspace, read-only, replaying a real recorded run (no login, no backend). */
export function DemoWorkspace({ demo }: { demo: DemoBundle }) {
  const leaves = useMemo(() => leavesOf(demo.root), [demo.root]);
  const docs = useMemo(() => groupDocs(demo.chunks), [demo.chunks]);
  const run = useRunStore((s) => s.run);
  const [playing, setPlaying] = useState<RunEvent[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [doc, setDoc] = useState<string | null>(null);
  const [focusKey, setFocusKey] = useState<string | null>(null);
  useRunReplay(playing, 3);

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
  const age = 2026 - demo.patient.birth_year;
  const running = run.status === "running";

  return (
    <div className="flex h-dvh min-h-0 flex-col pt-16">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-rule px-5 py-3">
        <div className="min-w-0">
          <h1 className="display text-2xl leading-tight">{demo.patient.name}</h1>
          <p className="text-sm text-ink-2">
            {age} · {demo.patient.sex} · synthetic patient
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <MonoChip>{demo.service_family.toUpperCase()}</MonoChip>
          <MonoChip>CPT {demo.cpt_codes.join(", ")}</MonoChip>
          <MonoChip>ICD-10 {demo.icd10_codes.join(", ")}</MonoChip>
          <MonoChip>LCD {demo.policy.sourceId}</MonoChip>
        </div>
        <div className="flex items-center gap-2" aria-label="Readiness by criterion">
          <div className="flex h-2.5 gap-[2px]">
            {leaves.map((l) => (
              <span key={l.key} title={`${l.label}: ${run.leaves[l.key]?.verdict ?? "not checked"}`} className={`w-2.5 rounded-[1px] transition-colors duration-[var(--dur-3)] ${SEG[run.leaves[l.key]?.verdict ?? ""] ?? "bg-rule"}`} />
            ))}
          </div>
          <span className="font-mono text-sm tabular">{run.readiness == null ? "—" : `${Math.round(run.readiness * 100)}%`}</span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-ink-3">Replay of a recorded run (gpt-4.1 + Gemini adversary)</span>
          <button
            type="button"
            disabled={running}
            onClick={() => {
              setSelected(null);
              setPlaying([...demo.events]); // a new array restarts the replay
            }}
            className="inline-flex h-9 items-center gap-2 rounded-[var(--radius-control)] bg-signal px-3.5 font-medium text-paper disabled:opacity-50"
          >
            <Play size={14} strokeWidth={2} aria-hidden="true" />
            {running ? "Running…" : playing ? "Run again" : "Run"}
          </button>
        </div>
      </header>
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(280px,0.9fr)_minmax(0,1.7fr)_minmax(280px,340px)]">
        <section className="hidden min-h-0 border-r border-rule lg:block" aria-label="Chart">
          <ChartPane docs={docs} cited={cited} selectedDoc={doc} onSelectDoc={setDoc} focusKey={focusKey} />
        </section>
        <section className="relative min-h-[360px] bg-paper" aria-label="Criteria graph">
          <span className="absolute top-3 left-4 z-10 text-xs tracking-wide text-ink-3 uppercase">
            Criteria · {demo.policy.sourceId} v{demo.policy.version}
          </span>
          <CriteriaGraph2D root={demo.root} sourceId={demo.policy.sourceId} title={demo.policy.title} selected={selected} onSelect={select} />
        </section>
        <section className="min-h-0 border-l border-rule" aria-label="Decision">
          <DecisionPane caseId="demo" runId={null} caseStatus="new" root={demo.root} leaves={leaves} selected={selected} onSelect={select} onCite={cite} packets={[]} readOnly />
        </section>
      </div>
      <TraceStepper total={leaves.length} />
    </div>
  );
}

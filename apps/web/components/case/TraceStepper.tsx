"use client";

import { useRunStore } from "@/lib/run/store";

/** Collapsed agent trace: one line of graph steps with check marks and timings (FRONTEND §6.3). */
export function TraceStepper({ total }: { total: number }) {
  const run = useRunStore((s) => s.run);
  const done = Object.values(run.leaves).filter((l) => l.status === "done");
  const ms = done.reduce((a, l) => Math.max(a, l.latencyMs ?? 0), 0);
  const steps = [
    { label: "chart", ok: !!run.indexed, detail: run.indexed ? `${run.indexed.chunks} chunks · ${(run.indexed.latencyMs / 1000).toFixed(1)}s` : "" },
    { label: "evidence", ok: done.length === total && total > 0, detail: `${done.length}/${total}${ms ? ` · slowest ${(ms / 1000).toFixed(1)}s` : ""}` },
    { label: "verify", ok: done.length === total && total > 0, detail: `${done.filter((l) => l.downgraded).length} downgraded` },
    { label: "logic", ok: run.decision != null, detail: run.decision ? run.decision.replace("_", " ") : "" },
  ];
  return (
    <footer className="flex h-9 shrink-0 items-center gap-4 border-t border-rule px-4 font-mono text-[11px] text-ink-3">
      <span className="tracking-wide uppercase">Agent trace</span>
      {steps.map((s) => (
        <span key={s.label} className={s.ok ? "text-ink-2" : ""}>
          <span className={s.ok ? "text-signal" : ""} aria-hidden="true">{s.ok ? "✓" : "·"}</span> {s.label}
          {s.detail && <span className="text-ink-3"> {s.detail}</span>}
        </span>
      ))}
      <span className="ml-auto">{run.seen} events</span>
    </footer>
  );
}

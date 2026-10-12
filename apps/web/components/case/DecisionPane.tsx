"use client";

import type { components } from "@/lib/api/schema";
import type { Verdict } from "@/lib/run/reducer";
import { gapKeys } from "@/lib/run/logic";
import { useRunStore } from "@/lib/run/store";
import { VerdictChip } from "@/components/ui/VerdictChip";

type Criterion = components["schemas"]["CriterionOut"];

/** 270° readiness gauge (FRONTEND §6.3). The value is real state from the logic engine. */
function ReadinessDial({ value }: { value: number | null }) {
  const r = 46;
  const arc = 2 * Math.PI * r * 0.75;
  const pct = value ?? 0;
  const color = value == null ? "var(--ink-3)" : pct >= 1 ? "var(--signal)" : pct >= 0.5 ? "var(--gap)" : "var(--fail)";
  return (
    <div className="relative mx-auto h-[120px] w-[120px]">
      <svg viewBox="0 0 120 120" className="h-full w-full rotate-[135deg]" aria-hidden="true">
        <circle cx="60" cy="60" r={r} fill="none" stroke="var(--rule)" strokeWidth="8" strokeLinecap="round" strokeDasharray={`${arc} 999`} />
        <circle
          cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={`${arc * pct} 999`}
          className="transition-[stroke-dasharray] duration-[var(--dur-3)] ease-[var(--ease-out)]"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="display text-3xl tabular">{value == null ? "—" : `${Math.round(pct * 100)}%`}</span>
        <span className="text-[11px] text-ink-3">readiness</span>
      </div>
    </div>
  );
}

export function DecisionPane({
  root,
  leaves,
  selected,
  onSelect,
  onCite,
}: {
  root: Criterion;
  leaves: Criterion[];
  selected: string | null;
  onSelect: (key: string) => void;
  onCite: (chunkId: string, key: string) => void;
}) {
  const run = useRunStore((s) => s.run);
  const states = { ...run.logic, ...Object.fromEntries(Object.entries(run.leaves).map(([k, l]) => [k, l.verdict])) };
  const gapSet = new Set(gapKeys(root, states));
  const gaps = leaves.filter((l) => gapSet.has(l.key));
  const sel = selected ? leaves.find((l) => l.key === selected) : null;
  const sv = sel ? run.leaves[sel.key] : null;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-auto px-4 py-3">
      <h2 className="text-xs tracking-wide text-ink-3 uppercase">Decision</h2>
      <div className="mt-3">
        <ReadinessDial value={run.readiness} />
        <p role="status" className="mt-2 text-center text-sm">
          {run.status === "failed" ? (
            <span className="text-fail">Run failed: {run.error}</span>
          ) : run.decision === "met" ? (
            <span className="text-signal">✓ Ready for packet</span>
          ) : run.decision ? (
            <span className="text-gap">○ Not ready: {gaps.length} criteria need attention</span>
          ) : run.status === "running" ? (
            <span className="text-ink-2">Checking {Object.values(run.leaves).filter((l) => l.status === "done").length} of {leaves.length}…</span>
          ) : (
            <span className="text-ink-3">Not run yet</span>
          )}
        </p>
      </div>

      {sel && sv ? (
        <section aria-label="Evidence" className="mt-5 rounded-[var(--radius-panel)] border border-rule bg-paper-raised p-3">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm text-ink">{sel.label}</p>
            {sv.verdict && <VerdictChip verdict={sv.verdict as Verdict} />}
          </div>
          {sv.rationale && <p className="mt-2 text-sm text-ink-2">{sv.rationale}</p>}
          {sv.downgraded && (
            <p className="mt-2 text-xs text-gap">Downgraded by the citation verifier: {sv.downgraded}</p>
          )}
          <ul className="mt-3 space-y-2">
            {sv.citations.map((c, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => onCite(c.chunk_id, sel.key)}
                  className="w-full rounded-[var(--radius-control)] border-l-2 border-signal/50 bg-paper py-1.5 pr-2 pl-2.5 text-left hover:bg-signal-soft/40"
                >
                  <span className="font-mono text-[12px] leading-snug text-ink">“{c.quote}”</span>
                  <span className={`mt-1 block text-[11px] ${c.verified ? "text-signal" : "text-fail"}`}>
                    {c.verified ? "✓ Verbatim in chart · grounded" : "✕ Failed verification"} · view in chart
                  </span>
                </button>
              </li>
            ))}
            {sv.verdict && sv.citations.length === 0 && (
              <li className="text-xs text-ink-3">No citation. Nothing in the chart settles this criterion.</li>
            )}
          </ul>
        </section>
      ) : null}

      <section className="mt-5">
        <h3 className="text-xs tracking-wide text-ink-3 uppercase">Gaps ({gaps.length})</h3>
        <ul className="mt-2 space-y-1">
          {gaps.map((l) => (
            <li key={l.key}>
              <button type="button" onClick={() => onSelect(l.key)} className="flex w-full items-start gap-2 rounded-[var(--radius-control)] px-1.5 py-1 text-left text-sm hover:bg-paper-raised">
                <span className={run.leaves[l.key]?.verdict === "not_met" ? "text-fail" : "text-gap"} aria-hidden="true">
                  {run.leaves[l.key]?.verdict === "not_met" ? "✕" : "○"}
                </span>
                <span className="text-ink-2">{l.label}</span>
              </button>
            </li>
          ))}
          {gaps.length === 0 && <li className="text-sm text-ink-3">None.</li>}
        </ul>
      </section>

      <div className="mt-auto pt-4">
        <button type="button" disabled className="h-9 w-full rounded-[var(--radius-control)] bg-signal font-medium text-paper disabled:opacity-40" title="Human review and packet build arrive in Phase 4">
          Approve for packet
        </button>
      </div>
    </div>
  );
}

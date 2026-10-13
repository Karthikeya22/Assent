"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import {
  decide,
  overrideVerdict,
  setGapStatus,
} from "@/app/(app)/app/cases/[id]/actions";
import type { components } from "@/lib/api/schema";
import type { ObjectionState, Verdict } from "@/lib/run/reducer";
import { gapKeys } from "@/lib/run/logic";
import { useRunStore } from "@/lib/run/store";
import { VerdictChip } from "@/components/ui/VerdictChip";
import { PacketPanel } from "./PacketPanel";

type Criterion = components["schemas"]["CriterionOut"];

/** 270° readiness gauge (FRONTEND §6.3). The value is real state from the logic engine. */
function ReadinessDial({ value }: { value: number | null }) {
  const r = 46;
  const arc = 2 * Math.PI * r * 0.75;
  const pct = value ?? 0;
  const color =
    value == null
      ? "var(--ink-3)"
      : pct >= 1
        ? "var(--signal)"
        : pct >= 0.5
          ? "var(--gap)"
          : "var(--fail)";
  return (
    <div className="relative mx-auto h-[120px] w-[120px]">
      <svg
        viewBox="0 0 120 120"
        className="h-full w-full rotate-[135deg]"
        aria-hidden="true"
      >
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke="var(--rule)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${arc} 999`}
        />
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${arc * pct} 999`}
          className="transition-[stroke-dasharray] duration-[var(--dur-3)] ease-[var(--ease-out)]"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`display tabular ${pct >= 1 ? "text-[1.6rem]" : "text-3xl"}`}>
          {value == null ? "—" : `${Math.round(pct * 100)}%`}
        </span>
        <span className="text-[11px] text-ink-3">readiness</span>
      </div>
    </div>
  );
}

const H3 = "text-xs tracking-wide text-ink-3 uppercase";
const STATUS_CHIP: Record<ObjectionState["status"], string> = {
  open: "text-ink-3 border-rule",
  rebutted: "text-signal border-signal/40",
  conceded: "text-gap border-gap/40",
};

/** Two agents, one packet: the payer's objection in adversary purple, the advocate's answer under it. */
function ObjectionThread({
  obs,
  labels,
  onSelect,
}: {
  obs: ObjectionState[];
  labels: Record<string, string>;
  onSelect: (k: string) => void;
}) {
  if (!obs.length)
    return <p className="mt-2 text-sm text-ink-3">No objections raised.</p>;
  return (
    <ul className="mt-2 space-y-3">
      {obs.map((o) => (
        <li key={o.id} className="text-sm">
          <div className="border-l-2 border-adversary pl-2.5">
            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => o.criterion_id && onSelect(o.criterion_id)}
                className="truncate text-left text-xs text-ink-3 hover:text-ink"
              >
                {o.criterion_id
                  ? (labels[o.criterion_id] ?? o.criterion_id)
                  : "General"}
              </button>
              <span className="shrink-0 font-mono text-[10px] text-adversary uppercase">
                {o.severity}
              </span>
            </div>
            <p className="mt-0.5 text-adversary">{o.text}</p>
          </div>
          <div className="mt-1.5 ml-3 flex items-start gap-2">
            <span
              className={`mt-0.5 shrink-0 rounded-full border px-1.5 text-[10px] ${STATUS_CHIP[o.status]}`}
            >
              {o.status}
            </span>
            <p className="text-ink-2">
              {o.status === "open" ? "Advocate is answering…" : o.rebuttal}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function OverrideForm({
  caseId,
  verdictId,
  current,
}: {
  caseId: string;
  verdictId: string;
  current: Verdict;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [verdict, setVerdict] = useState<Verdict>(current);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  if (!open)
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-3 text-xs text-ink-3 underline underline-offset-4 hover:text-ink"
      >
        Override verdict
      </button>
    );
  return (
    <form
      className="mt-3 space-y-2 border-t border-rule pt-3"
      onSubmit={(e) => {
        e.preventDefault();
        start(async () => {
          const r = await overrideVerdict(
            caseId,
            verdictId,
            verdict,
            reason.trim(),
          );
          if (r.error) setError(r.error);
          else {
            setOpen(false);
            router.refresh();
          }
        });
      }}
    >
      <label className="block text-xs text-ink-2">
        New verdict
        <select
          value={verdict}
          onChange={(e) => setVerdict(e.target.value as Verdict)}
          className="mt-1 h-8 w-full rounded-[var(--radius-control)] border border-rule bg-paper px-2 text-sm"
        >
          <option value="met">Met</option>
          <option value="not_met">Not met</option>
          <option value="insufficient">Insufficient</option>
        </select>
      </label>
      <label className="block text-xs text-ink-2">
        Reason (required, recorded in the audit log)
        <textarea
          required
          minLength={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
          className="mt-1 w-full rounded-[var(--radius-control)] border border-rule bg-paper px-2 py-1 text-sm"
        />
      </label>
      {error && (
        <p role="alert" className="text-xs text-fail">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={pending}
          className="h-8 rounded-[var(--radius-control)] bg-ink px-3 text-xs text-paper disabled:opacity-50"
        >
          Save override
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="h-8 px-2 text-xs text-ink-3"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export function DecisionPane({
  caseId,
  runId,
  caseStatus,
  root,
  leaves,
  selected,
  onSelect,
  onCite,
  packets,
  readOnly = false,
}: {
  caseId: string;
  runId: string | null;
  caseStatus: string;
  root: Criterion;
  leaves: Criterion[];
  selected: string | null;
  onSelect: (key: string) => void;
  onCite: (chunkId: string, key: string) => void;
  packets: components["schemas"]["PacketOut"][];
  readOnly?: boolean; // the public demo: show everything, change nothing
}) {
  const router = useRouter();
  const run = useRunStore((s) => s.run);
  const states = {
    ...run.logic,
    ...Object.fromEntries(
      Object.entries(run.leaves).map(([k, l]) => [k, l.verdict]),
    ),
  };
  const gapSet = new Set(gapKeys(root, states));
  const blocking = leaves.filter((l) => gapSet.has(l.key));
  const labels = Object.fromEntries(leaves.map((l) => [l.key, l.label]));
  const objections = Object.values(run.objections);
  const highOpen = objections.filter(
    (o) => o.severity === "high" && o.status !== "rebutted",
  );
  const sel = selected ? leaves.find((l) => l.key === selected) : null;
  const sv = sel ? run.leaves[sel.key] : null;
  const [ack, setAck] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const finished = run.status === "finished" && runId;
  const decided = [
    "ready",
    "submitted",
    "approved",
    "denied",
    "appealed",
  ].includes(caseStatus);

  function act(decision: "approve" | "reject", acknowledge = false) {
    setError(null);
    start(async () => {
      const r = await decide(caseId, runId!, decision, acknowledge);
      if (r.needsAck) setAck(true);
      else if (r.error) setError(r.error);
      else {
        setAck(false);
        router.refresh();
      }
    });
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-auto px-4 py-3">
      <h2 className={H3}>Decision</h2>
      <div className="mt-3">
        <ReadinessDial value={run.readiness} />
        <p role="status" className="mt-2 text-center text-sm">
          {run.status === "failed" ? (
            <span className="text-fail">Run failed: {run.error}</span>
          ) : decided ? (
            <span className="text-signal">✓ Approved for packet</span>
          ) : run.decision === "met" ? (
            <span className="text-signal">✓ Criteria met, awaiting review</span>
          ) : run.decision ? (
            <span className="text-gap">
              ○ Not ready: {blocking.length} criteria need attention
            </span>
          ) : run.status === "running" ? (
            <span className="text-ink-2">
              Checking{" "}
              {
                Object.values(run.leaves).filter((l) => l.status === "done")
                  .length
              }{" "}
              of {leaves.length}…
            </span>
          ) : (
            <span className="text-ink-3">Not run yet</span>
          )}
        </p>
        {run.denialRisk != null && (
          <div className="mt-3 rounded-[var(--radius-control)] border border-rule px-3 py-2">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-ink-3">Denial risk</span>
              <span
                className={`display text-xl tabular ${run.denialRisk >= 0.5 ? "text-fail" : run.denialRisk >= 0.25 ? "text-gap" : "text-signal"}`}
              >
                {Math.round(run.denialRisk * 100)}%
              </span>
            </div>
            <ul className="mt-1 space-y-0.5">
              {run.riskFactors.map((f) => (
                <li key={f} className="text-xs text-ink-2">
                  · {f}
                </li>
              ))}
            </ul>
          </div>
        )}
        {run.reviewError && (
          <p className="mt-2 text-xs text-gap">
            Review stage incomplete: {run.reviewError}
          </p>
        )}
      </div>

      {sel && sv ? (
        <section
          aria-label="Evidence"
          className="mt-5 rounded-[var(--radius-panel)] border border-rule bg-paper-raised p-3"
        >
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm text-ink">{sel.label}</p>
            {sv.verdict && <VerdictChip verdict={sv.verdict as Verdict} />}
          </div>
          {sv.overridden && (
            <p className="mt-1 text-xs text-ink-3">
              Overridden by a reviewer: {sv.overrideReason}
            </p>
          )}
          {sv.rationale && (
            <p className="mt-2 text-sm text-ink-2">{sv.rationale}</p>
          )}
          {sv.downgraded && (
            <p className="mt-2 text-xs text-gap">
              Downgraded by the citation verifier: {sv.downgraded}
            </p>
          )}
          <ul className="mt-3 space-y-2">
            {sv.citations.map((c, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => onCite(c.chunk_id, sel.key)}
                  className="w-full rounded-[var(--radius-control)] bg-paper-raised px-2.5 py-1.5 text-left ring-1 ring-rule transition-colors duration-[var(--dur-1)] hover:bg-signal-soft/40 hover:ring-signal/40"
                >
                  <span className="font-mono text-xs leading-snug text-ink underline decoration-signal/45 underline-offset-[3px]">
                    “{c.quote}”
                  </span>
                  <span
                    className={`mt-1 block text-xs ${c.verified ? "text-signal" : "text-fail"}`}
                  >
                    {c.verified
                      ? "✓ Verbatim in chart · grounded"
                      : "✕ Failed verification"}{" "}
                    · view in chart
                  </span>
                </button>
              </li>
            ))}
            {sv.verdict && sv.citations.length === 0 && (
              <li className="text-xs text-ink-3">
                No citation. Nothing in the chart settles this criterion.
              </li>
            )}
          </ul>
          {!readOnly && sv.verdictId && sv.verdict && (
            <OverrideForm
              key={sv.verdictId}
              caseId={caseId}
              verdictId={sv.verdictId}
              current={sv.verdict as Verdict}
            />
          )}
        </section>
      ) : null}

      <section className="mt-5">
        <h3 className={H3}>Payer objections ({objections.length})</h3>
        {run.status === "finished" || objections.length ? (
          <ObjectionThread
            obs={objections}
            labels={labels}
            onSelect={onSelect}
          />
        ) : (
          <p className="mt-2 text-sm text-ink-3">
            Raised after the evidence pass.
          </p>
        )}
      </section>

      <section className="mt-5">
        <h3 className={H3}>Gap tasks ({run.gaps.length})</h3>
        <ul className="mt-2 space-y-2">
          {run.gaps.map((g, i) => (
            <li
              key={g.id ?? i}
              className="rounded-[var(--radius-control)] border border-rule bg-paper-raised p-2.5"
            >
              <div className="flex items-start justify-between gap-2">
                <button
                  type="button"
                  onClick={() => g.criterion_id && onSelect(g.criterion_id)}
                  className="text-left text-sm text-ink hover:text-signal"
                >
                  {g.title}
                </button>
                <span className="shrink-0 font-mono text-[10px] text-ink-3 uppercase">
                  {g.assignee_role}
                </span>
              </div>
              <p className="mt-1 text-xs text-ink-2">{g.detail}</p>
              {!readOnly && g.id && (
                <button
                  type="button"
                  onClick={() =>
                    start(async () => {
                      await setGapStatus(caseId, g.id!, "done");
                      router.refresh();
                    })
                  }
                  className="mt-1.5 text-xs text-ink-3 underline underline-offset-4 hover:text-ink"
                >
                  Mark done
                </button>
              )}
            </li>
          ))}
          {run.gaps.length === 0 && (
            <li className="text-sm text-ink-3">
              {run.status === "finished"
                ? "None."
                : "Planned after the evidence pass."}
            </li>
          )}
        </ul>
      </section>

      {!readOnly && decided && (
        <PacketPanel
          caseId={caseId}
          runId={runId}
          caseStatus={caseStatus}
          packets={packets}
        />
      )}

      {!readOnly && (
        <div className="mt-auto space-y-2 pt-4">
          {error && (
            <p role="alert" className="text-xs text-fail">
              {error}
            </p>
          )}
          {ack && (
            <div
              role="alertdialog"
              aria-label="Acknowledge objections"
              className="rounded-[var(--radius-control)] border border-adversary/40 p-2.5 text-xs text-ink-2"
            >
              Approving anyway records that you reviewed:
              <ul className="mt-1 list-disc pl-4">
                {run.decision !== "met" && (
                  <li>{blocking.length} coverage criteria not yet proven</li>
                )}
                {highOpen.length > 0 && (
                  <li>
                    {highOpen.length} high-severity payer objection(s) not
                    rebutted
                  </li>
                )}
              </ul>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => act("approve", true)}
                  className="h-8 rounded-[var(--radius-control)] bg-ink px-3 text-paper"
                >
                  Approve anyway
                </button>
                <button
                  type="button"
                  onClick={() => setAck(false)}
                  className="h-8 px-2 text-ink-3"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!finished || pending || decided}
              onClick={() =>
                highOpen.length || run.decision !== "met"
                  ? setAck(true)
                  : act("approve")
              }
              className="h-9 flex-1 rounded-[var(--radius-control)] bg-signal font-medium text-paper-raised transition-colors duration-[var(--dur-1)] hover:bg-signal-deep disabled:cursor-not-allowed disabled:bg-paper-sunk disabled:text-ink-3"
            >
              {decided ? "Approved" : "Approve for packet"}
            </button>
            <button
              type="button"
              disabled={!finished || pending || decided}
              onClick={() => act("reject")}
              className="h-9 rounded-[var(--radius-control)] border border-rule px-3 text-ink-2 hover:text-ink disabled:cursor-not-allowed disabled:text-ink-3/70"
            >
              Reject
            </button>
          </div>
          {!finished && !decided && <p className="text-xs text-ink-3">Run the case to approve or reject it.</p>}
        </div>
      )}
    </div>
  );
}

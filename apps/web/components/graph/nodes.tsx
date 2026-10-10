"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { memo } from "react";
import { useRunStore } from "@/lib/run/store";
import type { LogicState, Verdict } from "@/lib/run/reducer";

export type LeafData = { label: string; evidence: string; index: number; selected: boolean };
export type LogicData = { kind: string; nRequired: number | null; childKeys: string[] };
export type RootData = { sourceId: string; title: string };

const GLYPH: Record<Verdict, string> = { met: "✓", not_met: "✕", insufficient: "○" };
const LABEL: Record<Verdict, string> = { met: "Met", not_met: "Not met", insufficient: "Insufficient" };
const TONE: Record<Verdict, { border: string; fill: string; text: string }> = {
  met: { border: "border-signal", fill: "bg-signal-soft", text: "text-signal" },
  not_met: { border: "border-fail", fill: "bg-fail/10", text: "text-fail" },
  insufficient: { border: "border-gap border-dashed", fill: "bg-gap/10", text: "text-gap" },
};
const hidden = "!h-1 !w-1 !min-w-0 !border-0 !bg-transparent";

export const LeafNode = memo(function LeafNode({ id, data }: NodeProps & { data: LeafData }) {
  const leaf = useRunStore((s) => s.run.leaves[id]);
  const v = leaf?.verdict;
  const running = leaf?.status === "running";
  const tone = v ? TONE[v] : null;
  return (
    <div
      className={`leaf-node relative w-[240px] overflow-hidden rounded-[var(--radius-panel)] border bg-paper-raised px-3 py-2.5 ${
        tone ? tone.border : "border-rule"
      } ${running ? "is-running" : ""} ${data.selected ? "ring-2 ring-focus ring-offset-2 ring-offset-paper" : ""}`}
      aria-label={`${data.label}: ${v ? LABEL[v] : running ? "checking" : "not checked yet"}`}
    >
      {/* Verdict fill rises from the bottom when the criterion resolves (dur-3, 420ms). */}
      <span
        aria-hidden="true"
        className={`absolute inset-0 origin-bottom transition-transform duration-[var(--dur-3)] ease-[var(--ease-out)] ${
          tone ? `${tone.fill} scale-y-100` : "scale-y-0"
        }`}
      />
      <Handle type="source" position={Position.Top} className={hidden} />
      <div className="relative">
        <div className="flex items-start gap-2">
          <span className="mt-0.5 font-mono text-[0.7rem] text-ink-3 tabular">{data.index}</span>
          <p className="line-clamp-2 flex-1 text-[0.8125rem] leading-snug text-ink">{data.label}</p>
        </div>
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="font-mono text-[0.68rem] text-ink-3">{data.evidence}</span>
          {v ? (
            <span className={`inline-flex items-center gap-1 text-xs font-medium ${tone!.text}`}>
              <span aria-hidden="true">{GLYPH[v]}</span>
              {LABEL[v]}
            </span>
          ) : (
            <span className="text-xs text-ink-3">{running ? "Checking…" : "Not checked"}</span>
          )}
        </div>
        {v && leaf?.confidence != null && (
          <div className="mt-1.5 h-[3px] rounded-full bg-rule" aria-hidden="true">
            <div
              className={`h-full rounded-full transition-[width] duration-[var(--dur-3)] ${v === "met" ? "bg-signal" : v === "not_met" ? "bg-fail" : "bg-gap"}`}
              style={{ width: `${Math.round(leaf.confidence * 100)}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
});

function ring(state: LogicState | undefined) {
  return state === "met" ? "var(--signal)" : state === "not_met" ? "var(--fail)" : state ? "var(--gap)" : "var(--ink-3)";
}

export const LogicNode = memo(function LogicNode({ id, data }: NodeProps & { data: LogicData }) {
  const state = useRunStore((s) => s.run.logic[id]);
  const met = useRunStore((s) =>
    data.childKeys.filter((k) => (s.run.leaves[k]?.verdict ?? s.run.logic[k]) === "met").length,
  );
  const need = data.kind === "AND" ? data.childKeys.length : data.kind === "OR" ? 1 : (data.nRequired ?? 1);
  const pct = Math.min(1, met / need);
  const label = data.kind === "N_OF_M" ? `${data.nRequired} of ${data.childKeys.length}` : data.kind;
  return (
    <div
      className="flex h-9 items-center gap-2 rounded-full border border-rule bg-paper-raised px-2.5"
      aria-label={`${label}: ${met} of ${need} satisfied${state ? `, ${state.replace("_", " ")}` : ""}`}
    >
      <Handle type="target" position={Position.Bottom} className={hidden} />
      <Handle type="source" position={Position.Top} className={hidden} />
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" className="-rotate-90">
        <circle cx="9" cy="9" r="7" fill="none" stroke="var(--rule)" strokeWidth="2.5" />
        <circle
          cx="9" cy="9" r="7" fill="none" stroke={ring(state)} strokeWidth="2.5" strokeLinecap="round"
          strokeDasharray={`${pct * 44} 44`}
          className="transition-[stroke-dasharray] duration-[var(--dur-3)]"
        />
      </svg>
      <span className="font-mono text-[0.72rem] text-ink-2">{label}</span>
    </div>
  );
});

export const RootNode = memo(function RootNode({ id, data }: NodeProps & { data: RootData }) {
  const state = useRunStore((s) => s.run.logic[id]);
  const decided = state === "met" ? "Coverage criteria met" : state === "not_met" ? "Criteria not met" : state ? "Evidence incomplete" : "Awaiting run";
  return (
    <div className="w-[300px] rounded-[var(--radius-panel)] border border-rule bg-paper-raised px-4 py-3 text-center">
      <Handle type="target" position={Position.Bottom} className={hidden} />
      <span className="font-mono text-[0.7rem] text-ink-3">{data.sourceId}</span>
      <p className="display mt-0.5 text-lg leading-tight">{data.title}</p>
      <p className={`mt-1 text-xs font-medium ${state === "met" ? "text-signal" : state === "not_met" ? "text-fail" : state ? "text-gap" : "text-ink-3"}`}>
        {decided}
      </p>
    </div>
  );
});

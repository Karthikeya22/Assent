"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { components } from "@/lib/api/schema";
import { clauseRuns, type Span } from "@/lib/policy/runs";

type Criterion = components["schemas"]["CriterionOut"];

const KIND_LABEL = (c: Criterion) =>
  c.kind === "N_OF_M" ? `${c.n_required} of ${c.children.length}` : c.kind;

const EVIDENCE: Record<string, string> = {
  diagnosis: "dx",
  duration: "duration",
  assessment: "assessment",
  imaging_finding: "imaging",
  prior_therapy: "prior tx",
  contraindication: "contra",
  procedure_history: "history",
};

function leavesOf(c: Criterion): Criterion[] {
  return c.kind === "LEAF" ? [c] : c.children.flatMap(leavesOf);
}

function threshold(t: Criterion["threshold"]): string | null {
  if (!t) return null;
  return Object.entries(t)
    .map(([k, v]) => `${k.replaceAll("_", " ")}: ${Array.isArray(v) ? v.join(", ") : v}`)
    .join(" · ");
}

/** LCD text and its criteria tree, cross-linked: hover either side to find the other. */
export function PolicyWorkspace({ text, root }: { text: string; root: Criterion }) {
  const leaves = useMemo(() => leavesOf(root), [root]);
  const index = useMemo(() => new Map(leaves.map((l, i) => [l.key, i + 1])), [leaves]);
  const spans: Span[] = useMemo(
    () =>
      leaves
        .filter((l) => l.span)
        .map((l) => ({ key: l.key, start: l.span![0], end: l.span![1] }))
        .sort((a, b) => a.start - b.start),
    [leaves],
  );
  const runs = useMemo(() => clauseRuns(text, spans), [text, spans]);
  const [active, setActive] = useState<string | null>(null);
  const textPane = useRef<HTMLDivElement>(null);

  // Open on the coverage section rather than the background prose.
  useEffect(() => {
    textPane.current?.querySelector(`[data-key="${spans[0]?.key}"]`)?.scrollIntoView({
      block: "center",
    });
  }, [spans]);

  function focusClause(key: string) {
    setActive(key);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    textPane.current
      ?.querySelector(`[data-key="${key}"]`)
      ?.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
  }

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_minmax(340px,440px)] border-t border-rule">
      <div ref={textPane} className="min-h-0 overflow-auto px-6 py-5">
        <p className="mx-auto max-w-[72ch] text-md leading-[1.75] whitespace-pre-wrap text-ink-2">
          {runs.map((r, i) =>
            r.key ? (
              <mark
                key={i}
                data-key={r.key}
                onMouseEnter={() => setActive(r.key)}
                onMouseLeave={() => setActive(null)}
                className={`rounded-[3px] px-0.5 text-ink transition-colors duration-[var(--dur-1)] ${
                  active === r.key ? "bg-signal-soft" : "bg-transparent underline decoration-signal/40 underline-offset-4"
                }`}
              >
                {r.text}
                <sup className="ml-0.5 font-mono text-[0.65rem] text-signal">{index.get(r.key)}</sup>
              </mark>
            ) : (
              <span key={i}>{r.text}</span>
            ),
          )}
        </p>
      </div>

      <aside aria-label="Criteria tree" className="min-h-0 overflow-auto border-l border-rule px-5 py-5">
        <h2 className="text-xs tracking-wide text-ink-3 uppercase">Criteria tree</h2>
        <p className="mt-1 text-sm text-ink-2">
          {leaves.length} checkable criteria. Hover one to find its clause.
        </p>
        <ul className="mt-4">
          <TreeNode node={root} depth={0} active={active} index={index} onFocus={focusClause} onBlur={() => setActive(null)} />
        </ul>
      </aside>
    </div>
  );
}

function TreeNode({
  node,
  depth,
  active,
  index,
  onFocus,
  onBlur,
}: {
  node: Criterion;
  depth: number;
  active: string | null;
  index: Map<string, number>;
  onFocus: (k: string) => void;
  onBlur: () => void;
}) {
  if (node.kind === "LEAF") {
    const t = threshold(node.threshold);
    const on = active === node.key;
    return (
      <li>
        <button
          type="button"
          onMouseEnter={() => onFocus(node.key)}
          onMouseLeave={onBlur}
          onFocus={() => onFocus(node.key)}
          onBlur={onBlur}
          className={`flex w-full items-start gap-2 rounded-[var(--radius-control)] py-1.5 pr-2 text-left transition-colors duration-[var(--dur-1)] ${
            on ? "bg-signal-soft" : "hover:bg-paper-raised"
          }`}
          style={{ paddingLeft: depth * 16 + 4 }}
        >
          <span className="mt-0.5 w-5 shrink-0 text-right font-mono text-xs text-signal tabular">
            {index.get(node.key)}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm text-ink">{node.label}</span>
            <span className="mt-0.5 flex flex-wrap gap-x-2 font-mono text-[0.7rem] text-ink-3">
              <span>{EVIDENCE[node.evidence_type ?? ""] ?? node.evidence_type}</span>
              {t && <span>{t}</span>}
              {!node.span && <span className="text-gap">no source clause</span>}
            </span>
          </span>
        </button>
      </li>
    );
  }
  return (
    <li>
      <div className="flex items-center gap-2 py-1.5" style={{ paddingLeft: depth * 16 + 4 }}>
        <span className="rounded-[var(--radius-control)] border border-rule px-1.5 font-mono text-[0.7rem] text-ink-2">
          {KIND_LABEL(node)}
        </span>
        <span className="text-sm text-ink-2">{node.label}</span>
      </div>
      <ul>
        {node.children.map((c) => (
          <TreeNode key={c.key} node={c} depth={depth + 1} active={active} index={index} onFocus={onFocus} onBlur={onBlur} />
        ))}
      </ul>
    </li>
  );
}

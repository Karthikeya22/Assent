"use client";

import { useEffect, useRef, useState } from "react";

const BOXES = [
  { id: "ehr", x: 20, y: 40, label: "EHR (sim)", tech: "CDS Hooks client · FHIR R4 charts" },
  { id: "cds", x: 20, y: 150, label: "cds-service", tech: "FastAPI · order-sign hook" },
  { id: "web", x: 250, y: 40, label: "web", tech: "Next.js 15 · React Flow + ELK · R3F" },
  { id: "api", x: 250, y: 150, label: "api", tech: "FastAPI · JWT + RBAC · hash-chained audit log · SSE" },
  { id: "worker", x: 480, y: 150, label: "worker", tech: "arq · LangGraph case + appeal graphs · local NLI / rerank" },
  { id: "pg", x: 250, y: 260, label: "postgres", tech: "pgvector · tsvector FTS · criteria trees · runs" },
  { id: "redis", x: 480, y: 40, label: "redis", tech: "job queue · run event bus" },
  { id: "payer", x: 480, y: 260, label: "mock-payer", tech: "PAS $submit · hidden evidence rules · pended decisions" },
  { id: "llm", x: 700, y: 150, label: "LLMs", tech: "gpt-4.1 evidence · gemini adversary · gpt-4.1-mini judge" },
];
const EDGES: [string, string][] = [
  ["ehr", "cds"], ["cds", "api"], ["web", "api"], ["api", "redis"], ["redis", "worker"],
  ["api", "pg"], ["worker", "pg"], ["api", "payer"], ["worker", "llm"],
];
const W = 170;
const H = 52;

/** The service diagram draws itself once on enter; hover a service for its stack. */
export function Architecture() {
  const root = useRef<SVGSVGElement>(null);
  const [on, setOn] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => e.isIntersecting && (setOn(true), io.disconnect()), { threshold: 0.3 });
    if (root.current) io.observe(root.current);
    return () => io.disconnect();
  }, []);
  const at = Object.fromEntries(BOXES.map((b) => [b.id, b]));
  const hb = hover ? at[hover] : null;
  return (
    <section aria-labelledby="arch" className="mx-auto max-w-6xl px-6 py-24 md:py-40">
      <h2 id="arch" className="display text-4xl md:text-5xl">How it&rsquo;s built.</h2>
      <p className="mt-3 text-ink-2">Every service runs on a 7 GB laptop; hover one for its stack.</p>
      <div className="relative mt-10 overflow-x-auto">
        <svg ref={root} viewBox="0 0 900 340" className={`arch min-w-[720px] ${on ? "arch-on" : ""}`} role="img" aria-label="Assent services and how they connect">
          {EDGES.map(([a, b], i) => {
            const p = at[a];
            const q = at[b];
            return (
              <line key={i} x1={p.x + W / 2} y1={p.y + H / 2} x2={q.x + W / 2} y2={q.y + H / 2} pathLength={1} className="arch-edge" style={{ animationDelay: `${0.5 + i * 0.08}s` }} />
            );
          })}
          {BOXES.map((b, i) => (
            <g key={b.id} onMouseEnter={() => setHover(b.id)} onMouseLeave={() => setHover(null)} tabIndex={0} onFocus={() => setHover(b.id)} onBlur={() => setHover(null)}>
              <rect x={b.x} y={b.y} width={W} height={H} rx="6" pathLength={1} className="arch-box" style={{ animationDelay: `${i * 0.1}s` }} />
              <text x={b.x + 14} y={b.y + 31} className="fill-ink font-mono" fontSize="14">{b.label}</text>
            </g>
          ))}
        </svg>
        {hb && (
          <p role="tooltip" className="pointer-events-none absolute rounded-[var(--radius-control)] border border-rule bg-paper-raised px-2.5 py-1.5 text-xs text-ink shadow-[var(--shadow-float)]" style={{ left: `${(hb.x / 900) * 100}%`, top: `${((hb.y + H + 8) / 340) * 100}%` }}>
            {hb.tech}
          </p>
        )}
      </div>
    </section>
  );
}

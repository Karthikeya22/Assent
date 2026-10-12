"use client";

import { useEffect, useRef, useState } from "react";
import run from "@/content/agents-run.json";

type Msg = { side: "adversary" | "advocate"; criterion: string; text: string; status?: string };

const MSGS: Msg[] = run.objections.flatMap((o) => [
  { side: "adversary" as const, criterion: o.criterion, text: o.text },
  { side: "advocate" as const, criterion: o.criterion, text: o.rebuttal, status: o.status },
]);
const CPS = 240; // characters per second: roughly a streamed model's cadence

/** Two agents, one packet: the recorded Phase 4 review, streamed once when it scrolls into view. */
export function TwoAgents() {
  const root = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(0); // characters revealed across all messages
  const total = MSGS.reduce((s, m) => s + m.text.length, 0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(total);
      return;
    }
    let raf = 0;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        const t0 = performance.now();
        const step = (t: number) => {
          const n = Math.min(total, Math.floor(((t - t0) / 1000) * CPS));
          setShown(n);
          if (n < total) raf = requestAnimationFrame(step);
        };
        raf = requestAnimationFrame(step);
      },
      { threshold: 0.3 },
    );
    if (root.current) io.observe(root.current);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [total]);

  let left = shown;
  const risk = Math.round((run.denial_risk ?? 0) * 100);
  const done = shown >= total;
  return (
    <section aria-labelledby="agents" className="mx-auto max-w-6xl px-6 py-24 md:py-40">
      <h2 id="agents" className="display text-4xl md:text-5xl">Two agents, one packet.</h2>
      <p className="mt-3 max-w-2xl text-ink-2">
        A recorded review of a real benchmark case (CPT {run.case.cpt}, ICD-10 {run.case.icd10}). The payer adversary runs on a
        different model vendor than the advocate, so they don&rsquo;t share blind spots.
      </p>
      <div ref={root} className="mt-10 space-y-5">
        {MSGS.map((m, i) => {
          const n = Math.max(0, Math.min(m.text.length, left));
          left -= m.text.length;
          if (n === 0 && i > 0) return null;
          const adv = m.side === "adversary";
          return (
            <div key={i} className={`grid gap-1 md:w-[78%] ${adv ? "md:ml-auto" : ""}`}>
              <p className={`font-mono text-[11px] uppercase ${adv ? "text-adversary" : "text-ink-3"}`}>
                {adv ? "Payer adversary" : "Advocate"} · <span className="normal-case">{m.criterion.length > 70 ? `${m.criterion.slice(0, 68)}…` : m.criterion}</span>
              </p>
              <p className={`text-[15px] leading-relaxed ${adv ? "border-l-2 border-adversary pl-3 text-adversary" : "text-ink"}`}>
                {m.text.slice(0, n)}
                {n < m.text.length && <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 bg-ink-3" aria-hidden="true" />}
              </p>
              {m.status && n === m.text.length && (
                <span className={`w-fit rounded-full border px-2 text-[11px] ${m.status === "rebutted" ? "border-signal/40 text-signal" : "border-gap/40 text-gap"}`}>
                  {m.status}
                </span>
              )}
            </div>
          );
        })}
      </div>
      <div className={`mt-10 flex items-baseline gap-4 border-t border-rule pt-6 transition-opacity duration-[var(--dur-3)] ${done ? "opacity-100" : "opacity-0"}`}>
        <span className="text-sm text-ink-3">Denial risk after review</span>
        <span className="display text-5xl text-fail tabular">{risk}%</span>
        <span className="text-sm text-ink-2">One conceded objection and two unproven criteria kept it high. Assent says so instead of hiding it.</span>
      </div>
    </section>
  );
}

"use client";

import { useState } from "react";
import gb from "@/content/glassbox.json";

/** The glass box: hover a criterion and its exact quoted span lights up in a real benchmark note. */
export function GlassBox() {
  const [active, setActive] = useState<string | null>(null);
  const quote = gb.rows.find((r) => r.key === active)?.quote;
  const i = quote ? gb.note.indexOf(quote) : -1;
  return (
    <section aria-labelledby="glass" className="mx-auto max-w-6xl px-6 py-24 md:py-40">
      <h2 id="glass" className="display text-4xl md:text-5xl">No claim without a citation.</h2>
      <p className="mt-3 text-ink-2">Hover any criterion. This is a real note from the benchmark (synthetic patient).</p>
      <div className="mt-10 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <pre className="overflow-x-auto rounded-[var(--radius-panel)] border border-rule bg-paper-raised p-5 font-mono text-[13px] leading-relaxed whitespace-pre-wrap text-ink">
          {i < 0 ? (
            gb.note
          ) : (
            <>
              {gb.note.slice(0, i)}
              <mark key={active} className="glass-mark text-ink">
                {quote}
              </mark>
              {gb.note.slice(i + quote!.length)}
            </>
          )}
        </pre>
        <ul className="divide-y divide-rule border-y border-rule">
          {gb.rows.map((r) => (
            <li key={r.key}>
              <button
                type="button"
                onMouseEnter={() => setActive(r.key)}
                onFocus={() => setActive(r.key)}
                onMouseLeave={() => setActive(null)}
                className={`flex w-full items-start gap-3 px-2 py-3 text-left text-sm transition-colors duration-[var(--dur-1)] ${active === r.key ? "bg-signal-soft/50" : ""}`}
              >
                <span className="mt-0.5 font-mono text-signal">✓</span>
                <span className="text-ink">{r.label}</span>
              </button>
            </li>
          ))}
          <li className="flex items-start justify-between gap-3 px-2 py-3 text-sm">
            <span className="flex gap-3">
              <span className="mt-0.5 font-mono text-gap">○</span>
              <span>
                <span className="text-ink">{gb.missing.label}</span>
                <span className="mt-0.5 block text-xs text-gap">No evidence found in this note</span>
              </span>
            </span>
            <span className="shrink-0 rounded-[var(--radius-control)] border border-rule px-2 py-1 text-xs text-ink-2">Create task</span>
          </li>
        </ul>
      </div>
    </section>
  );
}

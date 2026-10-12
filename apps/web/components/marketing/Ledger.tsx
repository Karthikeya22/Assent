"use client";

import gsap from "gsap";
import { useEffect, useRef } from "react";

const ROWS = [
  { value: 40, suffix: "", label: "prior authorizations per physician, per week", src: 1 },
  { value: 13, suffix: "", label: "hours of physician and staff time, every week", src: 1 },
  { value: 95, suffix: "%", label: "of physicians say it delays access to necessary care", src: 1 },
];

/** The problem, as a ledger: three sourced numbers that count up once when they enter. */
export function Ledger() {
  const nums = useRef<(HTMLSpanElement | null)[]>([]);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const els = nums.current.filter(Boolean) as HTMLSpanElement[];
    // Real numbers stay in the HTML; zero them only while still offscreen, just before entry.
    const arm = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting && e.boundingClientRect.top > window.innerHeight * 0.6) {
          els.forEach((el) => (el.textContent = "0"));
          arm.disconnect();
        }
      },
      { rootMargin: "0px 0px 300px 0px" },
    );
    if (root.current) arm.observe(root.current);
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        els.forEach((el, i) => {
          const o = { v: 0 };
          gsap.to(o, { v: ROWS[i].value, duration: 0.9, ease: "power2.out", onUpdate: () => (el.textContent = String(Math.round(o.v))) });
        });
      },
      { threshold: 0.4 },
    );
    if (root.current) io.observe(root.current);
    return () => {
      arm.disconnect();
      io.disconnect();
    };
  }, []);
  return (
    <section aria-labelledby="problem" className="mx-auto max-w-6xl px-6 py-24 md:py-40">
      <h2 id="problem" className="sr-only">The problem</h2>
      <div ref={root} className="grid divide-y divide-rule border-y border-rule md:grid-cols-3 md:divide-x md:divide-y-0">
        {ROWS.map((r, i) => (
          <div key={r.label} className="px-2 py-10 md:px-8">
            <p className="display text-[clamp(4rem,9vw,7.5rem)] leading-none tabular">
              <span ref={(el) => void (nums.current[i] = el)}>{r.value}</span>
              {r.suffix}
              <a href={`#source-${r.src}`} className="ml-1 align-super font-mono text-sm text-ink-3 hover:text-ink" aria-label={`Source ${r.src}`}>
                {r.src}
              </a>
            </p>
            <p className="mt-4 max-w-[16rem] text-ink-2">{r.label}</p>
          </div>
        ))}
      </div>
      <p className="mt-10 max-w-3xl text-lg text-ink-2">
        And since January 2026, Original Medicare&rsquo;s WISeR model requires prior authorization or pre-payment review for selected
        services in six states
        <a href="#source-2" className="align-super font-mono text-xs text-ink-3 hover:text-ink">2</a>, including all three that Assent
        covers: epidural steroid injections, hypoglossal nerve stimulation and vertebral augmentation
        <a href="#source-3" className="align-super font-mono text-xs text-ink-3 hover:text-ink">3</a>.
      </p>
    </section>
  );
}

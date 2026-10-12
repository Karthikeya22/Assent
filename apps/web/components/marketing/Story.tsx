"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { LatticeMount } from "@/components/lattice/LatticeMount";
import { useStory } from "@/components/lattice/store";

gsap.registerPlugin(ScrollTrigger);

const STEPS = [
  {
    title: "Compile the policy",
    body: "The coverage policy (here, LCD L39240 for epidural steroid injections) becomes a typed AND/OR tree of atomic criteria. Every node keeps the exact policy sentence it came from.",
  },
  {
    title: "Read the chart",
    body: "Notes, imaging, procedures and medications are de-identified, split into passages and laid out on a timeline, so recency and duration can be reasoned about.",
  },
  {
    title: "Prove each criterion",
    body: "One evidence agent per criterion searches the chart in parallel and answers met, not met or insufficient, quoting the sentence that proves it.",
  },
  {
    title: "Verify every citation",
    body: "Each quote must exist verbatim and entail its claim. One here does not: it is rejected, and the criterion is downgraded to insufficient instead of guessed.",
  },
  {
    title: "Argue with the payer",
    body: "A payer adversary from a different model vendor attacks the packet. The advocate answers with new citations or concedes, and every concession becomes a task for a human.",
  },
];

/** Pinned scrollytelling (FRONTEND §5.1 §3): text scrolls left, the lattice stays put on the right. */
export function Story({ poster }: { poster: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState(0);
  const [gap, setGap] = useState(false);
  useEffect(() => {
    if (!root.current) return;
    const proxy = { p: 0 };
    const tween = gsap.to(proxy, {
      p: 1,
      ease: "none",
      scrollTrigger: { trigger: root.current, start: "top top", end: "bottom bottom", scrub: 0.6 },
      onUpdate: () => {
        useStory.setState({ progress: proxy.p });
        setStep(Math.min(4, Math.floor(proxy.p * 5)));
        setGap(proxy.p > 0.93);
      },
    });
    return () => {
      tween.scrollTrigger?.kill();
      tween.kill();
    };
  }, []);
  return (
    <section id="how" aria-labelledby="how-title" ref={root} className="relative mx-auto max-w-6xl px-6">
      <h2 id="how-title" className="sr-only">How Assent reads a chart</h2>
      <div className="grid gap-8 lg:grid-cols-12">
        <ol className="lg:col-span-5">
          {STEPS.map((s, i) => (
            <li key={s.title} className="flex min-h-[85vh] flex-col justify-center py-12">
              <p className="font-mono text-xs text-ink-3 tabular">0{i + 1} / 05</p>
              <h3 className={`display mt-3 text-4xl transition-colors duration-[var(--dur-2)] md:text-5xl ${step === i ? "text-ink" : "text-ink-3"}`}>
                {s.title}
              </h3>
              <p className="mt-4 max-w-md text-lg text-ink-2">{s.body}</p>
            </li>
          ))}
        </ol>
        <div className="hidden lg:col-span-7 lg:block">
          <div className="sticky top-16 flex h-[calc(100dvh-4rem)] items-center">
            <div className="relative w-full">
              <LatticeMount mode="story" poster={poster} className="aspect-[640/520] w-full" />
              <div
                role="status"
                className={`absolute right-2 bottom-4 w-64 rounded-[var(--radius-panel)] border border-rule bg-paper-raised p-3 text-sm shadow-[var(--shadow-float)] transition-[opacity,transform] duration-[var(--dur-2)] ${
                  gap ? "translate-x-0 opacity-100" : "pointer-events-none translate-x-4 opacity-0"
                }`}
              >
                <p className="font-mono text-[10px] text-gap uppercase">Gap task · clinician</p>
                <p className="mt-1 text-ink">Record a baseline pain or function score</p>
                <p className="mt-1 text-xs text-ink-2">Conceded to the payer: no objective scale before the injection.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

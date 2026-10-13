"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { CHAPTERS } from "./chapters";
import { useWorld } from "./store";
import type { Tier } from "./World";

// three.js loads after first paint and never on the server.
const World = dynamic(() => import("./World"), { ssr: false });

/** Reduced motion, no WebGL, or a low-end device: the posters carry the story instead. */
function pickTier(): Tier | null {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return null;
  const c = document.createElement("canvas");
  if (!c.getContext("webgl2")) return null;
  const nav = navigator as Navigator & { deviceMemory?: number };
  const cores = nav.hardwareConcurrency ?? 4;
  const mem = nav.deviceMemory ?? 4;
  if (cores <= 2 || mem <= 2) return null;
  return cores >= 8 && mem >= 8 && window.innerWidth >= 768 ? "high" : "mid";
}

/**
 * The fixed layer behind the landing. Static-frame-first: each chapter's poster (a still of the
 * world at rest) is always underneath; the live world fades in over it once three.js is ready.
 */
export function WorldMount() {
  const index = useWorld((s) => s.index);
  const [tier, setTier] = useState<Tier | null | undefined>(undefined);
  const [ready, setReady] = useState(false);
  const [armed, setArmed] = useState(false);
  useEffect(() => setTier(pickTier()), []);
  // Load three.js when the reader engages (or, on desktop, once the main thread is idle). The
  // poster is the same frame, so nothing is lost by waiting, and phones skip the parse/compile cost
  // until they scroll.
  useEffect(() => {
    if (!tier) return;
    const go = () => setArmed(true);
    const events = ["pointerdown", "pointermove", "wheel", "touchstart", "keydown"] as const;
    events.forEach((e) => window.addEventListener(e, go, { once: true, passive: true }));
    const unsub = useWorld.subscribe((s) => s.t > 0.01 && go());
    const desktop = window.innerWidth >= 768;
    const idle = desktop ? (window.requestIdleCallback?.(go, { timeout: 2500 }) ?? window.setTimeout(go, 1500)) : 0;
    return () => {
      events.forEach((e) => window.removeEventListener(e, go));
      unsub();
      if (desktop) (window.cancelIdleCallback ?? window.clearTimeout)(idle);
    };
  }, [tier]);
  const live = !!tier && ready;
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0">
      {CHAPTERS.map((id, i) => (
        // eslint-disable-next-line @next/next/no-img-element -- full-bleed stills, no layout to optimise
        <img
          key={id}
          src={`/world/posters/${id}.webp`}
          alt=""
          loading={i === 0 ? "eager" : "lazy"}
          fetchPriority={i === 0 ? "high" : "low"}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-[var(--dur-4)] ${!live && i === index ? "opacity-100" : "opacity-0"}`}
        />
      ))}
      {tier && armed && (
        <div className={`absolute inset-0 transition-opacity duration-[var(--dur-4)] ${ready ? "opacity-100" : "opacity-0"}`}>
          <World tier={tier} onReady={() => setReady(true)} />
        </div>
      )}
    </div>
  );
}

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
  useEffect(() => setTier(pickTier()), []);
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
      {tier && (
        <div className={`absolute inset-0 transition-opacity duration-[var(--dur-4)] ${ready ? "opacity-100" : "opacity-0"}`}>
          <World tier={tier} onReady={() => setReady(true)} />
        </div>
      )}
    </div>
  );
}

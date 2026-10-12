"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState, type ReactNode } from "react";

// three.js loads only after first paint, never on the server (FRONTEND §5.1: next/dynamic, ssr:false).
const Lattice = dynamic(() => import("./Lattice"), { ssr: false });

/** Poster first (fast LCP, reduced motion, no GPU); the live scene fades in over it when visible. */
export function LatticeMount({ mode, poster, className = "" }: { mode: "hero" | "story"; poster: ReactNode; className?: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [motion, setMotion] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setMotion(!mq.matches);
    sync();
    mq.addEventListener("change", sync);
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), { rootMargin: "120px" });
    if (box.current) io.observe(box.current);
    return () => {
      mq.removeEventListener("change", sync);
      io.disconnect();
    };
  }, []);

  return (
    <div ref={box} className={`relative ${className}`}>
      <div aria-hidden={motion && ready} className={`absolute inset-0 transition-opacity duration-[var(--dur-3)] ${motion && ready ? "opacity-0" : "opacity-100"}`}>
        {poster}
      </div>
      {motion && (
        <div className={`absolute inset-0 transition-opacity duration-[var(--dur-3)] ${ready ? "opacity-100" : "opacity-0"}`}>
          <Lattice mode={mode} active={visible} onReady={() => setReady(true)} />
        </div>
      )}
    </div>
  );
}

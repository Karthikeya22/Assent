"use client";

import Link from "next/link";
import { useWorld } from "@/components/world/store";

/** 64px nav; gains glass and a hairline once the story starts (reads the Lenis-driven store, no scroll listener). */
export function Nav() {
  const scrolled = useWorld((s) => s.t > 0.02);
  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 h-16 border-b transition-[background-color,border-color] duration-[var(--dur-2)] ${
        scrolled ? "border-rule bg-paper/80 backdrop-blur-[10px]" : "border-transparent"
      }`}
    >
      <nav aria-label="Main" className="mx-auto flex h-full max-w-7xl items-center gap-8 px-4 sm:px-6">
        <Link href="/" className="wordmark text-2xl leading-none text-ink">
          Assent
        </Link>
        <div className="hidden gap-6 text-sm text-ink-2 md:flex">
          <Link href="/#policy" className="py-2 hover:text-ink">How it works</Link>
          <Link href="/evals" className="py-2 hover:text-ink">Benchmark</Link>
          <Link href="/#packet" className="py-2 hover:text-ink">Standards</Link>
        </div>
        <div className="ml-auto flex items-center gap-4 text-sm">
          <Link href="/login" className="py-2 text-ink-2 hover:text-ink">
            Sign in
          </Link>
          <Link href="/demo" className="btn-primary !h-10 !px-4 text-sm">
            Run a live case
          </Link>
        </div>
      </nav>
    </header>
  );
}

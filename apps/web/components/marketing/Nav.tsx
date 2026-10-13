"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

/** Sticky 64px nav; gains a hairline and the site's only blur once the page scrolls. */
export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 h-16 transition-colors duration-[var(--dur-2)] ${
        scrolled ? "border-b border-rule bg-paper/85 backdrop-blur-[8px]" : "border-b border-transparent"
      }`}
    >
      <nav aria-label="Main" className="mx-auto flex h-full max-w-6xl items-center gap-8 px-6">
        <Link href="/" className="wordmark text-2xl leading-none text-ink">
          Assent
        </Link>
        <div className="hidden gap-6 text-sm text-ink-2 md:flex">
          <Link href="/#how" className="hover:text-ink">How it works</Link>
          <Link href="/evals" className="hover:text-ink">Evals</Link>
          <Link href="/#standards" className="hover:text-ink">Standards</Link>
        </div>
        <div className="ml-auto flex items-center gap-3 text-sm">
          <Link href="/demo" className="inline-flex h-9 items-center rounded-[var(--radius-control)] border border-rule px-3 text-ink hover:border-ink-3">
            Live demo
          </Link>
          <Link href="/login" className="text-ink-2 hover:text-ink">
            Sign in
          </Link>
        </div>
      </nav>
    </header>
  );
}

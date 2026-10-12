import Link from "next/link";

export function Closing() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-32 text-center md:py-48">
      <p className="display text-[clamp(2.5rem,6vw,5rem)] leading-tight">See it work on a real chart.</p>
      <Link href="/demo" className="mt-10 inline-flex h-12 items-center rounded-[var(--radius-control)] bg-signal px-6 font-medium text-paper">
        Run a live case
      </Link>
      <p className="mt-4 text-sm text-ink-3">Synthetic patients only. No PHI.</p>
    </section>
  );
}

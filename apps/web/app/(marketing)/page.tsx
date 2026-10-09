import Link from "next/link";

// Placeholder until Phase 7 builds the landing page (FRONTEND §5.1).
export default function Home() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-5xl flex-col justify-center px-6">
      <p className="font-mono text-xs tracking-wide text-ink-3">WISeR · CMS-0057-F · 2026</p>
      <h1 className="display mt-6 text-[clamp(3rem,9vw,6rem)] leading-[0.95]">
        Prior authorization,
        <br />
        <em>argued with evidence.</em>
      </h1>
      <p className="mt-6 max-w-xl text-lg text-ink-2">
        Assent reads the chart, proves every Medicare coverage criterion with a cited sentence, and
        stress-tests the packet against a simulated payer before you hit submit.
      </p>
      <div className="mt-10">
        <Link
          href="/login"
          className="inline-flex h-11 items-center rounded-[var(--radius-control)] bg-signal px-5 font-medium text-paper"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}

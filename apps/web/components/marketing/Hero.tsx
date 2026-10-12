import Link from "next/link";
import { LatticeMount } from "@/components/lattice/LatticeMount";
import { LatticePoster } from "@/components/lattice/LatticePoster";

export function Hero() {
  return (
    <section className="relative mx-auto grid min-h-dvh max-w-6xl items-center gap-8 px-6 pt-24 pb-12 lg:grid-cols-12">
      <div className="lg:col-span-5">
        <p className="font-mono text-xs tracking-wide text-ink-3">WISeR · CMS-0057-F · 2026</p>
        <h1 className="display mt-6 text-[clamp(3rem,6vw,4.75rem)] leading-[0.95]">
          Prior authorization,
          <br />
          <em>argued with evidence.</em>
        </h1>
        <p className="mt-6 max-w-md text-lg text-ink-2 md:text-xl">
          Assent reads the chart, proves every Medicare coverage criterion with a cited sentence, and stress-tests the packet
          against a simulated payer before you hit submit.
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-6">
          <Link href="/demo" className="inline-flex h-11 items-center rounded-[var(--radius-control)] bg-signal px-5 font-medium text-paper">
            Run a live case
          </Link>
          <Link href="/evals" className="text-ink-2 underline-offset-4 hover:text-ink hover:underline">
            See the benchmark →
          </Link>
        </div>
      </div>
      <LatticeMount
        mode="hero"
        className="aspect-[640/520] w-full lg:col-span-7"
        poster={<LatticePoster title="Chart pages on the left; the L39240 coverage criteria as a graph on the right, most criteria proven, one insufficient." />}
      />
    </section>
  );
}

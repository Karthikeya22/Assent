import Link from "next/link";
import run from "@/content/agents-run.json";
import { Body, Chapter, H2, Ref } from "@/components/landing/Chapter";
import { WorldMount } from "@/components/world/WorldMount";

/**
 * The landing: eleven scroll chapters over one continuous 3D world (docs/design/storyboard.md).
 * Every resting frame is the finished frame: all copy and numbers are in the HTML; the world and
 * its posters only illustrate it.
 */
const PROBLEM = [
  { value: "40", label: "prior authorizations per physician, per week" },
  { value: "13", label: "hours of physician and staff time, every week" },
  { value: "95%", label: "of physicians say it delays access to necessary care" },
];

const STEPS = [
  { title: "Sign the order.", body: "In the EHR, a CDS Hooks card tells the clinician prior auth is required and what is still missing." },
  { title: "Review the case.", body: "The coordinator sees every criterion, its quote and its source, and closes the gaps Assent found." },
  { title: "Approve and send.", body: "One approval builds the packet. Status, denials and appeals come back to the same worklist." },
];

const PROOF = [
  { value: "16 / 18", label: "decisions correct" },
  { value: "0", label: "unproven cases marked ready" },
  { value: "0%", label: "unsupported claims" },
  { value: "$0.079", label: "per case" },
];

export default function Home() {
  const objection = run.objections.find((o) => o.status === "rebutted") ?? run.objections[0];
  return (
    <main id="main">
      <WorldMount />
      <Chapter id="hero" side="left" label="Introduction" bare wide tall={false}>
        <p className="font-mono text-xs tracking-wide text-ink-3">WISeR · CMS-0057-F · 2026</p>
        <h1 className="display mt-5 text-[clamp(2.6rem,4.7vw,4.25rem)] leading-[1.04]">
          Prior authorization,
          <br />
          <span className="text-signal">argued with evidence.</span>
        </h1>
        <p className="mt-6 max-w-[26rem] text-lg leading-relaxed text-ink-2">
          Assent proves every Medicare coverage criterion with a cited sentence from the chart, before the payer sees it.
        </p>
        <div className="mt-9 flex flex-wrap items-center gap-6">
          <Link href="/demo" className="btn-primary">
            Run a live case
          </Link>
          <Link href="/evals" className="link-quiet">
            See the benchmark
          </Link>
        </div>
      </Chapter>

      <Chapter id="problem" side="center" label="The problem">
        <dl className="grid gap-6 text-left sm:grid-cols-3 md:gap-4">
          {PROBLEM.map((p) => (
            <div key={p.label}>
              <dt className="sr-only">{p.label}</dt>
              <dd className="display text-[clamp(2.5rem,5vw,3.5rem)] leading-none tabular">
                {p.value}
                <Ref n={1} />
              </dd>
              <dd className="mt-2 text-sm leading-snug text-ink-2">{p.label}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-7 border-t border-rule pt-5 text-left text-[0.9375rem] leading-relaxed text-ink-2">
          And since January 2026, Original Medicare&rsquo;s WISeR model requires prior authorization or pre-payment review in six
          states
          <Ref n={2} />, including all three services Assent covers
          <Ref n={3} />.
        </p>
      </Chapter>

      <Chapter id="policy" side="left" label="Compile the policy">
        <H2>Compile the policy.</H2>
        <Body>
          The coverage policy (LCD L39240 for epidural steroid injections) becomes a typed AND/OR tree of atomic criteria. Every
          node keeps the exact sentence it came from.
        </Body>
      </Chapter>

      <Chapter id="chart" side="right" label="Read the chart">
        <H2>Read the chart.</H2>
        <Body>
          Notes, imaging, procedures and medications are de-identified, split into passages and laid on a timeline, so recency and
          duration can be reasoned about.
        </Body>
      </Chapter>

      <Chapter id="prove" side="left" label="Prove each criterion">
        <H2>Prove each criterion.</H2>
        <Body>
          One evidence agent per criterion searches the chart in parallel and answers met, not met or insufficient, quoting the
          sentence that proves it.
        </Body>
      </Chapter>

      <Chapter id="verify" side="right" label="Verify every citation">
        <H2>Verify every citation.</H2>
        <Body>
          Each quote must exist verbatim and support its claim. This one does not. It is rejected, and the criterion drops to
          insufficient instead of being guessed.
        </Body>
      </Chapter>

      <Chapter id="argue" side="left" label="Argue with the payer">
        <H2>Argue with the payer.</H2>
        <Body>
          A payer adversary from a different model vendor attacks the packet. The advocate answers with new citations or concedes,
          and every concession becomes a task for a human.
        </Body>
        <figure className="mt-6 space-y-3 border-t border-rule pt-5 text-[0.9375rem] leading-relaxed">
          <blockquote className="line-clamp-3 text-adversary">
            <span className="mr-1.5 font-mono text-xs tracking-wide">PAYER</span>
            {objection.text}
          </blockquote>
          <blockquote className="line-clamp-3 text-ink">
            <span className="mr-1.5 font-mono text-xs tracking-wide text-signal">ADVOCATE</span>
            {objection.rebuttal}
          </blockquote>
          <figcaption className="text-xs text-ink-3">
            Recorded review of benchmark case CPT {run.case.cpt}. Objection {objection.status}.
          </figcaption>
        </figure>
      </Chapter>

      <Chapter id="packet" side="right" label="Submit a packet that holds">
        <H2>Submit a packet that holds.</H2>
        <Body>
          Assent builds a Da Vinci PAS bundle on HL7 FHIR R4 and a cited letter. A human approves. If the payer denies, it searches
          the chart again and drafts the appeal.
        </Body>
        <p className="mt-4 text-sm text-ink-3">
          Payers must answer within 72 hours (expedited) or 7 days and expose a FHIR Prior Authorization API by January 2027
          <Ref n={4} />.
        </p>
      </Chapter>

      <Chapter id="use" side="center" label="How you use it" bare>
        <div className="glass p-6 text-left md:p-8">
          <H2>How you use it.</H2>
          <ol className="mt-6 grid gap-5 md:grid-cols-3 md:gap-6">
            {STEPS.map((s) => (
              <li key={s.title}>
                <p className="font-medium text-ink">{s.title}</p>
                <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-ink-2">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </Chapter>

      <Chapter id="proof" side="left" label="Benchmark results">
        <H2>Measured, not claimed.</H2>
        <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-5">
          {PROOF.map((p) => (
            <div key={p.label}>
              <dt className="sr-only">{p.label}</dt>
              <dd className="display text-[2rem] leading-none tabular">{p.value}</dd>
              <dd className="mt-1.5 text-sm text-ink-2">{p.label}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-6 text-sm text-ink-3">On a locked test split of 18 synthetic cases across three services.</p>
        <Link href="/evals" className="link-quiet mt-4 inline-block">
          See the benchmark
        </Link>
      </Chapter>

      <Chapter id="close" side="center" label="Try it" bare top tall={false}>
        <div className="flex flex-col items-center text-center">
          <p className="display text-[clamp(2.25rem,5vw,4.25rem)] leading-[1.05]">See it work on a real chart.</p>
          <Link href="/demo" className="btn-primary mt-9">
            Run a live case
          </Link>
          <p className="mt-4 text-sm text-ink-3">Synthetic patients only. No PHI.</p>
        </div>
      </Chapter>
    </main>
  );
}

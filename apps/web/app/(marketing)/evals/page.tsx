import type { Metadata } from "next";
import latest from "@/public/evals/latest.json";

export const metadata: Metadata = { title: "Benchmark", description: "How well Assent works, including where it fails." };

type Fam = { family: string; n_cases: number; criterion_macro_f1: number; case_accuracy: number; citation_precision: number | null; unsupported_claim_rate: number | null; latency_p50_s: number; cost_per_case_usd: number; false_ready: number; false_not_ready: number };
type Cmp = Omit<Fam, "family"> & { system: string };

const pct = (x: number | null | undefined, d = 0) => (x == null ? "—" : `${(x * 100).toFixed(d)}%`);
const NAME: Record<string, string> = { esi: "Epidural steroid injection", hgns: "Hypoglossal nerve stimulation", pva: "Vertebral augmentation", all: "All three" };

function FamilyTable({ rows, caption }: { rows: Fam[]; caption: string }) {
  return (
    <div className="mt-6 overflow-x-auto">
      <table className="w-full min-w-[680px] text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-rule text-left text-xs text-ink-3">
          <tr>
            <th className="py-2 pr-4 font-normal">Service</th>
            <th className="py-2 pr-4 text-right font-normal">Cases</th>
            <th className="py-2 pr-4 text-right font-normal">Decisions correct</th>
            <th className="py-2 pr-4 text-right font-normal">Wrongly ready</th>
            <th className="py-2 pr-4 text-right font-normal">Wrongly held back</th>
            <th className="py-2 pr-4 text-right font-normal">Criterion F1</th>
            <th className="py-2 pr-4 text-right font-normal">Citation precision</th>
            <th className="py-2 text-right font-normal">Cost / case</th>
          </tr>
        </thead>
        <tbody className="font-mono tabular">
          {rows.map((r) => (
            <tr key={r.family} className={`border-b border-rule ${r.family === "all" ? "text-ink" : "text-ink-2"}`}>
              <td className="py-2.5 pr-4 font-sans">{NAME[r.family] ?? r.family}</td>
              <td className="py-2.5 pr-4 text-right">{r.n_cases}</td>
              <td className="py-2.5 pr-4 text-right">{pct(r.case_accuracy)}</td>
              <td className={`py-2.5 pr-4 text-right ${r.false_ready ? "text-fail" : "text-signal"}`}>{r.false_ready}</td>
              <td className="py-2.5 pr-4 text-right">{r.false_not_ready}</td>
              <td className="py-2.5 pr-4 text-right">{r.criterion_macro_f1.toFixed(2)}</td>
              <td className="py-2.5 pr-4 text-right">{pct(r.citation_precision)}</td>
              <td className="py-2.5 text-right">{r.family === "esi" && caption.includes("dev") ? "$0.093" : `$${r.cost_per_case_usd.toFixed(3)}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const H2 = "display mt-24 text-3xl md:text-4xl";

export default function EvalsPage() {
  const test = latest.test.per_family as Fam[];
  const dev = latest.dev.per_family as Fam[];
  const cmp = latest.dev.comparison as Cmp[];
  const adv = latest.dev.adversary;
  const inj = latest.dev.injection;
  const risk = latest.dev.risk_model;
  const all = test.find((r) => r.family === "all")!;
  const [assent, lc] = cmp;
  return (
    <main className="mx-auto max-w-4xl px-6 pt-32 pb-24">
      <p className="font-mono text-xs tracking-wide text-ink-3">BENCHMARK · OCTOBER 2026</p>
      <h1 className="display mt-4 text-[clamp(2.75rem,6vw,4.5rem)] leading-[1]">How well does it work?</h1>
      <p className="mt-6 text-lg text-ink-2">
        On the locked test split, Assent decided <strong className="text-ink">{pct(all.case_accuracy)}</strong> of {all.n_cases} cases correctly
        and marked <strong className="text-ink">{all.false_ready}</strong> unproven cases ready to submit. Every mistake it made held a case back for
        a human instead of sending a weak one. Below are the method, the numbers, and the failures.
      </p>

      <h2 className={H2}>Method</h2>
      <div className="mt-4 space-y-4 text-ink-2">
        <p>
          150 synthetic Medicare cases, 50 per service family, built on Synthea patients. Each case starts as a fact sheet; an LLM then
          writes 3 to 5 clinical notes from it, and every fact sentence must appear verbatim in its note, so the gold labels are correct by
          construction. Difficulty mix: 40% clean, 30% buried in abbreviations, 15% missing one criterion, 10% contradictory notes, 5% prompt
          injection. The gold criteria come from the real Medicare LCDs (L39240, L38307, L34228), quoted verbatim.
        </p>
        <p>
          Models: gpt-4.1 evidence agents, a gpt-4.1-mini citation judge, a Gemini payer adversary, and local embedding, reranking and NLI
          models on a CPU laptop. The test split was locked until the final run, which was then run once.
        </p>
      </div>

      <h2 className={H2}>Locked test split</h2>
      <p className="mt-3 text-sm text-ink-3">6 cases per family, trimmed for cost. Small n: one case moves a family by 17 points.</p>
      <FamilyTable rows={test} caption="test split results" />

      <h2 className={H2}>Development split</h2>
      <p className="mt-3 text-sm text-ink-3">
        ESI 34 cases; HGNS and PVA 12 each (after two fixes, below). ESI cost is from the original run; later rows replayed recorded calls.
      </p>
      <FamilyTable rows={dev} caption="dev split results" />

      <h2 className={H2}>Against a long-context prompt</h2>
      <p className="mt-4 text-ink-2">
        The same {assent.n_cases} cases, the same model, the whole chart and all criteria in one prompt. It decided all {lc.n_cases} cases correctly,
        against Assent&rsquo;s {Math.round(assent.case_accuracy * assent.n_cases)}. But{" "}
        <strong className="text-ink">{pct(lc.unsupported_claim_rate)} of its met or not-met answers had no valid citation</strong> (Assent:{" "}
        {pct(assent.unsupported_claim_rate)}), and its criterion F1 was {lc.criterion_macro_f1.toFixed(2)} against {assent.criterion_macro_f1.toFixed(2)}.
        It is often right without being able to show why. A payer, or an auditor, can&rsquo;t accept that.
      </p>

      <h2 className={H2}>Robustness</h2>
      <dl className="mt-6 grid gap-8 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-ink-3">Payer adversary, seeded defects</dt>
          <dd className="mt-1 text-ink-2">
            <span className="display text-3xl text-ink tabular">{pct(adv.catch_rate)}</span> of {adv.n_seeded} packets with one planted weak, misattributed
            or missing citation were caught. It is over-eager, though: it raises {adv.objections_per_clean_packet} objections on a clean packet.
          </dd>
        </div>
        <div>
          <dt className="text-sm text-ink-3">Prompt injection</dt>
          <dd className="mt-1 text-ink-2">
            <span className="display text-3xl text-ink tabular">{inj.decision_flips_to_ready}</span> of {inj.n_cases} attacked not-ready cases flipped to ready,
            including {inj.attacks_missed_by_screen} attacks the keyword screen did not catch.
          </dd>
        </div>
        <div>
          <dt className="text-sm text-ink-3">Denial-risk model (logistic, 5-fold CV)</dt>
          <dd className="mt-1 text-ink-2">
            Brier {risk.cv.brier.toFixed(3)}, AUC {risk.cv.auc.toFixed(2)}, against the hand-set prior&rsquo;s {risk.prior_same_cases.brier.toFixed(3)} and{" "}
            {risk.prior_same_cases.auc.toFixed(2)} on the same {risk.n} cases. Fitted, but on too few cases to trust closely.
          </dd>
        </div>
      </dl>

      <h2 className={H2}>Where it fails</h2>
      <ol className="mt-6 space-y-8 text-ink-2">
        <li>
          <p className="text-ink">1. It once called two unproven PVA cases ready.</p>
          <p className="mt-1">
            In two cases the contraindication check was deliberately undocumented. The model cited &ldquo;Back pain began 07/02/2026 after bending to
            pick up a grandchild&rdquo; as proof of no contraindication, and the verifier accepted it because the sentence was real and the claim
            loosely followed. Fix: the agent is told that a sentence about something else is not evidence that no contraindication exists.
            Wrongly-ready PVA cases went from 2 to 0.
          </p>
        </li>
        <li>
          <p className="text-ink">2. It misses sleep-study facts.</p>
          <p className="mt-1">
            Hypoglossal nerve stimulation is the weakest family: sleep-study dates, AHI and central-apnea percentages often come back
            &ldquo;insufficient&rdquo; even though the polysomnography report states them. Search hints written for spine cases were part of it.
            Family-specific hints won back one decision, but criterion-level misses did not drop.
          </p>
        </li>
        <li>
          <p className="text-ink">3. It prefers &ldquo;insufficient&rdquo; to being wrong.</p>
          <p className="mt-1">
            Across every split, every wrong decision held a ready case back. The verifier downgrades a met verdict whenever its quote does
            not entail the claim, so terse notes (&ldquo;HEP daily, compliant.&rdquo;) cost points. This is the intended trade-off, but it
            means more human review than a perfect system would need.
          </p>
        </li>
      </ol>

      <h2 className={H2}>Not measured yet</h2>
      <p className="mt-4 text-ink-2">
        To keep API spend low, these were cut: the full 150-case run (HGNS and PVA ran 12 dev and 6 test cases each), the naive-RAG
        baseline, and the reranker, hybrid-search and verifier ablations. The harness for all of them is in the repository.
      </p>
    </main>
  );
}

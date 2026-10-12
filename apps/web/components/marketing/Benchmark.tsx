import Link from "next/link";
import latest from "@/public/evals/latest.json";

type Row = { system?: string; family?: string; criterion_macro_f1: number; citation_precision: number | null; unsupported_claim_rate: number | null; cost_per_case_usd: number; n_cases: number };

const pct = (x: number | null | undefined) => (x == null ? "n/a" : `${Math.round(x * 100)}%`);

/** Benchmark preview from the committed eval table: same cases, Assent vs a long-context prompt. */
export function Benchmark() {
  const cmp = (latest.dev?.comparison ?? []) as Row[];
  const test = (latest.test?.per_family ?? []) as Row[];
  const all = test.find((r) => r.family === "all");
  const metrics: { key: keyof Row; label: string }[] = [
    { key: "criterion_macro_f1", label: "Criterion F1" },
    { key: "citation_precision", label: "Citation precision" },
    { key: "unsupported_claim_rate", label: "Unsupported claims (lower is better)" },
  ];
  return (
    <section aria-labelledby="bench" className="mx-auto max-w-6xl px-6 py-24 md:py-40">
      <h2 id="bench" className="display text-4xl md:text-5xl">Measured, not claimed.</h2>
      {all && (
        <p className="mt-4 max-w-3xl text-lg text-ink-2">
          On the locked test split ({all.n_cases} cases across three service families), Assent decided {pct((all as unknown as { case_accuracy: number }).case_accuracy)} of
          cases correctly, never marked an unproven case ready, and made {pct(all.unsupported_claim_rate)} unsupported claims, at $
          {all.cost_per_case_usd.toFixed(3)} per case.
        </p>
      )}
      {cmp.length > 0 && (
        <div className="mt-12 space-y-8">
          <p className="font-mono text-xs text-ink-3">Same {cmp[0].n_cases} dev cases · gpt-4.1 for both</p>
          {metrics.map((m) => (
            <div key={m.key}>
              <p className="text-sm text-ink-2">{m.label}</p>
              <div className="mt-2 space-y-1.5">
                {cmp.map((r) => {
                  const v = (r[m.key] as number | null) ?? 0;
                  const assent = r.system?.startsWith("assent");
                  return (
                    <div key={r.system} className="grid grid-cols-[9rem_1fr_3.5rem] items-center gap-3 text-sm">
                      <span className={assent ? "text-ink" : "text-ink-3"}>{assent ? "Assent" : "Long-context prompt"}</span>
                      <span className="h-2 overflow-hidden rounded-full bg-rule" aria-hidden="true">
                        <span className={`block h-full ${assent ? "bg-signal" : "bg-ink-3"}`} style={{ width: `${Math.max(1, v * 100)}%` }} />
                      </span>
                      <span className="text-right font-mono tabular">{pct(r[m.key] as number | null)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
      <Link href="/evals" className="mt-10 inline-block text-ink-2 underline-offset-4 hover:text-ink hover:underline">
        Full report, including where it fails →
      </Link>
    </section>
  );
}

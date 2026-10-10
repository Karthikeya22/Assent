import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api/client";

export const metadata: Metadata = { title: "Worklist" };

const SERVICE: Record<string, string> = { esi: "Epidural steroid injection", hgns: "Hypoglossal nerve stim.", pva: "Vertebral augmentation" };
const STATUS: Record<string, { label: string; dot: string }> = {
  new: { label: "New", dot: "bg-ink-3" },
  running: { label: "Running", dot: "bg-signal animate-pulse motion-reduce:animate-none" },
  needs_review: { label: "Needs review", dot: "bg-gap" },
  ready: { label: "Ready", dot: "bg-signal" },
  submitted: { label: "Submitted", dot: "bg-ink-2" },
  approved: { label: "Approved", dot: "bg-signal" },
  denied: { label: "Denied", dot: "bg-fail" },
  appealed: { label: "Appealed", dot: "bg-gap" },
};

export default async function WorklistPage() {
  const { data, error } = await (await api()).GET("/api/v1/cases", { params: { query: { limit: 100 } } });

  return (
    <div className="px-6 py-5">
      <div className="flex items-baseline justify-between">
        <h1 className="display text-xl">Worklist</h1>
        <span className="font-mono text-xs text-ink-3 tabular">{data ? `${data.items.length} cases` : ""}</span>
      </div>

      {error ? (
        <p role="alert" className="mt-8 text-fail">
          Couldn’t load cases. Is the API running?
        </p>
      ) : data && data.items.length === 0 ? (
        <div className="mt-16 max-w-md">
          <p className="display text-2xl leading-tight">No cases yet.</p>
          <p className="mt-3 text-ink-2">
            Load the benchmark cases with <code className="font-mono text-sm">python -m assent_evals.bench</code>, or
            create one from an order.
          </p>
        </div>
      ) : (
        <table className="mt-4 w-full border-collapse text-left">
          <thead className="text-xs text-ink-3">
            <tr className="border-b border-rule">
              <th className="h-8 pr-4 font-normal">Patient</th>
              <th className="pr-4 font-normal">Service</th>
              <th className="pr-4 font-normal">Codes</th>
              <th className="w-[180px] pr-4 font-normal">Readiness</th>
              <th className="pr-4 font-normal">Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((c) => {
              const st = STATUS[c.status] ?? STATUS.new;
              const r = c.readiness_score;
              return (
                <tr key={c.id} className="group h-10 border-b border-rule hover:bg-paper-raised">
                  <td className="pr-4">
                    <Link href={`/app/cases/${c.id}`} className="font-medium text-ink group-hover:text-signal">
                      {c.patient_name || "Unnamed patient"}
                    </Link>
                  </td>
                  <td className="pr-4 text-ink-2">{SERVICE[c.service_family] ?? c.service_family}</td>
                  <td className="pr-4 font-mono text-xs text-ink-2">
                    CPT {c.cpt_codes.join(", ")} · {c.icd10_codes.join(", ")}
                  </td>
                  <td className="pr-4">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-24 rounded-full bg-rule" aria-hidden="true">
                        {r != null && (
                          <div className={`h-full rounded-full ${r >= 1 ? "bg-signal" : "bg-gap"}`} style={{ width: `${Math.round(r * 100)}%` }} />
                        )}
                      </div>
                      <span className="font-mono text-xs text-ink-2 tabular">{r == null ? "—" : `${Math.round(r * 100)}%`}</span>
                    </div>
                  </td>
                  <td className="pr-4 text-sm">
                    <span className="inline-flex items-center gap-1.5">
                      <span className={`size-1.5 rounded-full ${st.dot}`} aria-hidden="true" />
                      {st.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

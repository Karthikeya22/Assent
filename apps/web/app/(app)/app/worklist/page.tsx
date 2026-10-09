import type { Metadata } from "next";
import { api } from "@/lib/api/client";

export const metadata: Metadata = { title: "Worklist" };

export default async function WorklistPage() {
  const { data, error } = await (await api()).GET("/api/v1/cases", {
    params: { query: { limit: 50 } },
  });

  return (
    <div className="px-6 py-5">
      <div className="flex items-baseline justify-between">
        <h1 className="display text-xl">Worklist</h1>
        <span className="font-mono text-xs text-ink-3 tabular">
          {data ? `${data.items.length} cases` : ""}
        </span>
      </div>

      {error ? (
        <p role="alert" className="mt-8 text-fail">
          Couldn’t load cases. Is the API running on {process.env.API_URL ?? "localhost:8000"}?
        </p>
      ) : data && data.items.length === 0 ? (
        <div className="mt-16 max-w-md">
          <p className="display text-2xl leading-tight">No cases yet.</p>
          <p className="mt-3 text-ink-2">
            New prior authorization requests land here with their SLA clocks. Case creation arrives
            with the evidence agent in Phase 2.
          </p>
        </div>
      ) : (
        // Dense virtualized table comes with Phase 3; a plain list keeps Phase 0 honest.
        <ul className="mt-6 divide-y divide-rule border-y border-rule">
          {data?.items.map((c) => (
            <li key={c.id} className="flex h-10 items-center gap-4 font-mono text-sm">
              <span className="text-ink-3">{c.id.slice(0, 8)}</span>
              <span>{c.service_family}</span>
              <span className="text-ink-2">{c.cpt_codes.join(", ")}</span>
              <span className="ml-auto text-ink-2">{c.status}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

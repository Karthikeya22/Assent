import type { Metadata } from "next";
import Link from "next/link";
import { MonoChip } from "@/components/ui/MonoChip";
import { api } from "@/lib/api/client";

export const metadata: Metadata = { title: "Policies" };

const FAMILY: Record<string, string> = {
  esi: "Epidural steroid injection",
  hgns: "Hypoglossal nerve stimulation",
  pva: "Vertebral augmentation",
};

export default async function PoliciesPage() {
  const { data, error } = await (await api()).GET("/api/v1/policies");

  return (
    <div className="px-6 py-5">
      <h1 className="display text-xl">Policies</h1>
      <p className="mt-1 text-ink-2">
        Medicare LCDs compiled into criteria trees. Each tree is human-approved before cases use it.
      </p>
      {error ? (
        <p role="alert" className="mt-8 text-fail">
          Couldn’t load policies.
        </p>
      ) : (
        <table className="mt-6 w-full border-collapse text-left">
          <thead className="text-xs text-ink-3">
            <tr className="border-b border-rule">
              <th className="py-2 pr-4 font-normal">Policy</th>
              <th className="py-2 pr-4 font-normal">Service</th>
              <th className="py-2 pr-4 font-normal">Contractor</th>
              <th className="py-2 pr-4 font-normal">Version</th>
              <th className="py-2 font-normal">Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((p) => (
              <tr key={p.id} className="h-10 border-b border-rule">
                <td className="pr-4">
                  {p.latest_version ? (
                    <Link
                      href={`/app/policies/${p.latest_version.id}`}
                      className="inline-flex items-center gap-2 hover:text-signal"
                    >
                      <MonoChip>{p.source_id}</MonoChip>
                      <span>{p.title}</span>
                    </Link>
                  ) : (
                    <MonoChip>{p.source_id}</MonoChip>
                  )}
                </td>
                <td className="pr-4 text-ink-2">{FAMILY[p.service_family] ?? p.service_family}</td>
                <td className="pr-4 text-ink-2">{p.payer.replace(/^Medicare \(|\)$/g, "")}</td>
                <td className="pr-4 font-mono text-sm tabular">v{p.latest_version?.version}</td>
                <td className="text-sm">
                  {p.latest_version?.status === "approved" ? (
                    <span className="text-signal">✓ Approved</span>
                  ) : (
                    <span className="text-gap">○ {p.latest_version?.status ?? "none"}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

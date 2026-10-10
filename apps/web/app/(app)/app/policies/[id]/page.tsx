import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PolicyWorkspace } from "@/components/policy/PolicyWorkspace";
import { MonoChip } from "@/components/ui/MonoChip";
import { api } from "@/lib/api/client";

export const metadata: Metadata = { title: "Policy" };

export default async function PolicyVersionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { data, response } = await (await api()).GET("/api/v1/policy-versions/{version_id}", {
    params: { path: { version_id: id } },
  });
  if (response.status === 404 || response.status === 422) notFound();
  if (!data) throw new Error(`policy version ${id}: ${response.status}`);

  // Stored as a UTC calendar date: format in UTC or US time zones show the previous day.
  const effective = data.effective_date
    ? new Date(data.effective_date).toLocaleDateString("en-US", { timeZone: "UTC" })
    : null;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="px-6 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <MonoChip>{data.policy.source_id}</MonoChip>
          <MonoChip>v{data.version}</MonoChip>
          {data.status === "approved" ? (
            <span className="text-sm text-signal">✓ Approved</span>
          ) : (
            <span className="text-sm text-gap">○ {data.status}</span>
          )}
          {effective && <span className="font-mono text-xs text-ink-3">effective {effective}</span>}
        </div>
        <h1 className="display mt-2 text-xl">{data.policy.title}</h1>
        <p className="mt-0.5 text-sm text-ink-2">
          {data.policy.payer} ·{" "}
          <a href={data.source_url} target="_blank" rel="noreferrer" className="underline decoration-rule underline-offset-4 hover:text-ink">
            CMS Medicare Coverage Database
          </a>
        </p>
      </header>
      {data.criteria ? (
        <PolicyWorkspace text={data.raw_text} root={data.criteria} />
      ) : (
        <p className="px-6 text-ink-2">This version has not been compiled yet.</p>
      )}
    </div>
  );
}

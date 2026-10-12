import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CaseWorkspace } from "@/components/case/CaseWorkspace";
import { api } from "@/lib/api/client";

export const metadata: Metadata = { title: "Case" };

export default async function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const client = await api();
  const { data: detail, response } = await client.GET("/api/v1/cases/{case_id}", {
    params: { path: { case_id: id } },
  });
  if (response.status === 404 || response.status === 422) notFound();
  if (!detail) throw new Error(`case ${id}: ${response.status}`);

  // The case's resolved policy, or the approved one for its service family before the first run.
  let versionId = detail.policy?.version_id;
  if (!versionId) {
    const { data: pols } = await client.GET("/api/v1/policies");
    // Same rule as the worker's policy_resolver (approved_version_for): highest source id wins.
    versionId = pols
      ?.filter((p) => p.service_family === detail.service_family && p.latest_version?.status === "approved")
      .sort((a, b) => b.source_id.localeCompare(a.source_id))[0]?.latest_version?.id;
  }
  if (!versionId) throw new Error(`no approved policy for ${detail.service_family}`);

  const finished = detail.latest_run?.status === "finished" ? detail.latest_run.id : null;
  const run = { params: { path: { run_id: finished ?? "" } } };
  const [pv, timeline, verdicts, objections, gaps, runDetail] = await Promise.all([
    client.GET("/api/v1/policy-versions/{version_id}", { params: { path: { version_id: versionId } } }),
    client.GET("/api/v1/cases/{case_id}/timeline", { params: { path: { case_id: id } } }),
    finished ? client.GET("/api/v1/runs/{run_id}/verdicts", run) : Promise.resolve({ data: [] }),
    finished ? client.GET("/api/v1/runs/{run_id}/objections", run) : Promise.resolve({ data: [] }),
    client.GET("/api/v1/cases/{case_id}/gaps", { params: { path: { case_id: id } } }),
    finished ? client.GET("/api/v1/runs/{run_id}", run) : Promise.resolve({ data: null }),
  ]);
  if (!pv.data?.criteria) throw new Error("policy has no criteria tree");
  const reviewStep = runDetail.data?.steps.find((s) => s.node === "review")?.payload as
    | { risk_factors?: string[]; error?: string | null }
    | undefined;

  return (
    <CaseWorkspace
      key={detail.latest_run?.id ?? "none"}
      detail={detail}
      root={pv.data.criteria}
      policy={{ sourceId: pv.data.policy.source_id, version: pv.data.version, title: pv.data.policy.title }}
      chunks={timeline.data ?? []}
      verdicts={verdicts.data ?? []}
      review={{
        objections: objections.data ?? [],
        gaps: (gaps.data ?? []).filter((g) => g.status === "open"),
        riskFactors: reviewStep?.risk_factors ?? [],
        error: reviewStep?.error ?? null,
      }}
    />
  );
}

"use server";

import { api } from "@/lib/api/client";

export async function startRun(caseId: string): Promise<{ runId?: string; error?: string }> {
  const { data, response } = await (await api()).POST("/api/v1/cases/{case_id}/runs", {
    params: { path: { case_id: caseId } },
    body: { trigger: "manual" },
  });
  if (data) return { runId: data.run_id };
  if (response.status === 409) return { error: "A run is already in progress for this case." };
  return { error: `Couldn’t start the run (${response.status}).` };
}

"use server";

import { revalidatePath } from "next/cache";
import { api } from "@/lib/api/client";

type Result = { error?: string };

async function detail(r: Response): Promise<string> {
  try {
    const body = await r.clone().json();
    return typeof body?.detail === "string" ? body.detail : `request failed (${r.status})`;
  } catch {
    return `request failed (${r.status})`;
  }
}

export async function startRun(caseId: string): Promise<{ runId?: string; error?: string }> {
  const { data, response } = await (await api()).POST("/api/v1/cases/{case_id}/runs", {
    params: { path: { case_id: caseId } },
    body: { trigger: "manual" },
  });
  if (data) return { runId: data.run_id };
  if (response.status === 409) return { error: "A run is already in progress for this case." };
  return { error: `Couldn’t start the run (${response.status}).` };
}

export async function decide(
  caseId: string,
  runId: string,
  decision: "approve" | "reject",
  acknowledgeHigh = false,
): Promise<Result & { needsAck?: boolean }> {
  const { data, response } = await (await api()).POST("/api/v1/runs/{run_id}/resume", {
    params: { path: { run_id: runId } },
    body: { decision, acknowledge_high: acknowledgeHigh },
  });
  if (data) {
    revalidatePath(`/app/cases/${caseId}`);
    return {};
  }
  const msg = await detail(response);
  return { error: msg, needsAck: response.status === 409 && msg.includes("high-severity") };
}

export async function overrideVerdict(
  caseId: string,
  verdictId: string,
  verdict: "met" | "not_met" | "insufficient",
  reason: string,
): Promise<Result> {
  const { response } = await (await api()).PATCH("/api/v1/verdicts/{verdict_id}", {
    params: { path: { verdict_id: verdictId } },
    body: { verdict, reason },
  });
  if (response.ok) {
    revalidatePath(`/app/cases/${caseId}`);
    return {};
  }
  return { error: response.status === 422 ? "Give a reason for the override." : await detail(response) };
}

export async function setGapStatus(caseId: string, gapId: string, status: "open" | "done" | "dismissed"): Promise<Result> {
  const { response } = await (await api()).PATCH("/api/v1/gaps/{gap_id}", {
    params: { path: { gap_id: gapId } },
    body: { status },
  });
  if (response.ok) revalidatePath(`/app/cases/${caseId}`);
  return response.ok ? {} : { error: await detail(response) };
}

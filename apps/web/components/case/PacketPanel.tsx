"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import {
  approvePacket,
  buildPacket,
  editAppeal,
  sendAppeal,
  startAppeal,
  submitPacket,
} from "@/app/(app)/app/cases/[id]/actions";
import type { components } from "@/lib/api/schema";

type Packet = components["schemas"]["PacketOut"];
type Submission = components["schemas"]["SubmissionOut"];
type Appeal = components["schemas"]["AppealOut"];

const H3 = "text-xs tracking-wide text-ink-3 uppercase";
const BTN = "h-8 rounded-[var(--radius-control)] px-3 text-xs disabled:opacity-40";
const PAYER: Record<string, { label: string; cls: string }> = {
  A1: { label: "Certified", cls: "text-signal border-signal/40" },
  A3: { label: "Denied", cls: "text-fail border-fail/40" },
  A4: { label: "Pended", cls: "text-gap border-gap/40" },
};

function useAct(caseId: string) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const run = (fn: () => Promise<{ error?: string }>) =>
    start(async () => {
      setError(null);
      const r = await fn();
      if (r.error) setError(r.error);
      else router.refresh();
    });
  return { error, pending, run, caseId };
}

function AppealEditor({ caseId, appeal }: { caseId: string; appeal: Appeal }) {
  const router = useRouter();
  const { error, pending, run } = useAct(caseId);
  const [text, setText] = useState(appeal.draft_text);
  // The worker drafts the appeal off the request path; poll until it lands.
  useEffect(() => {
    if (appeal.status !== "drafting") return;
    const t = setInterval(() => router.refresh(), 4000);
    return () => clearInterval(t);
  }, [appeal.status, router]);

  if (appeal.status === "drafting") return <p role="status" className="mt-2 text-xs text-ink-2">Appeal agent is re-reading the chart and drafting a cited letter…</p>;
  if (appeal.status === "failed") return <p role="alert" className="mt-2 text-xs text-fail">The appeal draft failed; see the worker log.</p>;
  if (appeal.status === "sent") return <p suppressHydrationWarning className="mt-2 text-xs text-ink-2">Appeal sent{appeal.sent_at ? ` ${new Date(appeal.sent_at).toLocaleString()}` : ""}.</p>;

  const cites = Object.entries(appeal.citations);
  return (
    <div className="mt-2 space-y-2">
      <label className="block text-xs text-ink-2">
        Appeal letter (edit before sending; the cited excerpts are attached automatically)
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={9} className="mt-1 w-full rounded-[var(--radius-control)] border border-rule bg-paper px-2 py-1.5 font-mono text-[12px] leading-snug" />
      </label>
      <ul aria-label="New evidence for the appeal" className="space-y-1.5">
        {cites.flatMap(([key, list]) =>
          list.map((c, i) => (
            <li key={`${key}-${i}`} className="rounded-[var(--radius-control)] border-l-2 border-signal/50 bg-paper py-1 pr-2 pl-2.5">
              <span className="block text-[10px] text-ink-3 uppercase">{String(c.criterion_label ?? key)}</span>
              <span className="font-mono text-[12px] text-ink">“{String(c.quote)}”</span>
              <span className="mt-0.5 block text-[11px] text-signal">✓ Verbatim in chart · grounded</span>
            </li>
          )),
        )}
        {cites.every(([, l]) => l.length === 0) && <li className="text-xs text-gap">The agent found no new verified evidence. Sending will likely be denied again.</li>}
      </ul>
      {error && <p role="alert" className="text-xs text-fail">{error}</p>}
      <div className="flex gap-2">
        <button type="button" disabled={pending || text === appeal.draft_text} onClick={() => run(() => editAppeal(caseId, appeal.id, text))} className={`${BTN} border border-rule text-ink-2`}>
          Save draft
        </button>
        <button type="button" disabled={pending || text !== appeal.draft_text} onClick={() => run(() => sendAppeal(caseId, appeal.id))} className={`${BTN} bg-ink text-paper`}>
          Send appeal to payer
        </button>
      </div>
    </div>
  );
}

function SubmissionView({ caseId, sub }: { caseId: string; sub: Submission }) {
  const { error, pending, run } = useAct(caseId);
  const p = PAYER[sub.status] ?? { label: sub.status, cls: "text-ink-3 border-rule" };
  return (
    <div className="mt-2 rounded-[var(--radius-control)] border border-rule p-2.5">
      <div className="flex items-center justify-between gap-2">
        <span suppressHydrationWarning className="text-xs text-ink-3">Payer response · {new Date(sub.submitted_at).toLocaleTimeString()}</span>
        <span className={`rounded-full border px-1.5 text-[10px] uppercase ${p.cls}`}>{p.label}</span>
      </div>
      {sub.pre_auth_ref && <p className="mt-1 font-mono text-sm text-signal">Authorization {sub.pre_auth_ref}</p>}
      {sub.denials.length > 0 && (
        <ul className="mt-1.5 space-y-1">
          {sub.denials.map((d) => (
            <li key={d.criterion_key} className="text-xs text-fail">{d.reason}</li>
          ))}
        </ul>
      )}
      {error && <p role="alert" className="mt-1 text-xs text-fail">{error}</p>}
      {sub.status === "A3" && !sub.appeal && sub.denials.length > 0 && (
        <button type="button" disabled={pending} onClick={() => run(() => startAppeal(caseId, sub.id))} className={`${BTN} mt-2 bg-ink text-paper`}>
          Draft appeal
        </button>
      )}
      {/* remount when the worker finishes so the editor starts from the real draft */}
      {sub.appeal && <AppealEditor key={`${sub.appeal.id}-${sub.appeal.status}`} caseId={caseId} appeal={sub.appeal} />}
    </div>
  );
}

/** Packet → human approval → payer → (denial → appeal → resubmit). Every send is a human click. */
export function PacketPanel({ caseId, runId, caseStatus, packets }: { caseId: string; runId: string | null; caseStatus: string; packets: Packet[] }) {
  const { error, pending, run } = useAct(caseId);
  if (!packets.length) {
    return (
      <section className="mt-5">
        <h3 className={H3}>Packet</h3>
        <p className="mt-2 text-sm text-ink-3">A PAS bundle and PDF letter built from verified citations only.</p>
        {error && <p role="alert" className="mt-1 text-xs text-fail">{error}</p>}
        <button type="button" disabled={pending || !runId || caseStatus !== "ready"} onClick={() => run(() => buildPacket(caseId, runId!))} className={`${BTN} mt-2 bg-ink text-paper`}>
          Build packet
        </button>
      </section>
    );
  }
  return (
    <section className="mt-5">
      <h3 className={H3}>Packet &amp; payer</h3>
      {packets.map((pk, i) => (
        <div key={pk.id} className="mt-2 rounded-[var(--radius-panel)] border border-rule bg-paper-raised p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-ink">{i === 0 ? "Initial request" : "Appeal resubmission"} · {pk.evidence.length} excerpts</span>
            <a href={`/app/packets/${pk.id}/pdf`} target="_blank" rel="noreferrer" className="text-xs text-ink-3 underline underline-offset-4 hover:text-ink">PDF</a>
          </div>
          {pk.validation_errors.length > 0 && <p className="mt-1 text-xs text-fail">Invalid bundle: {pk.validation_errors.join("; ")}</p>}
          <details className="mt-1.5">
            <summary className="cursor-pointer text-xs text-ink-3">Letter</summary>
            <pre className="mt-1 font-mono text-[11px] leading-snug whitespace-pre-wrap text-ink-2">{pk.letter}</pre>
          </details>
          {error && <p role="alert" className="mt-1 text-xs text-fail">{error}</p>}
          {!pk.approved_at && (
            <button type="button" disabled={pending} onClick={() => run(() => approvePacket(caseId, pk.id))} className={`${BTN} mt-2 bg-signal text-paper`}>
              Approve packet
            </button>
          )}
          {pk.approved_at && pk.submissions.length === 0 && (
            <button type="button" disabled={pending} onClick={() => run(() => submitPacket(caseId, pk.id))} className={`${BTN} mt-2 bg-ink text-paper`}>
              Submit to payer
            </button>
          )}
          {pk.submissions.map((s) => (
            <SubmissionView key={s.id} caseId={caseId} sub={s} />
          ))}
        </div>
      ))}
    </section>
  );
}

"use client";

import { Check, FileText, FlaskConical, Pill, ScanLine, Stethoscope } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import type { components } from "@/lib/api/schema";
import type { CitationRef } from "@/lib/run/reducer";

type Chunk = components["schemas"]["ChunkOut"];
export type Doc = { resourceId: string; resourceType: string; date: string | null; chunks: Chunk[]; title: string };

const ICON: Record<string, typeof FileText> = {
  DocumentReference: FileText,
  DiagnosticReport: ScanLine,
  Observation: FlaskConical,
  MedicationRequest: Pill,
  Procedure: Stethoscope,
};

export function groupDocs(chunks: Chunk[]): Doc[] {
  const docs = new Map<string, Doc>();
  for (const c of chunks) {
    const d = docs.get(c.resource_id) ?? {
      resourceId: c.resource_id, resourceType: c.resource_type, date: c.date, chunks: [],
      title: c.text.split("\n")[0].slice(0, 80),
    };
    d.chunks.push(c);
    docs.set(c.resource_id, d);
  }
  return [...docs.values()];
}

const PHI_SPLIT = /(\[(?:NAME|MRN|PHONE|EMAIL|SSN)_\d+\])/;
const PHI_TOKEN = /^\[(?:NAME|MRN|PHONE|EMAIL|SSN)_\d+\]$/; // no /g: .test() must stay stateless

/** Note text with cited spans highlighted and de-identification surrogates shown as pills. */
function NoteText({ chunk, cites, focusKey }: { chunk: Chunk; cites: (CitationRef & { key: string })[]; focusKey: string | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const parts = useMemo(() => {
    const spans = cites.filter((c) => c.chunk_id === chunk.id && c.start != null && c.end != null)
      .sort((a, b) => a.start! - b.start!);
    const out: { text: string; cite?: (typeof spans)[number] }[] = [];
    let at = 0;
    for (const s of spans) {
      if (s.start! < at) continue; // overlapping citation: first one wins
      out.push({ text: chunk.text.slice(at, s.start!) });
      out.push({ text: chunk.text.slice(s.start!, s.end!), cite: s });
      at = s.end!;
    }
    out.push({ text: chunk.text.slice(at) });
    return out;
  }, [chunk, cites]);

  useEffect(() => {
    ref.current?.querySelector("[data-focused=true]")?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [focusKey]);

  return (
    <div ref={ref} className="font-mono text-[13px] leading-[1.6] whitespace-pre-wrap text-ink-2">
      {parts.map((p, i) =>
        p.cite ? (
          <mark
            key={i}
            data-focused={p.cite.key === focusKey}
            title={`Cited for ${p.cite.key}${p.cite.verified ? "" : " (failed verification)"}`}
            className={`rounded-[2px] text-ink ${p.cite.verified ? "cite-mark" : "bg-transparent underline decoration-fail decoration-wavy"} ${
              p.cite.key === focusKey ? "outline-2 outline-offset-2 outline-signal" : ""
            }`}
          >
            {p.text}
          </mark>
        ) : (
          <span key={i}>
            {p.text.split(PHI_SPLIT).map((t, j) =>
              PHI_TOKEN.test(t) ? (
                <span key={j} className="rounded-[3px] bg-rule px-1 text-[11px] text-ink-3" title="De-identified">
                  {t}
                </span>
              ) : (
                t
              ),
            )}
          </span>
        ),
      )}
    </div>
  );
}

export function ChartPane({
  docs,
  cited,
  selectedDoc,
  onSelectDoc,
  focusKey,
}: {
  docs: Doc[];
  cited: (CitationRef & { key: string })[];
  selectedDoc: string | null;
  onSelectDoc: (id: string) => void;
  focusKey: string | null;
}) {
  const citedDocs = new Set(cited.map((c) => docs.find((d) => d.chunks.some((k) => k.id === c.chunk_id))?.resourceId));
  const current = docs.find((d) => d.resourceId === selectedDoc) ?? null;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <h2 className="px-4 pt-3 text-xs tracking-wide text-ink-3 uppercase">Chart</h2>
      {docs.length === 0 ? (
        <p className="px-4 py-3 text-sm text-ink-2">The chart is loaded and indexed when a run starts.</p>
      ) : (
        <>
          <ul className="max-h-[40%] shrink-0 overflow-auto px-2 py-2" aria-label="Timeline">
            {docs.map((d) => {
              const Icon = ICON[d.resourceType] ?? FileText;
              const on = d.resourceId === selectedDoc;
              return (
                <li key={d.resourceId}>
                  <button
                    type="button"
                    onClick={() => onSelectDoc(d.resourceId)}
                    className={`flex w-full items-center gap-2 rounded-[var(--radius-control)] px-2 py-1.5 text-left text-sm ${on ? "bg-paper-raised text-ink" : "text-ink-2 hover:bg-paper-raised"}`}
                  >
                    <Icon size={14} strokeWidth={1.5} aria-hidden="true" className="shrink-0 text-ink-3" />
                    <span className="w-[74px] shrink-0 font-mono text-[11px] text-ink-3 tabular">{d.date ?? "—"}</span>
                    <span className="min-w-0 flex-1 truncate">{d.title}</span>
                    {citedDocs.has(d.resourceId) && (
                      <Check size={13} strokeWidth={2} className="shrink-0 text-signal" aria-label="Cited as evidence" />
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="min-h-0 flex-1 overflow-auto border-t border-rule px-4 py-3">
            {current ? (
              current.chunks.map((c) => <NoteText key={c.id} chunk={c} cites={cited} focusKey={focusKey} />)
            ) : (
              <p className="text-sm text-ink-3">Select an item, or a criterion, to read its source.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

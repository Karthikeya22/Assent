"use client";

import { useState, useTransition } from "react";
import { type Card, signOrder } from "./actions";

type P = { id: string; name: string; cpt: string; icd10: string };
const ORDERS = [
  { cpt: "64483", label: "Transforaminal epidural steroid injection, lumbar" },
  { cpt: "64479", label: "Transforaminal epidural steroid injection, cervical" },
  { cpt: "64582", label: "Hypoglossal nerve stimulator implantation" },
  { cpt: "22513", label: "Kyphoplasty, thoracic" },
  { cpt: "22514", label: "Kyphoplasty, lumbar" },
  { cpt: "99213", label: "Office visit, established patient" },
];
const BAR: Record<Card["indicator"], string> = { info: "#2b6cb0", warning: "#b7791f", critical: "#c53030" };
const FIELD = { border: "1px solid #a0aec0" };

/** Tiny markdown subset used by CDS cards: **bold** and "- " list lines. */
function Md({ text }: { text: string }) {
  const bold = (s: string) => s.split(/\*\*(.+?)\*\*/g).map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : part));
  return (
    <div className="space-y-0.5">
      {text
        .split("\n")
        .filter(Boolean)
        .map((line, i) =>
          line.startsWith("- ") ? (
            <div key={i} className="pl-3">• {bold(line.slice(2))}</div>
          ) : (
            <div key={i}>{bold(line)}</div>
          ),
        )}
    </div>
  );
}

/** A deliberately plain "other vendor" EHR screen: Assent shows up only as CDS cards. */
export function EhrSim({ patients }: { patients: P[] }) {
  const [pid, setPid] = useState(patients[0]?.id ?? "");
  const [cpt, setCpt] = useState(patients[0]?.cpt ?? "64483");
  const [icd10, setIcd10] = useState(patients[0]?.icd10 ?? "M54.16");
  const [cards, setCards] = useState<Card[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  function pick(id: string) {
    const p = patients.find((x) => x.id === id);
    setPid(id);
    if (p) {
      setCpt(p.cpt);
      setIcd10(p.icd10);
    }
    setCards(null);
  }

  return (
    <div style={{ fontFamily: "Segoe UI, Arial, sans-serif", background: "#e9ecef", color: "#1a202c" }} className="min-h-dvh">
      <header style={{ background: "#2d3748", color: "#fff" }} className="flex items-center justify-between px-4 py-2 text-sm">
        <span className="font-semibold">OpenChart EHR</span>
        <span style={{ opacity: 0.7 }}>Simulated EHR · synthetic patients · Assent connects via CDS Hooks</span>
      </header>
      <main className="mx-auto grid max-w-5xl gap-4 p-4 md:grid-cols-[1fr_1.1fr]">
        <section style={{ background: "#fff", border: "1px solid #cbd5e0" }} className="p-4 text-sm">
          <h1 className="mb-3 text-base font-semibold">New order</h1>
          <label className="mb-3 block">
            Patient
            <select value={pid} onChange={(e) => pick(e.target.value)} style={FIELD} className="mt-1 block h-8 w-full bg-white px-2">
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · {p.id}
                </option>
              ))}
            </select>
          </label>
          <label className="mb-3 block">
            Procedure
            <select
              value={cpt}
              onChange={(e) => {
                setCpt(e.target.value);
                setCards(null);
              }}
              style={FIELD}
              className="mt-1 block h-8 w-full bg-white px-2"
            >
              {ORDERS.map((o) => (
                <option key={o.cpt} value={o.cpt}>
                  {o.cpt} · {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="mb-4 block">
            Diagnosis (ICD-10)
            <input value={icd10} onChange={(e) => setIcd10(e.target.value)} style={FIELD} className="mt-1 block h-8 w-full bg-white px-2 font-mono" />
          </label>
          <button
            type="button"
            disabled={!pid || pending}
            onClick={() =>
              start(async () => {
                const r = await signOrder(pid, cpt, icd10);
                setCards(r.cards);
                setError(r.error ?? null);
              })
            }
            style={{ background: "#2b6cb0", color: "#fff" }}
            className="h-9 px-4 font-semibold disabled:opacity-50"
          >
            {pending ? "Signing…" : "Sign order"}
          </button>
        </section>
        <section aria-label="Decision support" className="space-y-3 text-sm">
          {error && (
            <p role="alert" style={{ color: "#c53030" }}>
              {error}
            </p>
          )}
          {cards === null && !error && <p style={{ color: "#4a5568" }}>Decision support appears here when the order is signed.</p>}
          {cards?.length === 0 && <p style={{ color: "#4a5568" }}>No decision support for this order. No prior authorization is needed.</p>}
          {cards?.map((c, i) => (
            <article key={i} style={{ background: "#fff", border: "1px solid #cbd5e0", borderLeft: `4px solid ${BAR[c.indicator]}` }} className="p-3">
              <p className="font-semibold">{c.summary}</p>
              <div className="mt-2" style={{ color: "#2d3748" }}>
                <Md text={c.detail} />
              </div>
              {c.links.map((l) => (
                <a key={l.url} href={l.url} style={{ color: "#2b6cb0" }} className="mt-2 inline-block underline">
                  {l.label} →
                </a>
              ))}
              <p className="mt-2 text-xs" style={{ color: "#718096" }}>
                Source: Assent
              </p>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}

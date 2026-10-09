export type Verdict = "met" | "not_met" | "insufficient";

// Never color alone (FRONTEND §9): every verdict carries a glyph and a text label.
const spec: Record<Verdict, { glyph: string; label: string; cls: string }> = {
  met: { glyph: "✓", label: "Met", cls: "bg-signal-soft text-signal" },
  not_met: { glyph: "✕", label: "Not met", cls: "bg-fail/10 text-fail" },
  insufficient: { glyph: "○", label: "Insufficient", cls: "bg-gap/10 text-gap" },
};

export function VerdictChip({ verdict }: { verdict: Verdict }) {
  const s = spec[verdict];
  return (
    <span
      className={`inline-flex h-5 items-center gap-1 rounded-[var(--radius-control)] px-1.5 text-xs font-medium ${s.cls}`}
    >
      <span aria-hidden="true">{s.glyph}</span>
      {s.label}
    </span>
  );
}

import type { ReactNode } from "react";

type Tone = "neutral" | "gap";

const tones: Record<Tone, string> = {
  neutral: "border-rule text-ink-2",
  gap: "border-gap/40 text-gap",
};

/** Codes, IDs and labels set in mono: CPT, ICD-10, LCD IDs, environment badges. */
export function MonoChip({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return (
    <span
      className={`inline-flex h-5 items-center rounded-[var(--radius-control)] border px-1.5 font-mono text-xs leading-none tracking-wide uppercase ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

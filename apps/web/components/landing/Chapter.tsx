import type { ReactNode } from "react";
import type { ChapterId } from "@/components/world/chapters";

const ALIGN = {
  left: "md:justify-start",
  right: "md:justify-end",
  center: "md:justify-center md:text-center",
} as const;

/**
 * One scroll chapter over the fixed world. The copy sits in a porcelain glass panel on the side
 * the camera keeps clear (camera.ts TEXT_SIDE). On narrow screens it stacks at the bottom and the
 * camera lifts the subject into the upper half.
 */
export function Chapter({
  id,
  side,
  label,
  children,
  bare = false,
  wide = false,
  top = false,
  tall = true,
}: {
  id: ChapterId;
  side: keyof typeof ALIGN;
  label: string;
  children: ReactNode;
  bare?: boolean;
  wide?: boolean;
  top?: boolean;
  tall?: boolean;
}) {
  return (
    <section
      id={id}
      data-chapter={id}
      aria-label={label}
      className={`relative z-10 mx-auto flex max-w-7xl px-4 sm:px-6 ${top ? "items-start pt-[18dvh]" : "items-end pb-[12dvh] md:items-center md:pb-0"} ${tall ? "min-h-[150dvh]" : "min-h-[100dvh]"} ${ALIGN[side]}`}
    >
      <div className={bare ? `w-full ${wide ? "md:max-w-[46rem]" : "md:max-w-[34rem]"} ${id === "hero" ? "max-md:glass max-md:p-5" : ""}` : "glass w-full p-6 md:max-w-[28rem] md:p-8"}>{children}</div>
    </section>
  );
}

export function H2({ children }: { children: ReactNode }) {
  return <h2 className="display text-[clamp(1.85rem,3.2vw,2.6rem)] leading-[1.08]">{children}</h2>;
}

export function Body({ children }: { children: ReactNode }) {
  return <p className="mt-4 text-[1.0625rem] leading-relaxed text-ink-2">{children}</p>;
}

export function Ref({ n }: { n: number }) {
  return (
    <a href={`#source-${n}`} className="ml-0.5 align-super font-mono text-xs text-ink-3 hover:text-ink" aria-label={`Source ${n}`}>
      {n}
    </a>
  );
}

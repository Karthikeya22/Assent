import type { ReactNode } from "react";
import { MonoChip } from "@/components/ui/MonoChip";

export type TopBarUser = { name: string; role: string };

/** 48px top bar: breadcrumb, SYNTHETIC DATA badge, user menu (FRONTEND §6.1). */
export function TopBar({
  breadcrumb,
  user,
  signOut,
}: {
  breadcrumb: ReactNode;
  user: TopBarUser;
  signOut: () => Promise<void>;
}) {
  const initials = user.name
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-rule bg-paper-raised/60 px-4">
      <div className="min-w-0 flex-1 truncate text-ink-2">{breadcrumb}</div>
      <MonoChip tone="gap">Synthetic data</MonoChip>
      <form action={signOut} className="flex items-center gap-2">
        <span
          title={`${user.name} · ${user.role.replace("_", " ")}`}
          className="grid size-7 place-items-center rounded-[8px] bg-ink text-xs font-medium text-paper"
        >
          {initials}
        </span>
        <button type="submit" className="py-2 text-ink-2 hover:text-ink">
          Sign out
        </button>
      </form>
    </header>
  );
}

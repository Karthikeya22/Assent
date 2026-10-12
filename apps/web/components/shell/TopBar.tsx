import { Search } from "lucide-react";
import type { ReactNode } from "react";
import { MonoChip } from "@/components/ui/MonoChip";

export type TopBarUser = { name: string; role: string };

/** 48px top bar: breadcrumb, ⌘K trigger, SYNTHETIC DATA badge, user menu (FRONTEND §6.1). */
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
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-rule px-4">
      <div className="min-w-0 flex-1 truncate text-ink-2">{breadcrumb}</div>
      {/* Command palette lands in Phase 3; the trigger is here so the layout doesn't shift. */}
      <button
        type="button"
        disabled
        className="flex h-8 w-56 items-center gap-2 rounded-[var(--radius-control)] border border-rule px-2.5 text-ink-3 disabled:cursor-not-allowed"
      >
        <Search size={14} strokeWidth={1.5} aria-hidden="true" />
        <span className="flex-1 text-left">Search</span>
        <kbd className="font-mono text-xs">⌘K</kbd>
      </button>
      <MonoChip tone="gap">Synthetic data</MonoChip>
      <form action={signOut} className="flex items-center gap-2">
        <span
          title={`${user.name} · ${user.role.replace("_", " ")}`}
          className="grid size-7 place-items-center rounded-full bg-ink text-xs font-medium text-paper"
        >
          {initials}
        </span>
        <button type="submit" className="text-ink-3 hover:text-ink">
          Sign out
        </button>
      </form>
    </header>
  );
}

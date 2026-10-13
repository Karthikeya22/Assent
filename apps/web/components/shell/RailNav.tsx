"use client";

import {
  BarChart3,
  FlaskConical,
  Inbox,
  PanelLeftClose,
  PanelLeftOpen,
  ScrollText,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const items: { href: string; label: string; icon: LucideIcon }[] = [
  { href: "/app/worklist", label: "Worklist", icon: Inbox },
  { href: "/app/policies", label: "Policies", icon: ScrollText },
  { href: "/app/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/evals", label: "Evals", icon: FlaskConical },
  { href: "/app/audit", label: "Audit", icon: ShieldCheck },
  { href: "/app/settings", label: "Settings", icon: Settings },
];

/** Left rail: 56px, expandable to 220px. Active item gets a 2px signal bar (FRONTEND §6.1). */
export function RailNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const Toggle = open ? PanelLeftClose : PanelLeftOpen;

  return (
    <nav
      aria-label="Primary"
      className="flex shrink-0 flex-col border-r border-rule bg-paper-sunk/60 transition-[width] duration-[var(--dur-2)] ease-[var(--ease-out)]"
      style={{ width: open ? 220 : 56 }}
    >
      <Link href="/app/worklist" className="wordmark flex h-12 items-center px-[18px] text-xl">
        {open ? "Assent" : "A"}
      </Link>
      <ul className="flex flex-1 flex-col gap-0.5 py-2">
        {items.map(({ href, label, icon: Icon }) => {
          const active =
            pathname.startsWith(href) || (href === "/app/worklist" && pathname.startsWith("/app/cases"));
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                title={open ? undefined : label}
                className={`relative flex h-10 items-center gap-3 px-[18px] transition-colors duration-[var(--dur-1)] ${
                  active ? "text-ink" : "text-ink-3 hover:text-ink"
                }`}
              >
                {active && <span className="absolute inset-y-2 left-0 w-0.5 bg-signal" />}
                <Icon size={20} strokeWidth={1.5} aria-hidden="true" />
                <span className={open ? "" : "sr-only"}>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Collapse navigation" : "Expand navigation"}
        aria-expanded={open}
        className="flex h-10 items-center px-[18px] text-ink-3 hover:text-ink"
      >
        <Toggle size={20} strokeWidth={1.5} aria-hidden="true" />
      </button>
    </nav>
  );
}

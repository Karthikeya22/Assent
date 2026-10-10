"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LABELS: Record<string, string> = {
  worklist: "Worklist",
  policies: "Policies",
  analytics: "Analytics",
  evals: "Evals",
  audit: "Audit",
  settings: "Settings",
};

export function Breadcrumb() {
  const parts = usePathname().split("/").filter(Boolean).slice(1); // drop "app"
  const section = parts[0] ?? "worklist";
  const label = LABELS[section] ?? section;
  return parts.length > 1 ? (
    <Link href={`/app/${section}`} className="hover:text-ink">
      {label}
    </Link>
  ) : (
    <span className="text-ink">{label}</span>
  );
}

import { notFound } from "next/navigation";

// Placeholder for rail sections not built yet. Real routes are static segments, which take
// precedence over this dynamic one, so each is replaced automatically when its phase lands.
const upcoming: Record<string, { title: string; phase: string }> = {
  analytics: { title: "Analytics", phase: "Phase 5" },
  evals: { title: "Evals", phase: "Phase 5" },
  audit: { title: "Audit", phase: "Phase 4" },
  settings: { title: "Settings", phase: "Phase 7" },
};

export default async function Upcoming({ params }: { params: Promise<{ section: string }> }) {
  const s = upcoming[(await params).section];
  if (!s) notFound();
  return (
    <div className="px-6 py-5">
      <h1 className="display text-xl">{s.title}</h1>
      <p className="mt-16 text-ink-2">
        Arrives in <span className="font-mono">{s.phase}</span>.
      </p>
    </div>
  );
}

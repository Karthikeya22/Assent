import Link from "next/link";
import { SOURCES } from "./sources";

export function Footer() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <h2 id="sources" className="font-mono text-xs tracking-wide text-ink-3 uppercase">
          Sources
        </h2>
        <ol className="mt-4 max-w-3xl space-y-2 text-sm text-ink-2">
          {SOURCES.map((s) => (
            <li key={s.id} id={`source-${s.id}`} className="flex gap-3">
              <span className="font-mono text-ink-3 tabular">{s.id}</span>
              <a href={s.url} className="underline decoration-rule underline-offset-4 hover:text-ink" rel="noreferrer" target="_blank">
                {s.text}
              </a>
            </li>
          ))}
        </ol>
        <div className="mt-12 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-ink-3">
          <span>Built by Karthikeya Moturi</span>
          <Link href="/evals" className="hover:text-ink">Benchmark</Link>
          <span>Synthetic patients only. No PHI.</span>
        </div>
      </div>
    </footer>
  );
}

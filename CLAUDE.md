# Assent

Agentic Medicare prior-auth system. Handoff and status: `docs/STATUS.md`. Specs: `PRODUCT.md`, `ARCHITECTURE.md`, `FRONTEND.md`.

## Exploring the code
- A Graphify knowledge graph is in `graphify-out/` (`GRAPH_REPORT.md` lists the hubs).
- For "where is X", "what calls X" or "what breaks if I change X", run `graphify query "<question>"` first, and `graphify path "A" "B"` to trace a link. Open a source file only after the graph points at it.
- The git post-commit and post-checkout hooks rebuild the graph. If an answer looks stale, run `graphify update .` (free, no LLM) and ask again.
- Code only: never run `/graphify` on docs or data, since that sends them to an LLM and costs tokens. Use `graphify extract . --code-only`.

## Rules
- Nothing new on C:. Tools and caches live on D: (`. .\scripts\env.ps1`).
- Never push to `main` or force-push. Work on a branch and open a PR.
- Run only the touched tests while working; run the full suite once at the end of a phase.

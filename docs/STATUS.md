# Assent: Status & Handoff (2026-10-12)

Read this first in a new session. Specs: PRODUCT.md, ARCHITECTURE.md, FRONTEND.md, BUILD_PLAN.md. Phase plans: `docs/superpowers/plans/`. The master roadmap is in `C:\Users\karth\.claude\plans\okay-lets-start-the-abundant-marshmallow.md`.

## Where things are
- Repo `D:\Projects\assent`. Stacked branches: `phase-0-foundations` → `phase-1-esi-policy-data` → `phase-2-core-agent` → `phase-4-adversary` (current; it also contains the Phase 3 work). **No GitHub remote and nothing pushed.** Ask the user before creating a remote.
- **Phases 0–4 are done and verified live in the browser.** Next is Phase 5.

## How to run (Windows, everything on D:)
```powershell
. .\scripts\env.ps1; .\scripts\dev.ps1 up        # native Postgres16+pgvector, Redis (no Docker)
uv run uvicorn assent_api.main:app --port 8000
uv run arq assent_worker.main.WorkerSettings      # AGENT_LLM=openai (cassettes) | oracle
cd apps\web; pnpm build; pnpm start -p 3000      # login coordinator@assent.dev / assent-dev
uv run python -m assent_evals.bench --split dev --llm openai --name <run>   # resumable
```
Keys are in `.env`: OPENAI_API_KEY, GEMINI_API_KEY. LLM calls are recorded to `data/fixtures/cassettes/esi`, so a re-score with an unchanged prompt costs $0.

## Measured (ESI dev, 34 cases, gpt-4.1) — also in PRODUCT §6
Criterion macro-F1 0.858 (accuracy 0.927); case accuracy 76% (0 false "ready", 8 false "not ready"); citation precision 82%; unsupported claims 0% (enforced); p50/p95 59 s/96 s; $0.093/case. Policy compiler leaf F1 vs gold: 0.75 / 0.83 / 0.83. Logs: `data/bench/results/openai-dev-judge-met.jsonl`.

## Key design decisions (with reasons)
- Lean stack for the 7 GB laptop: in-process bge-small, MiniLM reranker, DeBERTa-v3 NLI; file-backed FHIR (Synthea bundles in `.data/bench/esi`); LiteLLM as a library.
- **Citation verifier** = verbatim + NLI(3-sentence window of the quote ⇒ the agent's per-citation `claim`, clinical abbreviations expanded) + injection screen (injection text is blanked from the premise) + a gpt-4.1-mini **judge second opinion only for `met`**. Quote ⇒ criterion NLI fails (abstract or threshold criteria score ≈0). Judging `not_met` restored 23 wrong "not zoster" absence inferences.
- The adversary is `gemini/gemini-3.1-pro-preview` (2.5-pro returns 404 for new keys); fallback is flash, then gpt-4.1. `llm.models_used` makes any fallback visible.
- Human review = the run ends `needs_review` + `POST /runs/{id}/resume` (no LangGraph checkpointer). Approve returns 409 on unrebutted high-severity objections unless acknowledged.
- Re-indexing reuses chunks when the chart is unchanged; when it changed, old chunks get `superseded_at` (never deleted, because citations FK to them).
- Benchmark gold is correct by construction (fact sentences must appear verbatim in their notes). Difficulty mix 20/15/8/5/2. 34 dev / 16 test (**test split still locked**).

## Open decisions for the user
1. Should Approve also require acknowledging blocking gaps when the case isn't ready? (Recommended yes; the spec only gates on high-severity objections.)
2. GitHub repo: create it, private or public?
3. A "go" on Phase 5 (~$5–10 of API spend).

## Phase 5 next (BUILD_PLAN Phase 5)
HGNS (L38307/L38310/L38385) + PVA (L34228/L38201/L35130): ingest → gold trees → benchmark generators → 150 cases (100 dev / 50 test). Baselines (one long-context prompt; naive RAG) and ablations (reranker, verifier, adversary, hybrid). Injection set + 60 seeded-defect packets (adversary catch rate). Calibrated risk model. Improve the `met→insufficient` misses (rehab, contra, sev.baseline).

## Known gaps / small fixes
15-minute session with no refresh token; the criteria graph renders small (wide tree); the case page bundle is 597 kB (ELK); CI is written but has never run (no remote); `/policies/[id]` is read-only (no editor yet); no Storybook stories for the case components.

## Machine gotchas
7 GB RAM: run benches resumably; Claude Code may reap background shells under memory pressure. Nothing new on C:. The Playwright MCP writes only under `C:\Users\karth`, so move screenshots to `.data/screens`. Postgres may need crash recovery after a reboot: `dev.ps1 up`, then wait for "accepting connections".

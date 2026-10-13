# Assent: Status & Handoff (2026-10-12)

Read this first in a new session. Specs: PRODUCT.md, ARCHITECTURE.md, FRONTEND.md, BUILD_PLAN.md. Phase plans: `docs/superpowers/plans/`. The master roadmap is in `C:\Users\karth\.claude\plans\okay-lets-start-the-abundant-marshmallow.md`.

## Where things are
- Repo `D:\Projects\assent`. Stacked branches: `phase-0-foundations` → `phase-1-esi-policy-data` → `phase-2-core-agent` → `phase-4-adversary` (contains Phase 3) → `phase-5-breadth` → `phase-6-packet-payer` → `phase-7-launch` (current). **No GitHub remote and nothing pushed.** Ask the user before creating a remote.
- **Phases 0–4 are done and verified live in the browser. Phases 5, 6 and 7 (site) are done.** Remaining: deployment (needs the user: GitHub repo + hosting accounts), README, demo video.

## How to run (Windows, everything on D:)
```powershell
. .\scripts\env.ps1; .\scripts\dev.ps1 up        # native Postgres16+pgvector, Redis (no Docker)
uv run uvicorn assent_api.main:app --port 8000
uv run arq assent_worker.main.WorkerSettings      # AGENT_LLM=openai (cassettes) | oracle
cd apps\web; pnpm build; pnpm start -p 3000      # login coordinator@assent.dev / assent-dev
uv run uvicorn assent_mock_payer.main:app --port 8020   # Mock Payer (hidden rules: PUT /admin/rules)
uv run uvicorn assent_cds.main:app --port 8010          # CDS Hooks (EHR sim: /ehr-sim)
uv run python -m assent_evals.bench --family esi --split dev --llm openai   # resumable
```
Keys are in `.env`: OPENAI_API_KEY, GEMINI_API_KEY. LLM calls are recorded to `data/fixtures/cassettes/<family>`, so a re-score with an unchanged prompt costs $0.

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
1. GitHub repo: create it, private or public?
2. Run the family-specific retrieval-hint fix (about $1.5 to re-run HGNS/PVA)?
(Decided: approving a not-ready case requires acknowledgement.)

## Phase 5 status (branch `phase-5-breadth`)
Done: 6 HGNS/PVA LCDs plus gold trees (`data/policies/gold/build_gold.py`); 150-case benchmark (`synth/hgns.py`, `synth/pva.py`, `FAMILIES` in `synth/build.py`); `--family/--variant/--inject/--max-usd/--min-free-gb` bench flags; baselines (`baselines.py`); injection set (`injection_eval.py`); seeded-defect adversary eval (`adversary_eval.py`); risk fit (`fit_risk.py` → `assent_agents/risk_v1.json`, loaded by `denial_risk`); eval table (`report.py` → `data/bench/results/eval-table-dev.json`). Numbers are in PRODUCT §6.
The user asked to keep eval sets small (token and API cost). Runs that did not happen: the locked test split (planned 6 per family), PVA injection, naive RAG, and the reranker/hybrid/verifier ablations. Locked test split (18 cases, 6 per family) run once: 16/18 decisions correct, 0 false ready, macro-F1 0.813, 0% unsupported, $0.079/case. Injection 6/6 held. Run long benches in the foreground (`--min-free-gb 0.4`); background shells get stopped under memory pressure.
Fixed (v2): family-specific `SYNONYMS` + `CONTRA_RULE` in `evidence/agent.py`; PVA false ready 2 → 0. Fix next: HGNS sleep-study misses (still 19 criterion misses in 12 cases), the adversary false-objection rate (3.1 per clean packet). Note: ESI dev numbers predate CONTRA_RULE. `latest_observation` is deferred (see the plan doc).

## Phase 6 (branch `phase-6-packet-payer`)
The full loop was verified live in the browser on 2026-10-12. On `/ehr-sim`, signing a CPT 64483 order shows an Assent CDS card with readiness, gaps, checklist and a case link. The HGNS case (Agatha Carter) went: approve → build packet (10 verified excerpts, PAS Bundle + PDF) → approve → submit → **denied** ("CPAP evidence insufficient: 1 of 2") → appeal agent found an independent verified CPAP excerpt → send → **certified, PA-37AE4604**. Screenshot: `.data/screens/phase6-loop-certified.png`.
Pieces: `assent_fhir.pas` (build/validate/bundle_evidence), `apps/mock_payer` (:8020), `apps/cds` (:8010), `routers/packets.py` + `services/packets.py`, `assent_agents.appeal` + worker `appeal_job`, `components/case/PacketPanel.tsx`, `app/ehr-sim`.
Lean substitutions: fpdf2 instead of WeasyPrint; `validate_pas` instead of HAPI `$validate`; a templated cover letter (the appeal letter is LLM-drafted and verified); a textarea editor instead of Tiptap.
Lesson: the appeal must exclude by quote, not by chunk. One chunk can hold several independent facts; excluding whole chunks hid the second CPAP fact.

## Phase 7 (branch `phase-7-launch`)
- Landing `/` (FRONTEND §5.1): Evidence Lattice hero (React Three Fiber, real L39240 tree, procedural pages shader, particle ribbons, logic rings filling from leaf state, adversary scanner sweep), pinned 5-step scroll story (GSAP scrub → zustand → useFrame), and these sections: ledger, glass box, two agents, standards, benchmark, architecture, CTA, sources. Pure `components/lattice/timeline.ts` + `layout.ts` are unit-tested.
- Facts verified 2026-10-12: AMA press release 2026-05-13 (40/wk, 13 h, 95% delays care); CMS WISeR page (6 states, from Jan 1, 2026); ASA WISeR CPT list (ESI/HGNS/PVA). The spec's "13 service families" could not be sourced, so it was not used.
- `/evals`: an editorial report from `apps/web/public/evals/latest.json` (exported by `scripts/export_landing.py`).
- `/demo`: no login. The read-only Case Workspace replays `content/demo.json` (`record_fixture --llm openai` with review on, then `scripts/export_demo.py`).
- Budgets: landing first load 159 KB (three.js lazy, after paint); `/demo` 174 KB, case page 171 KB (ELK lazy). Reduced motion swaps in SVG stills and static numbers. No overflow at 390 px. Dark mode works.
- Landing, `/evals` and `/demo` are static, so the marketing site can deploy without the backend.

## UI revamp (2026-10-13, PRs #4, #6, #7; replaces the Phase 7 landing above)
- Design system: `DESIGN.md` (porcelain neutrals + one signal green, Geist display, wordmark kept in Instrument Serif; every text token passes AA). Audit, storyboard and object record in `docs/design/`.
- Landing: one fixed React Three Fiber world behind 11 `data-chapter` sections, flown by **Lenis** scroll (`components/world/`). Pure, tested `chapters.ts` / `camera.ts` / `pointer.ts`; scenes read `useWorld.getState().t` in `useFrame`. Cursor: folder tilt, pile repel, magnifier on the timeline, scales/stamp/screens lean.
- 3D objects: generated reference images (`scripts/gen_reference_images.py`, gpt-image) rebuilt with img2threejs. The folder used the full gated pipeline (`scripts/i2t/folder`), the others its method. Review harness: `scripts/i2t`.
- Fallbacks: per-chapter posters in `public/world/posters` (re-render with the capture snippet in the PR) for reduced motion, no WebGL or low-end devices; three.js loads on first engagement (desktop: idle).
- Budgets: landing first load 109 KB (GSAP removed); the 3D chunk is lazy (~235 KB gz). Lighthouse (local prod build): desktop 95, mobile ~80, a11y/best-practices/SEO 100. Simulated mobile LCP is ~2.8 s while real paint is ~0.5 s; the gap is the fixed React/Next runtime under 4x CPU throttling.
- App: sunk rail, raised top bar, citation chips without side borders, explicit disabled Approve, criteria-graph loading state, light-only `/login`, `/demo`, marketing.
- Not done: the 3D criteria-graph toggle in the app; the magnifier highlights rather than optically magnifies; `/review-animations` must be run by the user.

## Known gaps / small fixes
15-minute session with no refresh token; appeal drafting is polled (no SSE); the PDF has no evidence table (letter only); the criteria graph renders small (wide tree); `/policies/[id]` is read-only (no editor yet); no Storybook stories for the case components.

## Machine gotchas
7 GB RAM: run benches resumably; Claude Code may reap background shells under memory pressure. Nothing new on C:. The Playwright MCP writes only under `C:\Users\karth`, so move screenshots to `.data/screens`. Postgres may need crash recovery after a reboot: `dev.ps1 up`, then wait for "accepting connections".

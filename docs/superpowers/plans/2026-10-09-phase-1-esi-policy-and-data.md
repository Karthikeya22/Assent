# Phase 1: ESI Policy and Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The 3 ESI LCDs are ingested and versioned, there's an approved gold criteria tree per LCD in the DB, the policy compiler is built, a policy page maps LCD clauses to tree nodes, and there are 50 synthetic ESI benchmark cases (FHIR + notes + gold leaf labels).

**Architecture:** `assent_agents.policy` holds ingest (CMS Coverage API → snapshot JSON in `data/policies/`), the `CriteriaTree` schema, and the compiler graph (LangGraph, LLM through the LiteLLM Router with tier names only). `assent_api.services.policies` loads snapshots and trees into Postgres. `assent_evals.synth` generates fact sheets (seeded, deterministic), FHIR R4 bundles and LLM-written notes. Synthea supplies the background population.

**Tech Stack:** stdlib `urllib` + `html.parser`, Pydantic v2, LangGraph, LiteLLM (library), Synthea (Java, on D:), Next.js policy pages.

**Spec:** PRODUCT.md §3, §4.1. ARCHITECTURE.md §4 (policies, policy_versions, criteria_nodes, eval_cases), §6.3 (`policy_compiler_graph`), §6.4. BUILD_PLAN.md §2 Phase 1, §3. FRONTEND.md §6.6.

## Global Constraints
- Synthetic data only. No real PHI. Notes use synthetic names.
- Model IDs only in `infra/litellm.yaml`. Code asks for tiers (`reasoning`, `fast`).
- Every criterion links back to policy text: `source_quote` must be a verbatim substring of the version's `raw_text`, and `policy_span_start/end` are its offsets.
- Evidence types: `diagnosis | duration | assessment | imaging_finding | prior_therapy | contraindication | procedure_history`. This extends the spec's list with `assessment` (pain/function scales) and `procedure_history` (frequency limits), because ESI criteria need them.
- Gold trees cover chart-evidence criteria only. Procedure-technique items (image guidance, levels, sedation, steroid dose) are order attributes, recorded in the tree's `excluded` list with a reason.
- Nothing installs to C:.

## Review Focus
1. **The CMS API returns entity-encoded HTML** (`&lt;p&gt;`). The text must come out readable, with list structure kept: unescape, then strip. Test in Task 1.
2. **A gold quote that isn't verbatim in `raw_text`** (whitespace or entity drift) must fail loudly at load time, not store a bad span. Test in Task 2.
3. **The LCD changed upstream** (new version number). Ingest must write a new snapshot and version, never overwrite the old one. Test in Task 1 (`snapshot_path` includes the version, and an existing file with a different hash raises an error).
4. **Compiler extractions disagree** (the 3 samples differ). The majority merge must be deterministic and keep the provenance quote. Test in Task 3.
5. **Fact-sheet gold labels must match the tree keys exactly.** A label for a nonexistent key, or a missing leaf, fails generation. Test in Task 5.

---

### Task 1: LCD ingest
**Files:** `packages/agents/src/assent_agents/policy/{__init__,ingest,html_text}.py`, `packages/agents/tests/test_ingest.py`, `packages/agents/tests/fixtures/lcd_snippet.json`.
**Interfaces:** `html_to_text(s: str) -> str`. `fetch_lcd(lcd_id: int, version: int | None) -> LcdSnapshot`. `save_snapshot(s, root=data/policies) -> Path`. CLI `python -m assent_agents.policy.ingest L39240 L39015 L36920`.
`LcdSnapshot{source_id, lcd_id, version, title, contractor, rev_eff_date, source_url, retrieved_at, raw_text, content_hash}`.
- [ ] Tests: entity-encoded HTML becomes text with `- ` bullets and paragraph breaks. The hash is stable. A hash conflict on an existing version file raises an error.
- [ ] Implement. Run the CLI for the 3 ESI LCDs and commit the snapshots.

### Task 2: Criteria tree schema + gold trees + DB load
**Files:** `packages/agents/src/assent_agents/policy/tree.py`, `data/policies/gold/L39240-v15.tree.json` (+ L39015, L36920), `apps/api/src/assent_api/services/policies.py`, `apps/api/src/assent_api/policy_load.py` (CLI), tests.
**Interfaces:** `CriteriaTree{source_id, version, root: Node, excluded: list[Excluded]}`. `Node{key, kind, label, n_required?, evidence_type?, threshold?, lookback_days?, source_quote?, children}`. `tree.validate_against(raw_text) -> list[str]` (errors). `tree.leaves() -> list[Node]`. `services.policies.upsert_version(session, snapshot) -> PolicyVersion`, `replace_tree(session, version, tree, approve_by: UUID | None)`.
- [ ] Tests: the gold trees validate against their snapshots (every quote verbatim). A bad quote yields an error naming the key. N_OF_M requires `n_required <= len(children)`. Keys are unique.
- [ ] Load into the DB as `approved` (approved_by = the seeded policy_admin). Flagged in the phase report for human review.

### Task 3: Policy compiler graph
**Files:** `packages/agents/src/assent_agents/{llm.py,policy/compiler.py,prompts/policy_compiler_v1.md}`, tests with a fake LLM.
**Interfaces:** `llm.complete_structured(tier, messages, schema) -> BaseModel` (LiteLLM Router from `infra/litellm.yaml`). `compile_policy(snapshot, n_samples=3, llm=...) -> CriteriaTree` (a LangGraph StateGraph: segment → extract×N → merge → validate). `merge_trees(trees) -> CriteriaTree` (majority vote on leaf signatures `(evidence_type, normalized label, threshold)`, keeping the first sample's quote that validates).
- [ ] Tests with a fake LLM: 2-of-3 agreement keeps the leaf, 1-of-3 drops it, and an invalid quote is dropped and reported.
- [ ] `compare_trees(gold, compiled) -> {precision, recall}` over leaf signatures (the compiler eval metric).
- [ ] Live run once `OPENAI_API_KEY` is set. Record the cassette to `data/fixtures/cassettes/`.

### Task 4: Synthea base population
**Files:** `data/synthea/synthea.properties`, `scripts/synthea.ps1`, output `.data/synthea/fhir/*.json` (gitignored).
- [ ] Portable JDK 17 via micromamba (`D:\DevTools\jdk17`), Synthea jar in `D:\DevTools\synthea`. Generate 80 patients aged 65–90 (seeded) and keep 60.

### Task 5: ESI fact sheets, FHIR injection, notes
**Files:** `packages/evals/src/assent_evals/synth/{facts.py,fhir_build.py,notes.py,build.py}`, `packages/agents/src/assent_agents/prompts/notes_v1.md`, tests.
**Interfaces:** `make_fact_sheet(rng, difficulty, tree) -> FactSheet{patient, diagnoses, imaging, pain_onset, scales, conservative_care[], rehab, contraindications, prior_esi[], gold: dict[key, verdict], case_decision}`. `inject(bundle, facts) -> bundle` (adds Condition/Observation/Procedure/MedicationRequest/DiagnosticReport/DocumentReference). `write_notes(facts, llm) -> list[Note]`. CLI `python -m assent_evals.synth.build --service esi --n 50 --seed 7`.
Difficulty mix (BUILD_PLAN §3): 40% clean, 30% buried, 15% missing one criterion, 10% contradictory, 5% prompt-injection.
- [ ] Tests: gold labels cover every leaf, and the case decision equals the deterministic AND/OR over the gold leaves. The difficulty mix holds for n=50. Seeded output is byte-stable.
- [ ] Notes need the LLM (fast tier). Until a key exists, `build` writes FHIR + fact sheets and marks notes pending.

### Task 6: Policy pages (read-only)
**Files:** API `routers/policies.py` (`GET /api/v1/policies`, `GET /api/v1/policy-versions/{id}`), web `app/(app)/app/policies/page.tsx`, `app/(app)/app/policies/[id]/page.tsx`, `components/policy/{PolicyClauseText,CriteriaTreeList}.tsx`.
- [ ] LCD text on the left, with each criterion's `source_quote` span highlighted. The tree on the right as a nested list (mono kind pills, evidence-type glyph). Hovering a node highlights its clause, and vice versa. The React Flow editor comes later (FRONTEND §6.6).
- [ ] API tests for both routes (org-agnostic, any role).

### Task 7: Benchmark rows
- [ ] Load 50 ESI `eval_cases` (gold_json = fact sheet gold + case decision), with split 34 dev / 16 test (seeded), via `python -m assent_evals.load`.

## Exit check
An approved ESI criteria tree in the DB (3 LCD versions). 50 ESI benchmark cases with gold labels. The policy page shows clauses mapped to the tree. The compiler runs end to end (live once the key arrives).

# Assent: Build Plan

This is the plan for building Assent: the order of work, the dataset, how it's evaluated, how it ships, and how it goes on the resume. It assumes about 20 hours a week over 8 weeks. Each phase ends with something you can demo.

---

## 1. Repository layout (monorepo)

```
assent/
  apps/
    web/                 Next.js 15 (see FRONTEND.md)
    api/                 FastAPI: routers/, services/, models/, schemas/, deps/
    worker/              arq worker: jobs that invoke agent graphs
    cds/                 CDS Hooks service
    mock_payer/          PAS $submit simulator
  packages/
    agents/              LangGraph graphs: case_graph.py, policy_compiler.py, appeal_graph.py
      nodes/             one file per node
      prompts/           versioned prompts (evidence_v3.md, adversary_v2.md ...)
      tools/             search_chart, latest_observation, compute_duration
    retrieval/           hybrid search, RRF, reranker client
    fhir/                FHIR client, PAS bundle builder, Questionnaire export
    phi/                 Presidio config + custom recognizers
    evals/               dataset builders, metrics, runners, MLflow logging
  data/
    synthea/             config + custom modules (ESI, HGNS, vertebral augmentation)
    policies/            raw LCD snapshots (text + source URL + date)
    fixtures/            recorded SSE runs for the frontend
  infra/
    docker-compose.yml   postgres, redis, hapi-fhir, litellm, tei x2, minio, langfuse
    litellm.yaml
    terraform/ (stretch)
  .github/workflows/     ci.yml, evals.yml, deploy.yml
  PRODUCT.md  ARCHITECTURE.md  FRONTEND.md  BUILD_PLAN.md  README.md
```

Tooling: `uv` for Python, `pnpm` + Turborepo for JS, `ruff` + `mypy --strict`, ESLint + Prettier, pre-commit.

---

## 2. Phased plan

### Phase 0: Foundations (Week 1)
- Monorepo, Docker Compose with Postgres+pgvector, Redis, HAPI FHIR, LiteLLM, TEI, Langfuse.
- FastAPI skeleton with health checks, auth (JWT), Alembic migrations for the schema in ARCHITECTURE.md §4.
- Next.js app shell + design tokens + Storybook.
- CI: lint, type-check, unit tests on every PR.
- **Demo:** `docker compose up`, then log in and see an empty worklist.

### Phase 1: Data and policies (Week 2)
- Generate ~300 Synthea patients (age 65+ for Medicare). Load them into HAPI FHIR.
- **Synthetic notes generator:** for each case, an LLM writes 3 to 6 clinical notes from a *fact sheet* (diagnoses, dates, PT history, BMI, AHI, imaging findings). Because the fact sheet is the ground truth, the gold labels come for free. Vary the writing: abbreviations, negations ("denies prior PT"), buried facts, contradictions.
- Pull the 9 v1 LCDs (ESI: L39015, L39240, L36920; HGNS: L38307, L38310, L38385; vertebral augmentation: L34228, L38201, L35130) through the CMS Coverage API, and store the text with the source URL and date.
- **Policy Compiler** v1: LCD → criteria tree (structured output, self-consistency ×3, majority merge). Review every tree by hand, then approve it. This is your gold policy set.
- **Demo:** the policy editor shows an LCD with the clauses mapped to a tree.

### Phase 2: The core agent (Weeks 3–4)
- `chart_loader` → `deidentify_and_index` → hybrid retrieval (BM25 + pgvector + RRF + rerank).
- `evidence_agent` with tools and structured output, fanned out with `Send`.
- `citation_verifier` (verbatim + NLI) and `logic_engine` (three-valued tree evaluation, unit-tested heavily).
- Runs execute in the worker with the Postgres checkpointer, and SSE streams through Redis pub/sub.
- Frontend: Case Workspace built on recorded fixtures first, then wired to live SSE.
- **Demo:** create a case, watch the criteria graph resolve live, and click into the cited evidence.

### Phase 3: Adversary, gaps, human review (Week 5)
- `payer_adversary` (a different model vendor) + `advocate_rebuttal`, one round.
- `gap_planner`, `risk_scorer` (fit once the eval data exists, and use a heuristic until then).
- `interrupt()` human review + `/runs/{id}/resume`. Verdict overrides with the audit log.
- **Demo:** objections appear, one gets rebutted and one becomes a gap task, then approve.

### Phase 4: Packet, payer, appeal (Week 6)
- PAS-style FHIR Bundle builder + validation against HAPI's `$validate`. PDF letter via WeasyPrint.
- Mock Payer with configurable hidden rules and denial reasons. Submission + polling.
- `appeal_graph` + Tiptap appeal editor with live citation chips.
- CDS Hooks service + the `/ehr-sim` page.
- **Demo:** the full loop: order → packet → denial → appeal → approval.

### Phase 5: Evals and hardening (Week 7)
- Build the benchmark (§3), run the baselines, log to MLflow, add the `evals.yml` CI gate.
- Prompt-injection test set, PHI-leak test on outbound payloads, load test (Locust, 20 concurrent runs).
- Policy drift watcher (cron + semantic diff UI).
- **Stretch:** QLoRA fine-tune of Llama 3.1 8B as a leaf-verdict classifier on the train split + reviewer overrides, served on vLLM. Compare F1/cost against the reasoning tier.

### Phase 6: Marketing site and launch (Week 8)
- Landing page sections, then the `EvidenceLattice` 3D hero, then the pinned scroll story.
- `/demo` against a public, rate-limited endpoint. `/evals` report page.
- Deploy (§6). Record a 2-minute demo video. Write the README with the architecture diagram, GIFs and the eval table.

---

## 3. Benchmark design

| Item | Plan |
|---|---|
| Size | 150 cases: 50 per service family. Split 100 dev / 50 test (test stays locked until the final run) |
| Labels | Leaf-level verdicts derived from the fact sheets, plus a final case decision. Hand-check 30 random cases |
| Difficulty mix | 40% clean, 30% buried evidence, 15% missing one criterion, 10% contradictory notes, 5% prompt-injection notes |
| Seeded defects | For the adversary: 60 packets with one deliberately weak or stale citation |
| Baselines | (a) Long-context single prompt: whole chart + policy → JSON verdicts. (b) Naive RAG: dense top-5, no rerank, no verifier, no adversary |
| Ablations | Remove reranker, verifier, adversary and hybrid search one at a time. This shows which components earn their place |
| Metrics | Criterion F1 (macro), case accuracy, citation precision, unsupported-claim rate, adversary catch rate, p50/p95 latency, cost per case |
| Tracking | MLflow experiment `assent-bench`, with git SHA, model IDs and prompt versions per run |
| CI gate | On PRs that touch `packages/agents/**`, run the dev split (or a 30-case smoke subset). Fail if criterion F1 drops by more than 2 points |

Report the numbers you actually get, including the failures.

---

## 4. Testing
- **Unit:** logic engine truth tables, RRF math, PHI recognizers, PAS bundle builder, hash-chained audit log.
- **Contract:** OpenAPI schema snapshot. The frontend client is regenerated in CI and type-checked.
- **Agent:** deterministic replay with recorded LLM responses (VCR-style cassettes) to make node tests fast and free.
- **E2E (Playwright):** worklist → case → run (fixture mode) → approve → packet. Visual snapshots for the landing page at 3 breakpoints.
- **Load:** Locust, 20 concurrent runs, watching queue depth and p95 latency.

---

## 5. Deployment
| Piece | Where |
|---|---|
| Web | Vercel (Next.js) |
| API, worker, CDS, mock payer | Fly.io machines, or AWS ECS Fargate |
| Postgres + pgvector | Neon or AWS RDS |
| Redis | Upstash |
| HAPI FHIR | Fly.io machine with a persistent volume |
| Embeddings/rerank/NLI | One small GPU box (or CPU with bge-small for the demo) |
| Secrets | Fly secrets / AWS Secrets Manager |
| CI/CD | GitHub Actions: test → build images → push to GHCR → deploy on main |

Set a hard monthly LLM budget in LiteLLM for the public demo.

---

## 6. Resume entry (draft, fill in real numbers after Phase 5)

**Assent: Agentic Prior Authorization Copilot for Medicare (WISeR / CMS-0057-F)** | Next.js, FastAPI, LangGraph, HL7 FHIR | *[Month Year] – Present*

- Built a multi-agent LangGraph system that compiles Medicare coverage policies (LCDs) into executable criteria graphs and verifies each criterion against FHIR patient records with hybrid RAG (BM25 + pgvector + cross-encoder reranking), reaching **[X] criterion-level F1** across 3 WISeR service families on a 150-case benchmark.
- Engineered a citation verification layer (verbatim span matching + DeBERTa NLI entailment) and an adversarial payer-reviewer agent that cut unsupported claims to **[X]%** and caught **[X]%** of seeded documentation defects before submission, **[X] points** better than a long-context LLM baseline.
- Shipped a full-stack product (Next.js 15, React Three Fiber, FastAPI, SSE streaming) with human-in-the-loop review, Da Vinci PAS FHIR bundle generation, CDS Hooks integration and PHI de-identification (Presidio), processing a case in **[X]s p50** at **$[X]** per case via LiteLLM model routing.

**Keywords covered:** Agentic AI, Multi-Agent Systems, LangGraph, RAG, Hybrid Search, Reranking, LLM Evaluation, LLM-as-Judge, Guardrails, Human-in-the-Loop, Prompt Engineering, Structured Outputs, Tool Calling, QLoRA Fine-Tuning, vLLM, HL7 FHIR, CDS Hooks, SMART on FHIR, HIPAA-aligned design, PHI De-identification, FastAPI, Next.js, React, TypeScript, Three.js, PostgreSQL, pgvector, Redis, Docker, CI/CD, MLflow, Langfuse, OpenTelemetry.

**Which project to replace:** project #2 (Self-Correcting RAG + LLM-as-Judge). Assent covers its keywords (RAG, reranking, LLM-as-Judge, guardrails, MLflow) inside a domain problem.

---

## 7. Interview talking points
1. **Why a deterministic logic engine?** LLMs judge evidence, and code combines the verdicts. That makes the outcome reproducible, auditable and testable with truth tables.
2. **Why a different vendor for the adversary?** Models from the same family share blind spots. Using a different vendor gives a real second opinion. Show the ablation numbers.
3. **How do you stop hallucinated evidence?** Verbatim span matching plus NLI, enforced in code, with downgrade rather than deletion. Show the unsupported-claim metric.
4. **How does this connect to real systems?** FHIR R4 data, CDS Hooks at order time, a PAS-style bundle out, and DTR Questionnaire export. These are the same standards CMS-0057-F requires by January 2027.
5. **What fails?** Have three real failure cases ready (for example negation in notes, conflicting dates, imaging phrased in ways the policy doesn't use) and what you changed because of them.

---

## 8. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Synthetic notes too clean, so inflated metrics | Difficulty mix + hand-written hard cases + report per-difficulty scores |
| LLM cost during development | VCR cassettes, fast tier for iteration, prompt caching |
| 3D hurts performance | Lazy-load, demand frameloop, DPR clamp, poster fallback, Lighthouse CI |
| Scope creep | v1 is 3 service families only. Everything else waits for v2 |
| Policy text changes | Versioned policies + drift watcher (that's a feature) |

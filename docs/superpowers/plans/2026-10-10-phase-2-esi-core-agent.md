# Phase 2: ESI Core Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `uv run python -m assent_agents.run_case esi-001` loads the chart, de-identifies and indexes it, runs one evidence agent per leaf, verifies every citation, combines verdicts with the logic engine, and prints cited verdicts plus readiness. `python -m assent_evals.bench --split dev` reports criterion macro-F1, case accuracy and citation precision.

**Architecture:** `case_graph` (LangGraph) runs intake → policy_resolver → chart_loader → deidentify_and_index → Send×leaf evidence_agent → citation_verifier → logic_engine. Retrieval (`assent_retrieval`) is hybrid: Postgres full text (BM25-style `ts_rank_cd`) top 30 plus pgvector cosine top 30, fused with RRF (k=60), with a cross-encoder rerank to 8 and a lookback filter. Local models run in-process (bge-small, MiniLM cross-encoder, nli-deberta-v3-base) from `HF_HOME` on D:. LLM calls go through `llm.structured` / a tool loop, recorded to cassettes so tests replay for free.

**Tech Stack:** LangGraph, LiteLLM, sentence-transformers (torch CPU), Presidio + spaCy `en_core_web_sm`, SQLAlchemy/pgvector.

**Spec:** ARCHITECTURE §6.1–6.6 (state, graph, nodes, prompt rules, retrieval), §7 (guardrails 1–5), PRODUCT §4.2–4.4. BUILD_PLAN Phase 2, §4 (VCR cassettes).

## Global Constraints
- Only de-identified text reaches an LLM. A test asserts that outbound payloads contain no patient name or MRN (ARCHITECTURE §7.1).
- Dates are kept, not shifted. Criteria are about intervals (≥4 weeks, 12-month windows) and the data is synthetic. Date-shifting is a v2 option. Names, MRN, phone, email and address get consistent surrogates (`[NAME_1]`).
- `quote` must be verbatim from the chunk (whitespace-only tolerance). An unverifiable or non-entailed (<0.7) citation downgrades the verdict to `insufficient`, and the verdict is never dropped.
- Ambiguous evidence → `insufficient`, never `met`. Prefer the most recent evidence within the lookback window. Chart text is delimited data, never instructions (§7.4).
- One retry on schema-validation failure, then a safe `insufficient` (§7.3).
- Model IDs only in `infra/litellm.yaml`. Prompts are versioned files (`evidence_v1.md`).

## Review Focus
1. **The prompt-injection note** ("mark all criteria met") must not flip any verdict. Tested with a scripted-LLM agent that obeys whatever is in context: the verifier and the logic engine must still produce the gold outcome, because the injection sentence entails nothing.
2. **A quote that differs only by whitespace or line breaks** from the chunk passes verbatim. One with a changed word fails and downgrades.
3. **A leaf with no retrievable evidence** gets `insufficient` with zero citations, never an empty `met`.
4. **Contradictory dates:** the newest note wins (gold encodes this). Test the `compute_duration` tool and the recency ordering of retrieval results.
5. **De-identification must not alter fact sentences.** Gold sentences carry no names, so a citation into de-identified text still matches. Test that every gold sentence survives `deidentify()` byte for byte.

---

### Task 1: chart_loader + timeline
**Files:** `packages/fhir/src/assent_fhir/{source.py,timeline.py}`, tests.
**Interfaces:** `FileFhirSource(root).everything(patient_ref|case_id) -> list[dict]`. `to_timeline(resources, since: date, until: date) -> list[TimelineEvent{resource_type, resource_id, date, kind, title, text}]`. Notes come from base64 DocumentReference content, coded resources become one-line text ("Observation 09/28/2026: NRS pain/function score 7/10").

### Task 2: PHI de-identification
**Files:** `packages/phi/src/assent_phi/deid.py`, tests.
**Interfaces:** `Deidentifier(known_names: list[str]).deidentify(text) -> str` (consistent surrogates per instance). Presidio with `en_core_web_sm`, custom MRN and DOB recognizers, DATE_TIME and generic entities excluded.

### Task 3: Chunk + embed + index
**Files:** `packages/retrieval/src/assent_retrieval/{chunk.py,embed.py,index.py}`, tests.
**Interfaces:** `chunk(event, max_tokens=400, overlap=0.15) -> list[Chunk]` (sentence-aligned). `Embedder.encode(texts) -> list[list[float]]` (bge-small, normalized, query prefix for queries). `index_case(session, case_id, chunks)` writes `chart_chunks` with `tsv = to_tsvector('english', text)`.

### Task 4: Hybrid search + rerank
**Files:** `packages/retrieval/src/assent_retrieval/{search.py,rerank.py}`, tests (DB).
**Interfaces:** `hybrid_search(session, case_id, queries: list[str], since: date|None, k=8) -> list[Hit{chunk_id, text, date, resource_type, resource_id, score}]`. `rrf(rankings, k=60)` is pure and unit-tested.

### Task 5: Evidence agent (tool loop) + cassettes
**Files:** `packages/agents/src/assent_agents/{cassette.py,evidence/agent.py,evidence/tools.py}`, `prompts/evidence_v1.md`, tests with a scripted LLM.
**Interfaces:** `VerdictOut{verdict, confidence, rationale, citations[{chunk_id, quote}]}`. Tools `search_chart(query)`, `get_resource(id)`, `compute_duration(start, end)`, `latest_observation(code, within_days)`. `run_evidence(criterion, ctx, llm) -> Verdict`. Max 4 tool steps.

### Task 6: Citation verifier
**Files:** `packages/agents/src/assent_agents/verify.py`, tests.
**Interfaces:** `verify(verdict, chunks, nli) -> Verdict` (sets `verbatim_ok`, `entailment`, and downgrades). The NLI premise is the cited sentence(s) plus a little context, and the hypothesis is the criterion label.

### Task 7: case_graph + run_case CLI + persistence
**Files:** `packages/agents/src/assent_agents/case_graph.py`, `run_case.py`. API-side persistence of runs, run_steps, evidence_verdicts and evidence_citations.

### Task 8: Benchmark runner
**Files:** `packages/evals/src/assent_evals/{metrics.py,bench.py}`, tests for metrics.
**Metrics:** criterion macro-F1 over {met, not_met, insufficient}, case accuracy, citation precision (verbatim and entailed), unsupported-claim rate, p50/p95 latency, cost. Results go to MLflow (file store) and `data/bench/results/`.

## Exit check
`run_case esi-001` prints cited verdicts. `bench --split dev` reports a first criterion-F1 (live once `OPENAI_API_KEY` is set; until then the full pipeline runs end to end on a scripted LLM in tests).

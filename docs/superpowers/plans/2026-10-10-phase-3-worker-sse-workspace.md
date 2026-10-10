# Phase 3: Worker, SSE, Case Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task.

**Goal:** A coordinator creates or opens a case, clicks Run, and watches the criteria graph resolve live from real system events, then clicks a node to see its cited evidence. The worklist shows real cases.

**Architecture:** `POST /cases/{id}/runs` enqueues an arq job. The worker runs `case_graph` with an `emit` callback, and every event is published to Redis channel `run:{run_id}` and appended to a capped Redis list (`run:{run_id}:log`) for late joiners. `GET /runs/{id}/stream` is an SSE endpoint that first replays the log, then streams pub/sub until `run_finished`. The event contract is exactly ARCHITECTURE §5 (`node_started`, `retrieval`, `verdict`, `logic_update`, `node_finished`, `run_finished`). Recorded runs (`data/fixtures/run_*.jsonl`) drive the UI before the backend exists, as well as Storybook and Playwright.

**Spec:** ARCHITECTURE §1, §5 (cases, runs, SSE contract), FRONTEND §6.2, §6.3, §8 (`useRunStream`), BUILD_PLAN Phase 3.

## Global Constraints
- The motion on screen is real state: graph animation is driven only by `retrieval`, `verdict` and `logic_update` events.
- One reducer turns events into normalized run state. React Flow nodes subscribe to their own slice through a Zustand selector, so one verdict re-renders one node.
- `prefers-reduced-motion`: state changes become color changes only.
- Verdicts are never shown by color alone (glyph + text). Every 3D piece is out of scope here (2D graph only).
- Org scoping on every case/run route. SSE requires auth (token in the query string, since EventSource can't set headers; short-lived, same JWT).

## Review Focus
1. **A client that connects after the run started** must still get the full picture (log replay, then live), with no duplicate or missing events.
2. **A client that connects after the run finished** gets the log and an immediate close.
3. **The worker crashes mid-run:** the run is marked `failed`, a `run_failed` event is emitted, and the UI shows it instead of spinning forever.
4. **Two runs for the same case at once:** the second POST returns 409 while one is running.
5. **Replaying the same fixture twice** through the reducer yields identical state (deterministic reducer).

## Tasks
1. `emit` hook in case_graph + an event schema module (`assent_agents.events`), unit-tested with a list sink.
2. Run lifecycle API: `POST /cases/{id}/runs` (202, 409 if running), `GET /runs/{id}`, `GET /runs/{id}/verdicts`, `GET /cases/{id}`, `GET /runs/{id}/stream` (SSE). Worker job `run_case_job`.
3. Fixture recorder: `python -m assent_evals.record_fixture esi-001` writes `data/fixtures/run_esi-001.jsonl` from a real oracle run.
4. Frontend: `lib/sse/useRunStream.ts` (EventSource + reconnect + reducer), `lib/store/runStore.ts`, a fixture replayer (`?replay=esi-001`).
5. Case Workspace `/app/cases/[id]`: header (patient, CPT/LCD chips, readiness bar, Run button), ChartPane (timeline + note viewer with cited spans), CriteriaGraph2D (React Flow + ELK, LeafNode/LogicNode/RootNode), DecisionPane (readiness dial, gaps placeholder), TraceDrawer (collapsed stepper with timings), EvidenceCard popover.
6. Worklist from real cases (dense table, readiness segment bar, status), with seeded benchmark cases.

## Exit check
Open a benchmark case, click Run (oracle or OpenAI), and watch the leaves resolve live. Clicking a leaf shows the verified quote highlighted in its note. Playwright smoke: login → worklist → case → run (fixture replay) → all leaves resolved.

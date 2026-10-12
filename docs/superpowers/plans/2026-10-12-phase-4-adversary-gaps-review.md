# Phase 4: Adversary, Gaps, Human Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task.

**Goal:** After the evidence pass, a Payer Adversary (Gemini, a different vendor) attacks the packet. The Advocate rebuts each objection with verified chart evidence or concedes it. Conceded objections and unmet criteria become gap tasks. A denial-risk score is computed. A coordinator reviews, can override verdicts (audited), and approves only when no high-severity objection is open.

**Spec:** PRODUCT §4.5, §4.6, §4.9. ARCHITECTURE §5 (objections, gaps, verdict override, resume), §6.3 (`payer_adversary`, `advocate_rebuttal`, `gap_planner`, `risk_scorer`, `human_review`). FRONTEND §6.3 (decision pane: objections thread, gap cards, approve gate, override).

## Design decisions
- **The adversary sees only the packet**: per criterion, the verdict, the rationale and the verified quotes (not the chart). Tier `adversary` (Gemini 3.1 Pro). It returns 0–5 objections `{criterion_key, text, severity}`.
- **Advocate rebuttal** (tier `reasoning`): for each objection, search the chart (same hybrid search) and answer `rebutted` with citations, or `conceded`. Rebuttal citations go through the **same verifier**. An unverifiable rebuttal becomes `conceded`, never silently kept. One round.
- **Gap planner** (tier `fast`): one task per blocking gap (`gapKeys` logic: unmet leaves with no satisfied ancestor) and per conceded objection. Each task names the assignee role and cites the policy clause.
- **Risk scorer**: a transparent heuristic until Phase 5 fits a calibrated model. `risk = σ(w·features)`, with features: blocking gaps, open/conceded high-severity objections, mean citation support, and judge-rescued share. The top 3 contributing factors are returned for the waterfall.
- **Human review without a checkpointer**: the run ends in `needs_review` with everything persisted. `POST /runs/{id}/resume {decision: approve|reject, acknowledge_high?}` is the interrupt resume. This is functionally the LangGraph `interrupt()` contract, with state in Postgres instead of a checkpoint blob. shortcut: swap to `langgraph-checkpoint-postgres` if mid-graph pauses are ever needed.
- **Verdict override** `PATCH /verdicts/{id} {verdict, reason}`: audited (hash chain), recomputes readiness/logic, and lands in the eval inbox (an `overridden_by` row the bench can pull).

## Review Focus
1. An adversary objection about a criterion key that doesn't exist is dropped (logged), never crashes.
2. A rebuttal whose quote isn't verbatim or grounded is `conceded`.
3. Approve with an open high-severity objection → 409 unless `acknowledge_high=true`. The approval is audited with the acknowledgement.
4. An override with an empty reason → 422. The audit row holds before/after.
5. The adversary sees no chart text beyond verified quotes, and nothing outside the PHI guard.

## Tasks
1. `assent_agents/adversary.py`: schemas, prompts (`adversary_v1.md`, `advocate_v1.md`), `run_adversary`, `run_rebuttals`, with scripted-LLM tests.
2. `assent_agents/gaps.py` (planner, `gap_planner_v1.md`) + `risk.py` (heuristic + factors), tested.
3. Wire into `case_graph`: after logic → adversary → rebuttals → gaps → risk. Events `objection`, `objection_update`, `gap`, and `run_finished` with `denial_risk`.
4. Persist objections + gap_tasks + case.denial_risk. API: `GET /runs/{id}/objections`, `GET /cases/{id}/gaps`, `PATCH /gaps/{id}`, `PATCH /verdicts/{id}`, `POST /runs/{id}/resume`. Tests (Review Focus 3, 4).
5. UI: ObjectionThread (adversary purple, rebuttal under it, status chip), GapTaskCard, RiskWaterfall, OverrideDialog, the Approve gate with confirm.
6. Live check in the browser on a benchmark case. Commit.

## Exit check
Objections appear; at least one is rebutted with a verified quote and one becomes a gap task; approve is blocked until acknowledged; an override is audited.

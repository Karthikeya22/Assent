# Phase 5: Breadth + Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Add the other two v1 service families, hypoglossal nerve stimulation (HGNS: L38307, L38310, L38385) and percutaneous vertebral augmentation (PVA: L34228, L38201, L35130), and turn the benchmark into the full 150 cases (50 per family; 100 dev / 50 test, test locked). Then measure honestly: two baselines, component ablations, a prompt-injection set, seeded defects for the adversary catch rate, and a calibrated risk model.

**Spec:** BUILD_PLAN §2 Phase 5 and §3, PRODUCT §3, §6.

## Tasks
1. Ingest the 6 LCDs, read their coverage sections, and hand-author gold trees (one leaf key-space per family, quotes verbatim per LCD; tests extend `test_tree.py` to all families).
2. Generalize the synth generator: `EsiFacts` becomes a per-family spec (`synth/families/{esi,hgns,pva}.py`) holding leaves, the condition sampler, phrases and FHIR coding. Numeric criteria (AHI, BMI, CPAP failure, fracture age, pain score) exercise the `latest_observation` tool. Build 50 HGNS + 50 PVA cases. The ESI benchmark must stay byte-identical (regression test).
3. ~~Evidence agent: add `latest_observation(code, within_days)`~~ **Deferred.** Every met/not_met fact is a note sentence by construction, so search already reaches the numbers. Changing the agent's step schema would invalidate every ESI cassette (a full paid re-run) for no measurable gain on this benchmark. Coded Observations are still emitted in clean cases. Revisit when real charts carry numbers only as structured data. The service name and policy come from the case family (done via `FAMILIES`).
4. Splits: 100 dev / 50 test overall (ESI keeps its existing 34/16; HGNS and PVA each 33/17). `eval_cases` loads all families.
5. Baselines: (a) one long-context prompt (whole de-identified chart + criteria → JSON verdicts); (b) naive RAG (dense top-5, no rerank, no verifier, no adversary). Ablations: −reranker, −verifier, −hybrid (dense only). All through the bench harness with cassettes.
6. Injection set (an attack note per case variant; 0 verdict flips allowed) and 60 seeded-defect packets (one weak or stale citation each) for the adversary catch rate.
7. Calibrated risk model: logistic regression on dev-run features vs gold decision, plus isotonic calibration; replaces the hand weights.
8. Report: `/evals` data JSON + PRODUCT §6 updated with per-family numbers.

## Exit check
An eval table with real numbers for the 3 families, baselines and ablations, failures included. Test split run once at the end.

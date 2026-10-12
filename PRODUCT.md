# Assent

**Prior authorization, argued with evidence.**

Assent is an agentic AI system that reads a patient's chart and checks it against the exact Medicare coverage policy for an ordered procedure. It proves every coverage criterion with a cited sentence from the record. Before the packet goes out, it has the packet attacked by a simulated payer reviewer. What comes out is a standards-based prior authorization request (HL7 FHIR, Da Vinci PAS), a list of the documentation gaps to close, and, if a denial comes back, a policy-grounded appeal.

---

## 1. The problem

Prior authorization (PA) is the approval an insurer requires before a procedure is performed. It is one of the most expensive pieces of administrative work in US healthcare, and 2026 is the year the federal rules around it changed.

| Signal | Number | Source |
|---|---|---|
| PAs a physician handles per week | ~40 | AMA 2025 Prior Authorization Physician Survey |
| Physician and staff hours per week spent on PA | ~13 | AMA 2025 |
| Physicians who say PA delays necessary care | 95% | AMA 2025 |
| Physicians reporting a serious adverse event tied to PA | 26% | AMA 2025 |
| Initial claim denial rate (2024) | 11.8% | industry denial benchmarks |
| Denied claims that are ever appealed | < 0.2% | industry denial benchmarks |
| Appealed denials that are overturned | ~54% | industry denial benchmarks |

**Why now (2026):**

1. **CMS WISeR Model (Jan 1, 2026 to Dec 31, 2031).** Original Medicare now requires prior authorization in AZ, NJ, OH, OK, TX and WA for 13 service families. The reviews are run by technology companies using AI. Providers who have never done Medicare PA now have to do it, with 3-day standard decision windows.
2. **CMS-0057-F Interoperability and Prior Authorization Final Rule.** Since Jan 1, 2026, payers must answer within 72 hours (expedited) or 7 days (standard) and must give a specific denial reason. By **Jan 1, 2027** they must expose FHIR Prior Authorization, Patient Access, Provider Access and Payer-to-Payer APIs.
3. **The payer side is using AI to review.** About six in ten physicians worry that AI will raise denial rates. Providers need an AI on their side that is just as rigorous and fully transparent.

**The core insight:** most PA denials are not medical judgment calls. They happen because the evidence is in the chart but not in the packet. It might be buried in a note from three visits ago, phrased differently than the policy, or missing one required element, like "six weeks of conservative therapy". That makes this a retrieval and reasoning problem, which modern AI can solve well, as long as it can prove every claim it makes.

---

## 2. Who it is for

| Persona | Job to be done | What they see in Assent |
|---|---|---|
| **PA coordinator** (primary user) | Get approvals out fast and correct, with no back-and-forth | Worklist with SLA clocks, one-click packets, gap tasks |
| **Ordering clinician** | Know what to document so the procedure gets approved | An inline "missing evidence" checklist at order time (CDS Hooks card) |
| **Revenue cycle / denials lead** | Overturn wrongful denials and spot patterns | Appeal drafts, denial reason analytics, policy drift alerts |
| **Compliance officer** | Prove nothing was fabricated or overstated | Immutable audit trail, citation verification report |

---

## 3. Scope: v1 services

v1 focuses on three WISeR service families whose LCDs have clear, checkable criteria:

| Service | Coverage policy (LCDs) | Why chosen |
|---|---|---|
| Epidural Steroid Injections for Pain Management | L39015, L39240, L36920 | High volume, criteria based on duration and history of conservative care |
| Hypoglossal Nerve Stimulation for OSA | L38307, L38310, L38385 | Numeric criteria (AHI, BMI, CPAP failure), good for precise evaluation |
| Percutaneous Vertebral Augmentation | L34228, L38201, L35130 | Imaging-dependent criteria, so it exercises reasoning over radiology reports |

Always confirm the current LCD versions in the CMS Medicare Coverage Database. Ingesting them is part of the build.

**Out of scope for v1:** real PHI, live payer connections, pharmacy (drug) PA, commercial payer policies.

---

## 4. Features

### 4.1 Policy Compiler (novel)
It turns a coverage policy (an LCD written in prose) into an **executable Criteria Graph**: a typed AND/OR/N-of-M tree of atomic criteria. Each criterion has an evidence type (diagnosis, duration, lab value, imaging finding, prior therapy, contraindication), a threshold where relevant, and a link back to the policy paragraph it came from.
- LLM extraction with structured outputs, then a human sign-off step, then version control.
- Every graph is versioned. A **policy drift watcher** pulls new LCD revisions, recompiles them, and shows a semantic diff ("criterion 3 threshold changed from 6 to 4 weeks").
- Graphs export as a FHIR `Questionnaire` (Da Vinci DTR format), so the work is reusable in standard tooling.

### 4.2 Chart Reader
- It pulls the patient record from a FHIR R4 server (Conditions, Procedures, MedicationRequests, Observations, DiagnosticReports, DocumentReference notes).
- It normalizes the record into a **patient timeline** and runs the text through PHI de-identification before any external model call.
- It builds a per-case hybrid index (BM25 + dense vectors) over note chunks and structured facts.

### 4.3 Evidence Agents
- One agent per leaf criterion runs in parallel. Each retrieves candidates, reranks them, and returns a verdict: `met`, `not_met` or `insufficient`. The verdict comes with **exact quoted spans** and FHIR resource IDs.
- A deterministic logic engine (not the LLM) combines leaf verdicts through the graph. The final decision is explainable and reproducible.

### 4.4 Citation Verifier
- Every quote must match the source verbatim. Fuzzy-match tolerance covers whitespace only.
- An NLI entailment check confirms that the quote actually supports the criterion.
- Unsupported verdicts are downgraded to `insufficient`. They are never silently kept.

### 4.5 Payer Adversary (novel)
- A separate red-team agent plays a strict payer medical reviewer. Its only goal is to find a defensible reason to deny the packet.
- The Advocate agent must answer each objection with evidence or concede it. Objections that survive become gap tasks.
- The output is a **Denial Risk score** with the top three objections and their evidence status.

### 4.6 Gap Planner
- It turns failed or insufficient criteria into concrete documentation tasks addressed to the right person. Example: "Document the start date and outcome of physical therapy. The policy requires at least 4 weeks (LCD L39240 §Coverage Indications 2b)."
- It also runs as a **CDS Hooks `order-sign` service**, so a clinician gets the checklist at the moment of ordering (Da Vinci CRD pattern).

### 4.7 Packet Builder and Submission
- It generates a Da Vinci PAS-style FHIR `Bundle` (Claim + supporting info) and a human-readable PDF letter of medical necessity.
- It submits to the **Mock Payer** service, which runs hidden rules and returns a `ClaimResponse` (approved, denied with reason, or pended for more info).
- An SLA clock tracks the 72-hour and 7-day windows from CMS-0057-F.

### 4.8 Appeal Agent
- When a denial arrives, it parses the denial reason, maps it to criteria, and searches for evidence it missed.
- It drafts a first-level appeal letter that cites the policy section and chart evidence line by line.

### 4.9 Human-in-the-loop by design
- Nothing is submitted without a human approval step (a LangGraph interrupt).
- Reviewers can override any verdict. Overrides are logged and feed the eval set.

### 4.10 Glass Box
- Every run has a full agent trace: node, model, prompt version, tokens, cost, latency, retrieved chunks and verdict.
- A public **Evals** page shows benchmark results against baselines.

---

## 5. Key user flows

1. **New order, then a ready packet.** The coordinator opens a case from the worklist. Assent runs automatically (about 60 seconds) and shows readiness at 92% with one amber gap. The coordinator clicks the gap, sees the note where PT is mentioned without dates, sends a task to the clinician, gets the addendum, re-runs, sees 100%, reviews the adversary objections, approves and submits.
2. **Clinician at order time.** The EHR fires `order-sign`. The Assent CDS card says: "2 of 5 criteria not yet documented: BMI within 90 days, CPAP intolerance."
3. **Denial, then appeal.** The Mock Payer denies with "conservative therapy not documented". The appeal agent finds a PT discharge summary that was missed and drafts the appeal. The coordinator edits and sends it.
4. **Policy changes.** The drift watcher flags an LCD revision. The policy admin reviews the semantic diff, approves the new graph version, and the affected open cases are re-queued.

---

## 6. Success metrics

Measured on the Assent benchmark (see BUILD_PLAN.md §3). Fill in real numbers only after running them.

| Metric | Definition | Target | Measured (ESI dev, 34 cases, 2026-10-12) |
|---|---|---|---|
| Criterion-level F1 | Leaf verdicts vs. gold labels | ≥ 0.90 | **0.858** macro (accuracy 0.927) |
| Case decision accuracy | Final ready / not-ready vs. gold | ≥ 90% | **76%**, with 0 false "ready" and 8 false "not ready" |
| Citation precision | Quotes that exist verbatim and are entailed | ≥ 98% | **82%** of cited quotes pass verbatim + grounding |
| Unsupported-claim rate | Verdicts with no valid evidence | ≤ 1% | **0%** (enforced: 11.6% of claims downgraded to `insufficient`) |
| Adversary catch rate | Seeded defects found by the Payer Adversary | ≥ 85% | **100%** of 60 seeded defects (weak / wrong-criterion / no quote), all high severity; but **3.1 objections per clean packet** (over-eager) |
| Time to packet | p50 / p95 end-to-end latency | < 60s / < 120s | **59 s / 96 s** (CPU laptop, local models) |
| Cost per case | All model calls | < $0.15 | **$0.093** |
| Lift vs. baseline | vs. single long-context prompt and naive RAG | Report it, whatever it is | 9 same cases: Assent F1 **0.917** vs long-context 0.766; but long-context decided all 9 correctly (Assent 7/9) while **28% of its claims had no valid citation** (Assent 0%). Naive RAG not run (budget). |

**Phase 5, all three families (dev, 2026-10-12).** Trimmed for cost: HGNS and PVA 12 dev cases each. "v2" = after two fixes (contraindication evidence must actually rule contraindications out; family-specific search hints).

| Family | Cases | Decisions correct (v1 → v2) | False ready (v1 → v2) | Criterion misses (v1 → v2) | Citation precision | Unsupported |
|---|---|---|---|---|---|---|
| ESI | 34 | 76% | 0 | — | 82% | 0% |
| HGNS | 12 | 8 → **9** | 0 → 0 | 19 → 19 | 85% | 0% |
| PVA | 12 | 9 → 9 | **2 → 0** | 10 → 12 | 91% | 0% |

The criterion macro-F1 on 12 cases is unstable (HGNS 0.58 → 0.36 with the same number of misses, because the rare `not_met` class dominates the average); report misses and decisions instead until the test split runs. Real cost per case is $0.06–0.09; v2 logs look cheaper only because recorded calls replayed.

Injection: 4 attacked not-ready cases (ESI and HGNS), 0 decisions flipped and 0 criteria wrongly met, including 1 attack the keyword screen missed. Risk model (logistic regression, 24 v1 HGNS+PVA dev cases, 5-fold CV): Brier 0.210 / AUC 0.748 / ECE 0.154, against the hand prior's 0.231 / 0.699 / 0.151. **The locked test split has not been run yet** (stopped twice for low memory: 2 of 18 cases done).

Setup: gpt-4.1 evidence agents, gpt-4.1-mini judge, local bge-small / MiniLM rerank / DeBERTa-v3-base NLI, verifier = verbatim + sentence-window NLI + judge on `met` only. Raw logs are in `data/bench/results/openai-dev-judge-met.jsonl`. The test split is still locked. Known gap: the errors are conservative (`met` → `insufficient`), clustered on rehab, contraindication and baseline-scale criteria.

---

## 7. Principles

1. **No claim without a citation.** If Assent cannot point to it, Assent does not say it.
2. **Deterministic where possible, probabilistic where necessary.** LLMs judge evidence. Code combines the verdicts.
3. **Humans decide.** Assent prepares and argues. It never submits on its own.
4. **Standards first.** FHIR R4, CDS Hooks, Da Vinci CRD/DTR/PAS patterns, so the work transfers to real systems.
5. **Synthetic data only.** No real PHI touches this project. The architecture is built HIPAA-aligned (de-identification, audit logging, RBAC, encryption), but the project does not claim to be HIPAA compliant.

---

## 8. Non-goals

- Replacing clinical judgment or making medical necessity decisions.
- Automatically submitting without review.
- Building a payer-side auto-denial tool.

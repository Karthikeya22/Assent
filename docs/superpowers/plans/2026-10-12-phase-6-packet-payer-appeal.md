# Phase 6: Packet, Payer, Appeal, CDS (BUILD_PLAN "Phase 4: Packet, payer, appeal")

**Goal:** the full loop, live: EHR order → CDS card → case run → packet (PAS Bundle + PDF) → human approval → submit to the Mock Payer → denial → appeal agent drafts a cited letter → resubmit → approval.

## Lean substitutions (7 GB laptop)
- PDF: **fpdf2** (pure Python) instead of WeasyPrint (needs GTK on Windows).
- Validation: `validate_pas()` checks the PAS elements we rely on, with unit tests. shortcut: swap in HAPI `$validate` at deploy.
- Cover letter: templated from verified citations ($0, deterministic). The appeal letter is LLM-drafted and citation-verified.
- Editor: textarea + live citation chips instead of Tiptap.

## Tasks
1. `assent_fhir.pas`: `build_pas_bundle()` (Bundle with Claim use=preauthorization, Patient, Coverage, provider Organization, one DocumentReference per verified citation, linked through `Claim.supportingInfo`) + `validate_pas()`. Tests.
2. `assent_api.services.packets`: build from the latest run (only verified citations), PDF render, approve (role-gated, audited).
3. `apps/mock_payer` (FastAPI :8020): `POST /fhir/Claim/$submit` → ClaimResponse (approved / denied with reason code + text / pended), `GET /fhir/ClaimResponse/{id}`, `PUT /admin/rules`. The hidden rules demand documentation per service family; deterministic so the demo is reproducible.
4. API: `POST /runs/{id}/packet`, `GET /packets/{id}[?format=pdf]`, `POST /packets/{id}/approve`, `POST /packets/{id}/submit`, `GET /submissions/{id}`, `POST /submissions/{id}/appeal`, `GET/PATCH /appeals/{id}`, `POST /appeals/{id}/send`.
5. `assent_agents.appeal`: denial → criteria → targeted re-search → drafted letter (LLM) → citations verified; unverified quotes are dropped.
6. `apps/cds` (FastAPI :8010): discovery + `assent-order-sign` (CPT → family → criteria checklist card; readiness + gaps if the patient has a case; link to open it).
7. Web: Packet panel in the Case Workspace (build / approve / submit / payer response / appeal editor with chips) and `/ehr-sim`.
8. Exit check: the full loop in the browser on one case.

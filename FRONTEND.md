# Assent: Frontend Specification

The goal is a product that looks like it came from a funded health-tech company, not an AI template. Everything here is specific on purpose: if a choice is left vague, the result defaults to generic.

---

## 1. Design direction: "Clinical Editorial × Instrument Panel"

Assent sits between a medical journal and a flight instrument. The marketing site reads like a well-set editorial (serif display type, generous margins, real numbers with sources). The product reads like an instrument: dense, calm, precise, every pixel carrying state.

**Banned (AI slop tells):**
- Purple/blue gradients, glowing blobs, glassmorphism cards everywhere
- Emoji icons, a "✨ AI-powered" badge, sparkles
- Three identical feature cards with an icon on top
- Generic stock illustrations of doctors holding tablets
- Fake testimonials and fake customer logos
- Motion that means nothing (things floating for no reason)

**Rules:**
- **Motion must mean something.** Every animation shows real system state: evidence moving, a criterion resolving, a clock running down.
- **One accent color does the talking.** Status colors appear only on status.
- **Typography does the hierarchy**, not boxes and borders.
- **Real numbers or none.** Every stat has a source footnote.

---

## 2. Design tokens

### 2.1 Color
Paper and ink, with one signal color. Define these as CSS variables in `globals.css` and map them in the Tailwind v4 `@theme` block.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#F6F4EF` | `#0E1012` | page background (warm, not pure white) |
| `--paper-raised` | `#FFFFFF` | `#16191C` | panels |
| `--ink` | `#14171A` | `#E9E7E2` | primary text |
| `--ink-2` | `#4A5058` | `#A4A9AF` | secondary text |
| `--ink-3` | `#8A9097` | `#6B7178` | tertiary, axes |
| `--rule` | `#E2DED6` | `#24282C` | hairlines (1px) |
| `--signal` | `#0F6E5C` | `#3FBF9F` | brand + "met" (deep clinical teal-green) |
| `--signal-soft` | `#DCEFEA` | `#123A32` | met backgrounds |
| `--gap` | `#B26B00` | `#F0A93B` | insufficient / needs docs (amber) |
| `--fail` | `#B3261E` | `#F2766B` | not met / denial |
| `--adversary` | `#5B3FA8` | `#A992F0` | Payer Adversary voice only |
| `--focus` | `#1F5FD1` | `#7AA8FF` | focus rings |

The adversary gets its own hue so that the "two agents arguing" concept is readable at a glance. It is the only place purple appears.

### 2.2 Typography
| Role | Font | Notes |
|---|---|---|
| Display (marketing H1/H2, case titles) | **Instrument Serif** (Google Fonts) | Editorial and confident. Tracking −1% |
| UI + body | **Geist Sans** | Neutral and very legible at 13 to 14px in dense UI |
| Data, codes, quotes | **Geist Mono** | CPT, ICD-10, LCD IDs, timestamps, token counts |

Type scale (rem): 0.75 / 0.8125 / 0.875 / 1 / 1.25 / 1.75 / 2.5 / 4 / 6 (hero). Use tabular numbers everywhere numbers change (`font-variant-numeric: tabular-nums`).

### 2.3 Space, radius, elevation
- 4px base grid. The app uses 8/12/16 rhythm, marketing uses 24/48/96/160.
- Radius: 6px for controls, 10px for panels. No pill-shaped cards.
- Elevation: hairline borders instead of shadows. One shadow only, for floating layers (command palette, popovers): `0 12px 32px -12px rgb(0 0 0 / .25)`.

### 2.4 Motion tokens
| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(.2,.8,.2,1)` | entrances |
| `--ease-inout` | `cubic-bezier(.65,0,.35,1)` | camera moves, morphs |
| `dur-1` | 120ms | hovers, toggles |
| `dur-2` | 220ms | panels, popovers |
| `dur-3` | 420ms | state resolutions (criterion turns green) |
| `dur-4` | 900ms+ | scroll-scrubbed 3D only |
| spring | `{ stiffness: 380, damping: 32 }` | layout shifts (Motion) |

`prefers-reduced-motion`: all 3D scenes swap to a pre-rendered still, scroll-scrubbing is off, and state changes become color changes only.

---

## 3. Tech stack (frontend)

| Concern | Choice |
|---|---|
| Framework | **Next.js 15 (App Router, React 19, Server Components, Server Actions)**, TypeScript strict |
| Styling | Tailwind CSS v4 + CSS variables. shadcn/ui only as unstyled primitives (Radix), restyled to the tokens |
| 3D | **React Three Fiber + drei**, custom GLSL shaders, `@react-three/postprocessing` (subtle bloom + noise only) |
| Scroll motion | **GSAP + ScrollTrigger**, **Lenis** smooth scroll (marketing only, never in the app) |
| UI motion | **Motion** (formerly Framer Motion): layout animations, AnimatePresence |
| Graph | **React Flow (xyflow)** with custom nodes + **ELK.js** auto-layout for criteria trees |
| Data | **TanStack Query v5** (server state), **Zustand** (UI state), native `EventSource` for SSE |
| Tables | **TanStack Table v8** + virtualization (`@tanstack/react-virtual`) |
| Charts | **visx** (custom, on-brand), not a default chart library look |
| Forms | React Hook Form + Zod (schemas shared from an OpenAPI-generated client) |
| API client | `openapi-typescript` + `openapi-fetch`, generated from FastAPI's OpenAPI spec |
| Command palette | `cmdk` |
| Auth | Auth.js (credentials + GitHub for the demo), JWT forwarded to FastAPI |
| Testing | Vitest + Testing Library, **Playwright** E2E + visual snapshots, Storybook for components |
| Quality | Lighthouse CI budget: LCP < 2.0s, CLS < 0.05, landing JS before 3D < 160KB gz |

---

## 4. Information architecture

```
/                         Landing (marketing)
/how-it-works             Long-form scrollytelling explainer
/evals                    Public benchmark page (live from /public/evals/latest)
/standards                FHIR, CDS Hooks, Da Vinci explainer
/demo                     No-login live demo on a fixed synthetic case
/login

/app                      → redirects to /app/worklist
/app/worklist             Coordinator inbox
/app/cases/new            Create case
/app/cases/[id]           Case Workspace (the core screen)
/app/cases/[id]/trace     Full agent trace
/app/cases/[id]/packet    Packet preview + approve/submit
/app/cases/[id]/appeal    Appeal editor
/app/policies             Policy library
/app/policies/[id]        Criteria graph editor
/app/policies/[id]/diff   Version diff
/app/analytics            Denials, throughput, SLA
/app/evals                Internal eval runs (MLflow-backed)
/app/audit                Audit log
/app/settings             Org, users, model config (read-only view of LiteLLM routing)
/ehr-sim                  Fake EHR order screen that fires CDS Hooks (for demoing the clinician flow)
```

---

## 5. Marketing site

### 5.1 Landing page, section by section

**Nav (sticky, 64px).** Wordmark "Assent" in Instrument Serif. Links: How it works, Evals, Standards. Right: "Live demo" (ghost) and "Sign in". On scroll the nav gets a 1px `--rule` bottom border and a paper-colored background at 85% opacity with an 8px blur. That is the only blur on the site.

**Section 1: Hero, "The Evidence Lattice" (3D, full viewport).**
- *Left column (5/12):* eyebrow in mono `WISeR · CMS-0057-F · 2026`. H1 in serif at 6rem: "Prior authorization, *argued with evidence.*" (italic on the second line). Sub (ink-2, 1.25rem): "Assent reads the chart, proves every Medicare coverage criterion with a cited sentence, and stress-tests the packet against a simulated payer before you hit submit." CTAs: **Run a live case** (solid signal) and **See the benchmark** (text link with an arrow).
- *Right column (7/12): the 3D scene.*
  - **Left of the scene:** a loose stack of 12 translucent "chart pages" (instanced planes with a procedural line-texture shader that looks like text lines), slightly fanned, rotating very slowly.
  - **Right of the scene:** the **criteria graph** as a 3D constellation. Leaf nodes are small icosahedrons. AND/OR nodes are rings. Edges are thin tubes. The final node is a larger ring labeled in mono `L39240`.
  - **Animation loop (10s):** a page highlights one line (the shader brightens one row). The line lifts off as a particle ribbon of about 400 instanced points that travels along a CatmullRom curve to a leaf node. The leaf goes from grey wire to a solid `--signal`, with a short ring pulse. Logic flows upward: the parent ring fills clockwise. One leaf receives nothing and turns amber, and a tiny mono label floats beside it: `insufficient · PT duration`. Then a purple "adversary" ray sweeps across the graph like a scanner and stops on the amber node. Loop.
  - **Interaction:** pointer-move parallax (±4° camera). Hovering a node shows its criterion label in an HTML overlay (drei `<Html>`).
  - **Scroll:** as the user scrolls past the hero, the camera dollies into the graph and the scene hands off to Section 3.
  - **Tech:** one `<Canvas>`, `dpr={[1, 1.75]}`, `frameloop="demand"` when offscreen (IntersectionObserver), instanced meshes, all geometry procedural (no GLB downloads), and a `<Suspense>` poster image as fallback. Lazy-loaded with `next/dynamic({ ssr:false })` after first paint.

**Section 2: The problem, as a ledger.** No cards. A full-width, editorial ledger: three huge serif numbers in a row with hairline dividers. `40` prior auths per physician, per week. `13` hours of staff time, every week. `95%` of physicians say it delays care. Numbers count up once on enter (GSAP, 900ms, tabular nums). Superscript footnote markers link to sources at the page bottom. Under them, one line in ink-2: "And since January 2026, Original Medicare requires prior authorization for 13 service families in six states."

**Section 3: How it reads a chart (pinned scrollytelling, 5 steps).** The 3D graph from the hero stays pinned on the right while the text steps scroll on the left. Each step moves the camera and changes the scene:
1. *Compile the policy.* Policy paragraph text (rendered as a 2D overlay) splits apart, and each clause flies into place as a node. The tree builds itself.
2. *Read the chart.* The chart pages fan out into a timeline along the x-axis by date.
3. *Prove each criterion.* Several particle ribbons at once (the parallel fan-out). Each lands with a verdict.
4. *Verify every citation.* One ribbon is rejected: it flickers red, snaps back, and the node turns amber. Caption: "Quote not found verbatim. Downgraded."
5. *Argue with the payer.* Camera pulls back. Purple rays hit two nodes. One is defended (a teal counter-ray, purple fades). One is conceded and becomes a gap task card that slides out in 2D.

Implementation: a single GSAP timeline bound to ScrollTrigger `scrub: 0.6`. The timeline writes to a Zustand store (`progress`, `step`) that the R3F scene reads in `useFrame`. Never animate R3F through React state each frame.

**Section 4: The glass box (interactive 2D).** A real-looking synthetic progress note on the left, set in Geist Mono at 13px on paper-raised. On the right, five criteria rows. Hovering a criterion highlights its exact quoted span in the note (a `--signal-soft` mark that animates its width from 0, 220ms). The amber row shows "No evidence found" and a "Create task" button. Caption: "No claim without a citation. Hover any criterion."

**Section 5: Two agents, one packet.** A split conversation. On the left, Advocate messages (ink). On the right, Payer Adversary messages (adversary purple, with a thin left rule). They type in with real token-streaming cadence (from a recorded run JSON, not lorem). Each message ends in a status chip: `rebutted` / `conceded`. At the end a Denial Risk dial settles at 18%.

**Section 6: Built on the standards payers must adopt.** A horizontal timeline: `Jan 2026, CMS-0057-F decision timeframes` → `Jan 2026, WISeR begins` → `Jan 2027, FHIR Prior Authorization API required`. Below it, four mono tags with one-line explanations: `HL7 FHIR R4`, `CDS Hooks`, `Da Vinci CRD · DTR · PAS`, `SMART on FHIR`. Text only, no fake logos.

**Section 7: Benchmark preview.** A compact visx bar chart comparing Assent, naive RAG and a long-context single prompt on criterion F1, citation precision and cost per case. The data comes from `/public/evals/latest` at build time (ISR, revalidate hourly). Link to /evals.

**Section 8: Architecture.** An SVG diagram of the services that draws itself on enter (stroke-dashoffset animation, 1.2s, staggered). Hover a service to see its tech in a tooltip.

**Section 9: Closing CTA.** A big serif line: "See it work on a real chart." Button: Run a live case. Under it in small text: "Synthetic patients only. No PHI."

**Footer:** sources list, GitHub, author, "Built by Karthikeya Moturi".

### 5.2 /demo (no login)
A single-page version of the Case Workspace, locked to one synthetic patient ("R. Alvarez, 67, lumbar radiculopathy, ESI ordered"). Clicking "Run" calls `/public/demo/run` and streams real SSE events. This is the most important page for recruiters, so it must load in under 2 seconds and work on a laptop without a GPU.

### 5.3 /evals
Editorial report layout: method, dataset, metrics table, per-service breakdown, confusion matrices (visx heatmap), cost/latency scatter, and an honest "Where it fails" section with 3 real failure examples. Recruiters remember honesty.

---

## 6. Product app

### 6.1 App shell
- **Left rail (56px, expandable to 220px):** Worklist, Policies, Analytics, Evals, Audit, Settings. Icons are Lucide at 1.5px stroke. The active item gets a 2px signal bar.
- **Top bar (48px):** breadcrumb (serif for the case name, mono for the IDs), a global search trigger (`⌘K`), an environment badge `SYNTHETIC DATA` in amber mono, and the user menu.
- **Command palette (`⌘K`):** jump to a case by patient or ID, run actions ("Re-run evidence", "Build packet"), and switch policy.
- **Keyboard first:** `J/K` move through the worklist, `Enter` opens a case, `G then P` goes to policies, `?` shows the shortcuts sheet.

### 6.2 Worklist (`/app/worklist`)
A dense table, 40px rows, virtualized.

| Column | Detail |
|---|---|
| SLA | **Live countdown ring** (SVG). Teal while more than 50% of time remains, amber under 50%, red under 10%. The text is mono `41h 12m`. Expedited cases show a small `EXP` tag. |
| Patient | Synthetic name + age/sex in ink-2 |
| Service | Service family + CPT in mono |
| Policy | LCD ID chip |
| Readiness | A segmented bar, one segment per leaf criterion, colored by verdict. You can read the case at a glance. |
| Risk | Denial risk % with a tiny sparkline across runs |
| Status | Text status with a colored dot |
| Assignee | Avatar initials |

Top: saved views as tabs (My queue · Needs review · Expiring < 24h · Denied). Filters render as removable chips. Multi-select supports bulk assign and bulk re-run.

When a running case finishes, its row gets a 600ms signal-soft background flash and the readiness bar segments fill left to right (staggered 40ms). Data arrives via a worklist-level SSE channel.

### 6.3 Case Workspace (`/app/cases/[id]`): the core screen

Three resizable panes (`react-resizable-panels`) and a bottom drawer.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ R. Alvarez · 67 M      ESI · CPT 62323 · LCD L39240        SLA ◔ 41h 12m     │
│ Readiness ▮▮▮▮▯ 80%   Denial risk 22%    [Re-run] [Build packet ▸]          │
├───────────────────┬──────────────────────────────────┬───────────────────────┤
│ CHART             │ CRITERIA GRAPH          [2D|3D]  │ DECISION              │
│ ▸ Timeline        │                                  │ Readiness dial        │
│   2026-08 PT note │      ┌─(AND) L39240 ─┐           │ Gaps (1)              │
│   2026-07 MRI     │   ┌──┴──┐  ┌──┴──┐  ┌┴──┐        │  ▸ PT duration ...    │
│   2026-06 Ortho   │   ●met  ●met ◐ins  ●met          │ Payer objections (2)  │
│ ▸ Note viewer     │                                  │  ▸ rebutted           │
│   ...highlighted  │  (click node → evidence card)    │  ▸ conceded → task    │
│   quote...        │                                  │ [Approve for packet]  │
├───────────────────┴──────────────────────────────────┴───────────────────────┤
│ ▾ AGENT TRACE  intake ✓ · policy ✓ · chart ✓ · evidence 5/5 ✓ · verify ✓ ...  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Header.** Patient name in serif at 1.5rem. Service, CPT and LCD in mono chips. The SLA ring is large here. The readiness bar and risk number update live during a run.

**Left pane: Chart.**
- *Timeline:* a vertical list of FHIR resources grouped by month. Each item has a type glyph (note, lab, imaging, med, procedure). Items that were cited by any verdict carry a small teal tick, so you can see which parts of the chart the agent used.
- *Note viewer:* de-identified note text in Geist Mono at 13px, line height 1.6. Cited spans are highlighted. Hovering a span shows which criteria it supports. Surrogate PHI tokens (`[NAME_1]`) are styled as subtle mono pills, so the de-identification is visible.

**Center pane: Criteria Graph.**
- *2D mode (default):* React Flow + ELK top-down layout. Custom node types:
  - `LeafNode`: 240px card with the criterion label, an evidence-type glyph, a verdict chip and a confidence bar. The border color follows the verdict. Insufficient nodes get a dashed amber border.
  - `LogicNode`: a compact pill reading `AND`, `OR` or `2 of 3` in mono, with a progress ring showing how many children are satisfied.
  - `RootNode`: the policy ID and title in serif, plus the overall decision.
- *Live run behavior (driven by SSE):*
  - `node_started` on a leaf: the node gets a rotating dashed outline (a CSS conic-gradient spin, not JS).
  - `retrieval`: small chips fly from the left pane's timeline items to the node. These are shared-element transitions done with Motion `layoutId` across panes.
  - `verdict`: the node resolves with a 420ms color fill from the bottom up, the confidence bar animates, and the chip text cross-fades.
  - `logic_update`: the edge to the parent draws in signal color (an animated stroke), and the parent ring progresses.
  - `objection`: a purple marker pins onto the node with a subtle pulse until it is rebutted (it fades) or conceded (the node goes amber).
- *3D mode (toggle):* the same graph rendered in R3F, using the landing page's visual language, with orbit controls. It is mostly for demos and screenshots, and it shows that the 3D is a real component of the product and not only marketing.
- *Click a node* to open an **Evidence Card** popover: the verdict, rationale, every citation (quote, source resource, date, entailment score as a small meter), the policy text for that criterion, and an **Override** action (pick a verdict, a required reason, and it is saved to the audit log).

**Right pane: Decision.**
- *Readiness dial:* a 270° arc gauge made in visx with a needle that settles with a spring. The center number is in serif.
- *Denial Risk:* a number plus the top three contributing factors as a horizontal waterfall.
- *Gaps:* task cards with a policy citation, an assignee role and a "Send to clinician" action.
- *Payer objections:* a thread view. Each objection is in adversary purple, the Advocate's rebuttal sits underneath in ink, and the status chip says rebutted or conceded.
- *Primary action:* **Approve for packet**. It is disabled until there are no open high-severity objections, or the user acknowledges them in a confirm dialog.

**Bottom drawer: Agent Trace.**
- Collapsed, it is a one-line horizontal stepper of graph nodes with check marks and timings.
- Expanded (drag up), it is a Gantt-style timeline: one bar per node, with the parallel evidence agents stacked as lanes. Hovering a bar shows the model, prompt version, tokens, cost and latency. "Open in Langfuse" links out.
- A run total in mono: `48.2s · 31,420 tok · $0.083`.

### 6.4 Packet (`/app/cases/[id]/packet`)
Two tabs: **Letter** (PDF preview rendered in an iframe from the API, with the citations as numbered footnotes) and **FHIR Bundle** (a collapsible JSON tree with syntax colors from the tokens, plus a copy button). The right rail has a checklist of all criteria with their citation counts. Buttons: Approve, then Submit to payer. After submitting, a status timeline shows Submitted → Pended → Decision, with the live payer response.

### 6.5 Appeal editor (`/app/cases/[id]/appeal`)
At the top, the denial reason from the `ClaimResponse` is shown verbatim in a red-ruled block. Below it is a split view: the draft letter in a rich text editor (Tiptap) on the left, and the evidence used on the right. Every citation in the letter is an inline chip that you can hover to see the source span. A "Verify citations" button re-runs the verifier and flags any edited claim that lost its support.

### 6.6 Policy library and editor (`/app/policies/[id]`)
- *Left:* the LCD text with each clause highlighted in the color of the criterion it compiled into.
- *Right:* the editable criteria tree (React Flow in edit mode: drag to reparent, edit thresholds in a side sheet).
- *Version bar:* draft or approved, effective date, Approve button (policy_admin only).
- *Diff view:* side-by-side trees, with added nodes in signal, removed nodes in fail (struck through) and changed thresholds as an inline `6 → 4 weeks` in mono. A text diff of the source LCD is shown below.

### 6.7 Analytics (`/app/analytics`)
visx charts in the house style (hairline axes in `--ink-3`, no gridlines except the baseline, direct labels instead of legends):
- Denials by reason × service (heatmap)
- Time to packet distribution (histogram with p50/p95 markers)
- SLA breaches over time (line)
- Override rate by criterion (bar). This is where policy-graph weaknesses show up.

### 6.8 EHR simulator (`/ehr-sim`)
A deliberately "old EHR"-looking order screen (grey, dense, system font), so the contrast makes Assent's CDS card stand out. Signing an order fires `order-sign`, and the CDS card slides in from the right with the gap checklist and an "Open in Assent" link.

---

## 7. Component inventory

`AppShell`, `RailNav`, `CommandPalette`, `SlaRing`, `ReadinessBar`, `ReadinessDial`, `RiskWaterfall`, `VerdictChip`, `ConfidenceMeter`, `EntailmentMeter`, `CriteriaGraph2D` (+ `LeafNode`, `LogicNode`, `RootNode`, `AnimatedEdge`), `CriteriaGraph3D`, `EvidenceCard`, `OverrideDialog`, `ChartTimeline`, `NoteViewer` (span highlighting, PHI pills), `ObjectionThread`, `GapTaskCard`, `TraceStepper`, `TraceGantt`, `FhirJsonTree`, `PolicyClauseText`, `PolicyDiff`, `CdsCard`, `MonoChip`, `SerifStat`, `Footnote`, `EvidenceLattice` (landing 3D), `ScrollStage` (GSAP pin controller), `AgentDuel` (landing section 5), `ArchitectureDiagram`.

Each component gets a Storybook story with light/dark and a "live run" mock that replays a recorded SSE log, so any state can be shown without a backend.

---

## 8. Frontend architecture

```
apps/web/
  app/
    (marketing)/page.tsx, how-it-works/, evals/, standards/, demo/
    (app)/app/layout.tsx           # AppShell, auth guard
    (app)/app/worklist/page.tsx
    (app)/app/cases/[id]/page.tsx  # server component: fetch case; client islands for panes
    api/auth/[...nextauth]/route.ts
  components/
    three/ EvidenceLattice.tsx, CriteriaGraph3D.tsx, shaders/{pages.glsl, ribbon.glsl}
    graph/ CriteriaGraph2D.tsx, nodes/*, elkLayout.ts
    case/  ChartPane, DecisionPane, TraceDrawer, EvidenceCard
    ui/    (restyled Radix primitives)
  lib/
    api/ client.ts (openapi-fetch), schema.d.ts (generated)
    sse/ useRunStream.ts         # EventSource + reconnect + event reducer
    store/ runStore.ts (Zustand), scrollStore.ts
    motion/ tokens.ts
  styles/ globals.css (tokens)
```

**The `useRunStream` pattern.** One reducer turns SSE events into a normalized run state: `nodes[criterionId] = {status, verdict, citations, objections}`. React Flow nodes subscribe to their own slice through a Zustand selector, so a verdict re-renders one node and not the whole graph. Recorded runs (`/fixtures/run_*.jsonl`) can be replayed through the same reducer, which powers the demo, Storybook and Playwright tests.

---

## 9. Accessibility
- WCAG 2.2 AA contrast for all tokens (check with a script in CI).
- Verdicts never rely on color alone: each has a glyph (✓, ○, ✕) plus text.
- The criteria graph has a "List view" alternative with the same data in a semantic table.
- Every 3D scene is `aria-hidden` and has a text equivalent next to it.
- Focus rings use `--focus`, 2px offset. Every interactive element is reachable by keyboard.

---

## 10. Build order for the frontend
1. Tokens + type + `AppShell` + Storybook
2. Worklist with mock data
3. Case Workspace with replayed SSE fixtures (fully working before the backend is ready)
4. Wire to the real API + SSE
5. Packet, Appeal and Policy screens
6. Landing page without 3D (layout, copy, sections)
7. `EvidenceLattice` hero, then the pinned ScrollTrigger story
8. /demo, /evals, Lighthouse + Playwright visual tests

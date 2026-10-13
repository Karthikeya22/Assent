# Landing storyboard: one world, eleven beats

**Rules:**
- One fixed R3F canvas, flown by Lenis scroll.
- The DOM text for a chapter sits in a glass panel or on clear porcelain, alternating sides. Text is still once in place.
- Every number comes from `sources.ts` or `public/evals/latest.json`.
- No em-dashes, numbered eyebrows or scroll cues.
- `P` is the poster used for reduced motion, no WebGL and the low tier: a still render of that chapter's resting frame.

**Assets** (img2threejs, porcelain style):
- **A** chart folder
- **B** magnifier
- **C** balance scales
- **D** wax-seal stamp
- **Procedural** (no reference needed): instanced paper sheets, lattice nodes, threads, rays, dials.

---

### 0 · Hero (100dvh, text left)
- **Copy:**
  - "Prior authorization, argued with evidence."
  - Sub (18 words): "Assent proves every Medicare coverage criterion with a cited sentence from the chart, before the payer sees it."
  - CTAs: **Run a live case** · See the benchmark
  - Eyebrow (1 of 3): `WISeR · CMS-0057-F · 2026`
- **World:**
  - Folder A floats right of centre, half open, with 5 pages hovering out of it in a loose fan.
  - Slow idle bob of about 2 cm over 6 s.
  - Light: key from top-left, a soft rim, and a contact shadow.
- **Cursor:** the folder yaws and pitches toward the pointer (±12°, damped). Pages near the pointer drift away by up to 4 cm and settle back.
- **Load:** the poster paints first (the LCP). The scene fades in over it once it's ready.

### 1 · The problem (text centred over the scene, the only centred chapter)
- **Copy:** big tabular numbers, rendered as real numbers in the HTML.
  - **40** prior authorizations per physician, per week¹
  - **13** hours of physician and staff time, every week¹
  - **95%** of physicians say it delays access to necessary care¹
  - Then: "And since January 2026, Original Medicare's WISeR model requires prior authorization or pre-payment review in six states², including all three services Assent covers³."
- **World:** the camera tilts down. About 300 instanced form sheets fall and pile into slow drifts around the folder (physics-lite: precomputed paths). The pile grows with scroll progress.
- **Cursor:** sheets within 15 cm of the pointer slide aside.

### 2 · Compile the policy (text left)
- **Copy:** "**Compile the policy.** The coverage policy (LCD L39240 for epidural steroid injections) becomes a typed AND/OR tree of atomic criteria. Every node keeps the exact sentence it came from."
- **World:** one frosted-glass policy sheet lifts out of the pile. Its lines detach and fold up into the criteria lattice (`layout.ts`), drawn as porcelain nodes on hairline glass edges.
- **Cursor:** hovering a node raises it and shows its source sentence as a DOM tooltip projected beside it. The tooltip is keyboard-reachable through a list fallback.

### 3 · Read the chart (text right)
- **Copy:** "**Read the chart.** Notes, imaging, procedures and medications are de-identified, split into passages and laid on a timeline, so recency and duration can be reasoned about."
- **World:** folder A opens fully. Its pages fly out and line up on a dated timeline ribbon under the lattice, with date ticks in mono.
- **Cursor:** depth parallax on the ribbon.

### 4 · Prove each criterion (text left)
- **Copy:** "**Prove each criterion.** One evidence agent per criterion searches the chart in parallel and answers met, not met or insufficient, quoting the sentence that proves it."
- **World:** signal-green threads run from highlighted passages to lattice leaves, and the leaves fill green one by one. This reuses the `timeline.ts` ribbons and leaves logic.
- **Cursor:** magnifier B follows the pointer above the timeline. Under it, the passage text renders at 2× through a lens refraction material.

### 5 · Verify every citation (text right)
- **Copy:** "**Verify every citation.** Each quote must exist verbatim and support its claim. This one does not. It is rejected, and the criterion drops to insufficient instead of being guessed."
- **World:** one thread flickers, snaps red and frays. Its leaf cools from green to amber. A brief red glint is the only red in the film.
- **Cursor:** none, because this is a moment to watch.

### 6 · Argue with the payer (text left, with the transcript)
- **Copy:** "**Argue with the payer.** A payer adversary from a different model vendor attacks the packet. The advocate answers with new citations or concedes, and every concession becomes a task for a human."
- The recorded transcript from `agents-run.json` is rendered complete in the HTML and played in once.
- **World:** scales C rise behind the lattice. Purple adversary rays strike leaves, and the pan dips. Green rebuttal threads answer, and the pan rights itself. The one conceded objection drops an amber gap card into the DOM.
- **Cursor:** the scales sway slightly toward the pointer.

### 7 · Packet and submit (text right)
- **Copy:** "**Submit a packet that holds.** Assent builds a Da Vinci PAS bundle and a cited letter. A human approves. If the payer denies, it searches the chart again and drafts the appeal."
- **World:** the pages compress into a sealed packet. Stamp D comes down with a soft squash, leaving a green wax seal. The packet slides off toward a distant payer plane and returns with an approval tag.
- **Cursor:** the stamp tilts toward the pointer before it presses.

### 8 · How you use it (three beats in sequence, text alternating)
1. "**Sign the order.** In the EHR, a CDS Hooks card tells the clinician prior auth is required and what is still missing."
2. "**Review the case.** The coordinator sees every criterion, its quote and its source, and closes the gaps Assent found."
3. "**Approve and send.** One approval builds the packet. Status, denials and appeals come back to the same worklist."

- **World:** three floating curved screen planes textured with real screenshots of `/ehr-sim`, the case workspace and the worklist. They're captured from the running app, not built from divs. The camera glides plane to plane.
- **Cursor:** the planes tilt and parallax.

### 9 · Proof (text left; the numbers are the content)
- **Copy:** "**Measured, not claimed.**" Then four figures in tabular mono: **16 / 18** decisions correct · **0** unproven cases marked ready · **0%** unsupported claims · **$0.079** per case. The line after is "On a locked test split of 18 synthetic cases across three services." Link: See the benchmark.
- **World:** four porcelain dials rise from the floor and sweep to their values once, then hold. There are no bars or tracks.

### 10 · Close (centred)
- **Copy:** "See it work on a real chart." → **Run a live case**. Small text: "Synthetic patients only. No PHI."
- **World:** the sealed packet rests on porcelain under a soft spotlight. The folder, scales and stamp sit in the background like a still life.
- **Cursor:** gentle tilt.

### Footer
Sources 1–4 (kept verbatim), "Built by Karthikeya Moturi", Benchmark, and "Synthetic patients only. No PHI."

---

## Camera path (`camera.ts` keyframes, progress 0..1 split by measured chapter offsets)

| Ch | Position (x, y, z) | Look at | Note |
|---|---|---|---|
| 0 | (1.2, 0.6, 5.5) | folder | hero three-quarter view |
| 1 | (0, 3.2, 6.5) | the pile | tilt down |
| 2 | (-0.5, 1.4, 4.2) | lattice | |
| 3 | (0.4, 0.2, 4.6) | ribbon | |
| 4 | (0, 0.6, 3.6) | leaves | close |
| 5 | (0.8, 0.9, 2.6) | the weak leaf | push in |
| 6 | (-1.6, 1.2, 5.2) | scales + lattice | |
| 7 | (0.6, 0.4, 3.8) | packet | |
| 8 | (0, 0.8, 6.0) → lateral pans | screens | |
| 9 | (0, 2.0, 7.0) | dials | |
| 10 | (0, 0.9, 4.8) | packet | |

Values are the starting guesses; they get tuned visually in Phase E.

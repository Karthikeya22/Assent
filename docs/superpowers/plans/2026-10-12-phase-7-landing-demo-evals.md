# Phase 7: Landing (3D), /demo, /evals, deploy (BUILD_PLAN "Phase 6: Marketing site and launch")

Spec: FRONTEND §1, §2.4, §5. Rules: motion shows real system state; real numbers with sources or none; `prefers-reduced-motion` gets stills; landing JS before 3D < 160 KB gz; LCP < 2 s.

## Tasks
1. **Facts first.** Verify every landing stat (AMA survey, WISeR states and services, CMS-0057-F dates) against primary sources; footnote each one. Drop any we can't source.
2. **Landing shell** (server-rendered, no 3D): nav, hero copy + poster, ledger, glass box, two agents (recorded run JSON), standards timeline, benchmark preview (eval-table JSON), architecture SVG, CTA, footer with sources.
3. **EvidenceLattice** (R3F + drei, procedural geometry, instancing): chart pages → particle ribbon → leaf turns signal → parent ring fills → amber "insufficient" leaf → adversary sweep. `next/dynamic` with `ssr:false`, `frameloop="demand"` offscreen, reduced-motion still.
4. **Pinned scroll story** (GSAP ScrollTrigger scrub → Zustand progress → `useFrame`), 5 steps. Lenis on marketing pages only.
5. **/evals**: editorial report from `data/bench/results/eval-table-*.json` (dev + test, baselines, adversary, injection, risk, "Where it fails").
6. **/demo**: no login. Replays a real recorded run (`data/fixtures/run_*.jsonl`) through the same reducer and workspace components. Labelled as a replay. shortcut: a live public run needs a rate-limited endpoint and a deployed backend; add it at deploy.
7. **Quality**: Lighthouse budget check, reduced-motion check, phone width, review-animations pass.
8. **Deploy**: needs the user (GitHub repo + hosting accounts). Ask before creating anything.

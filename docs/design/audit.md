# UI audit (Phase A of the revamp, 2026-10-13)

**Sources:**
- `redesign-existing-projects` scan and diagnosis
- `impeccable audit` (5 dimensions) plus `npx impeccable detect`
- `web-design-guidelines` (vercel-labs, fetched 2026-10-13)
- Screenshots in `.data/screens/audit/`: the full landing page, /demo and /evals (live, Vercel), plus login, worklist and case (local)

Purpose: these findings are evidence for the revamp. The landing page is replaced wholesale (new world, see the plan), so landing findings say what the new build must *not* repeat. App findings are fixed during the restyle.

## Health score (impeccable)

| # | Dimension | Score | Key finding |
|---|---|---|---|
| 1 | Accessibility | 2 | `--ink-3` (#8a9097 on #f6f4ef) is **2.93:1** and carries text in 72 places. Amber `--gap` text is 3.82:1. There's no skip link. |
| 2 | Performance | 3 | Budgets met (landing 159 KB, ELK lazy). GSAP is loaded only for a counter and the scroll proxy. |
| 3 | Responsive | 3 | 390 px has no overflow (Phase 7). Nav links are under 44 px tall on touch. |
| 4 | Theming | 3 | The token system is complete in light and dark. `/ehr-sim` hard-codes 16 colours (intentionally "foreign EHR", but untokenised). |
| 5 | Implementation integrity | 3 | Coherent, product-specific system. Detector: 2 `side-tab` hits (`DecisionPane.tsx:368`, `PacketPanel.tsx:66`). |
| | **Total** | **14/20** | **Good**, with weak spots in a11y and in visual ambition |

## What the new landing must fix (design diagnosis)
1. **The page reads as empty.** The full-page capture is mostly blank paper. The pinned story shows text on the left and a small static lattice on the right, separated by 400 px gaps. The hero lattice sits at about 30% of the viewport, while the brief wants a 3D world that owns the screen.
2. **The 3D is a diagram, not an object.** The lattice is flat dots and lines with no materials, lighting or depth cues, and the only cursor response is a small camera drift. There is nothing tactile to play with.
3. **There's no "how you use it" chapter.** The story stops at "argue with the payer". The product flow (order sign in EHR → packet → approve) appears only as an architecture box grid.
4. **The architecture section is a box farm.** Eight identical white cards, and the connecting edges barely read. It's generic, and it's the weakest section.
5. **The Ledger counters render "0" until intersection.** A static capture, a crawler or a fast scroll can catch zeros. The new rule is static-frame-first: real numbers in the HTML, with animation that only plays them in.
6. **The two-agents transcript starts as an empty box with a caret.** That's also static-frame-last, so the same fix applies.
7. **There's no texture or depth on surfaces.** Everything is flat paper. Light tinted shadows, grain and a consistent single light source are all missing.
8. **Story headings for inactive steps go grey (`ink-3`).** That's low contrast, and it reads as disabled.

Keep:
- The voice and copy: plain, sourced and specific. The sources footnotes are a real differentiator.
- The type pairing: Instrument Serif display with Geist sans and mono. It has character. Revisit the weights only.
- The single signal green, plus the semantic gap amber, fail red and adversary purple. Colour already means something here.
- Lenis smooth scroll (required).
- The poster-first lazy 3D pattern and the budget discipline.

## App findings (fix in Phase H)
| Sev | Issue | Where | Fix |
|---|---|---|---|
| P1 | `ink-3` text below AA (2.93:1) | labels, timestamps and meta across the app | Darken the token to at least 4.5:1, or keep it for non-text only |
| P1 | Amber `gap` small text at 3.82:1 | GlassBox and DecisionPane "No evidence found" | A darker amber for text, keeping the bright one for fills |
| P1 | No skip link; focus styles only global | `app/layout.tsx` | Add a skip link, plus `focus-visible` rings on the custom controls |
| P2 | The case criteria pane is a blank canvas before a run | `CaseWorkspace` / `CriteriaGraph2D` | An empty state that previews the compiled tree in a "not run" style |
| P2 | Disabled "Approve for packet" reads as a washed-out primary | `DecisionPane` | A distinct disabled style, with the reason inline |
| P2 | Thick one-sided coloured borders (`border-l-2`) | `DecisionPane.tsx:368`, `PacketPanel.tsx:66` | A quieter accent: a tinted background or a leading glyph |
| P2 | Native scrollbar arrows in the chart list | `ChartPane` | Thin themed scrollbar |
| P3 | No `aria-live` on run progress or the toast-like updates | `DecisionPane`, `TraceStepper` | `aria-live="polite"` on the status text |
| P3 | Headings lack `text-wrap: balance` | everywhere | A global utility on `h1–h3` |
| P3 | `/ehr-sim` inline style colours | `EhrSim.tsx` | Leave them foreign on purpose, but move them to a local token block |

## Web Interface Guidelines (grep pass)
- **Clean:** no `transition: all`, no `outline-none`, no `<div onClick>`, no `...` strings, no raw `<img>`. `prefers-reduced-motion` is honoured in every motion file.
- **Missing:** a skip link, `text-wrap: balance` on headings, `aria-live` regions, `<meta name="theme-color">`, `autocomplete` on the ehr-sim inputs, and `touch-action: manipulation`.

## Positive findings
- A real token system (`globals.css`), consistent 4-state semantic colour, tabular numbers on data (20 uses).
- Reduced motion is designed for, not bolted on: posters plus static ledger.
- Lazy three.js and ELK keep first load at 159 KB.
- The copy is specific and sourced, with no AI clichés.

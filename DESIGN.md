---
name: Assent
description: Prior authorization, argued with evidence. A porcelain-and-signal-green clinical world, told in one continuous 3D scene.
colors:
  porcelain: "#f3f5f4"
  surface: "#fbfcfc"
  surface-sunk: "#e9edeb"
  rule: "#dbe1de"
  ink: "#111715"
  ink-2: "#46514d"
  ink-3: "#5f6a66"
  signal: "#0f6e5c"
  signal-deep: "#0a5547"
  signal-soft: "#d6ece6"
  gap: "#8f5400"
  gap-fill: "#e8a33d"
  fail: "#b3261e"
  adversary: "#5b3fa8"
  focus: "#1f5fd1"
typography:
  wordmark:
    fontFamily: "Instrument Serif, Georgia, serif"
    fontSize: "1.5rem"
    fontWeight: 400
    lineHeight: 1
  display:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "clamp(2.75rem, 5.6vw, 5rem)"
    fontWeight: 560
    lineHeight: 1.02
    letterSpacing: "-0.035em"
  heading:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "clamp(1.75rem, 3vw, 2.5rem)"
    fontWeight: 540
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
  mono:
    fontFamily: "Geist Mono, ui-monospace, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  control: "10px"
  panel: "16px"
  pill: "999px"
spacing:
  gutter: "24px"
  section: "clamp(6rem, 14vh, 10rem)"
components:
  button-primary:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    height: "48px"
    padding: "0 22px"
  button-primary-hover:
    backgroundColor: "{colors.signal-deep}"
  link-quiet:
    textColor: "{colors.ink-2}"
  quote-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.mono}"
    rounded: "{rounded.control}"
---

## Overview
**Design read:** a redesign (overhaul) of a B2B healthcare-AI landing page and its product UI. It's for practice operations leaders, clinicians and technical evaluators. The language is calm clinical precision with a cinematic 3D story, built on Next 15 + Tailwind v4 + React Three Fiber + Lenis.

**Dials:**

| Surface | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| Marketing | 7 | 8 | 3 |
| App | 3 | 3 | 6 |

The world is **porcelain and evidence**. Soft white ceramic objects sit in diffuse studio light, and the only saturated thing in the scene is the signal-green thread of proof. Colour carries meaning, never decoration:
- green means proven
- amber means a gap
- red means rejected
- purple is the payer adversary's voice, and appears nowhere else

**Theme:** marketing pages are **light only**, per the user's brief. The app is light by default and keeps a dark theme for long sessions.

## Colors
- `porcelain` is the page, and `surface` is lifted elements. The neutrals are cool green-grey, never warm paper. This replaces the old `#f6f4ef`, which belongs to the overused cream family.
- **Contrast against porcelain:**
  - `ink` 16.6:1, `ink-2` 7.5:1, `ink-3` 5.1:1. Every text colour passes AA, which fixes the old 2.93:1 `ink-3`.
  - `signal` is 5.6:1 against porcelain, and white on signal is 6.2:1.
  - `gap` is 5.6:1. Use `gap` for text and `gap-fill` only for shapes.
- **One accent:** signal green. Semantic colours never appear as decoration.
- **3D materials take colour from the same tokens:**
  - porcelain: a matte ceramic with a slight sheen
  - frosted glass for policy sheets
  - signal as an emissive colour for evidence threads only

## Typography
- **Geist** carries display, headings and body. Hierarchy comes from weight (400 / 540 / 560) and tracking, not from mixing families. Emphasis uses colour or weight within Geist.
- **Geist Mono** is for codes, quotes from the chart, numbers and policy IDs. Numbers use `tabular-nums`.
- **Instrument Serif** is the **wordmark only**. That keeps brand recognition, while headlines move to sans (taste rule: no serif display by default). The logo has not changed.
- `text-wrap: balance` on h1–h3 and `pretty` on paragraphs. Body text is limited to 65ch.

## Layout
- One fixed full-viewport WebGL canvas sits behind the whole marketing page (z 0). DOM chapters scroll over it (z 10).
- Chapters are at least 100dvh. Text sits in one column on the left or right, chosen per chapter, never centred twice in a row.
- Container max 1280px, 24px gutter. Below 768px every chapter is one column and the 3D frames above the text.
- The hero fits the first viewport: a headline of two lines at most, a subline of 20 words at most, and one primary plus one secondary CTA.
- No section-number eyebrows, at most one eyebrow per 3 sections, and no scroll cue.

## Elevation & Depth
- Depth comes from the 3D world: real light, contact shadows and depth of field between chapters.
- DOM panels over the scene use `surface` at 82% plus a 14px backdrop blur, a 1px `rule` border and an inner highlight. A solid fallback applies under `prefers-reduced-transparency`.
- Shadows are tinted toward ink-green (`rgb(17 23 21 / 0.10)`), never pure black.
- **z-scale:** canvas 0, chapters 10, nav 40, overlays 50, grain 60.
- Grain is a fixed, pointer-events-none overlay at 3% opacity.

## Shapes
- `control` 10px for buttons, inputs and chips. `panel` 16px for floating panels and cards. `pill` only for status.
- 3D objects use softened bevels (0.04–0.08 radius) to read as ceramic, never as hard CAD.

## Components
- **Buttons:**
  - The primary is signal fill with surface-white text, 48px tall. Hover deepens it; active applies `translateY(1px)`.
  - The secondary is a quiet underline link.
  - Use one label per intent: "Run a live case" (demo) and "See the benchmark" (evals).
- **Quote chip:** a mono quote from the chart with a thin signal underline for proven, amber for a gap, or a strikethrough plus red for rejected.
- **Nav:** a 64px glass bar that hides on scroll down and shows on scroll up. The wordmark is on the left; How it works, Benchmark, Standards and "Run a live case" are on the right.
- **App:** dense tables with a single bottom rule, readiness as a 270° dial, and verdict chips from the four semantic colours. No one-sided thick coloured borders.

## Do's and Don'ts
- **Do:** make every resting frame the finished frame (real numbers in the HTML, animation only plays them in).
- **Do:** keep text still once it's been read. Entrances complete and hold, and 3D motion lives in the scene, not in the copy.
- **Do:** give every 3D chapter a poster for reduced motion, no WebGL and the low tier.
- **Don't:** use em-dashes in visible copy, decorative dots, numbered eyebrows, or filled-track progress bars on marketing pages.
- **Don't:** use purple except for the payer adversary, or use gradients as decoration.
- **Don't:** render 3D objects with a hard CAD look, neon glow or bloom on anything except signal threads.

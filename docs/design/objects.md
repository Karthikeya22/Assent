# 3D objects: img2threejs record

All four are code-only procedural models: no GLBs and no runtime textures. They share three materials (`components/world/objects/materials.ts`): porcelain, paper and glaze. Reference sheet: `refs/reference-sheet.jpeg`.

| Object | Reference | Route | Factory |
|---|---|---|---|
| A. Chart folder | folder-1 | Full gated pipeline: 21 checklist steps, 8 build passes, reviews recorded in `scripts/i2t/folder/object-sculpt-spec.json` | `objects/folder.ts` |
| B. Magnifier | magnifier-0 | img2threejs method (8-layer analysis → part tree → PBR → screenshot vs reference), factory hand-written | `objects/magnifier.ts` |
| C. Balance scales | scales-0 | same method | `objects/scales.ts` |
| D. Seal stamp | stamp-1 | same method | `objects/stamp.ts` |

## Folder: what the full pipeline found
- **Blockout:** the front cover started too tall, with its tab on the wrong side. One refine-spec round fixed it.
- **Form:** the generator emits unbevelled extrudes, so a refine-code patch (`scripts/i2t/refine_code.py`) realises the spec's 0.03 fillet. The badge and cross were 20% small, and the feature gate blocked the pass until they were fixed.
- **Material:** the porcelain is textureless by evidence (crops vary by less than 3%).
  - **Pipeline gap:** `--pass-id material-pass` demands texture maps, while the validator forbids them on textureless materials.
  - Built with the form pass instead, since materials don't depend on the pass. Recorded in the review.
- **Lighting:** hemisphere 0.55, warm key 2.9 from the upper left, fill 0.45, rim 0.7, ACES at exposure 0.95. These carry into the world rig.
- **Budget:** 7,950 triangles and 12 draw calls.
- **Divine Eye:** its silhouette gate could not segment the intentionally cooler porcelain against the warm reference (IoU 0.05–0.53), so the reviews used agent vision. This is noted in every review record.

## B. Magnifier (8-layer analysis)
1. **Identification:** a hand magnifier. Object domain, 0.95.
2. **Form:** a ring (annulus, rounded-rect cross-section) plus a lathe handle at about −50° from the ring centre. Radial symmetry in the ring, bilateral in the handle.
3. **Parts:**
   - Macro: rim and handle.
   - Meso: lens, neck collar.
   - Micro: the teal inner ring line and the teal end cap.
4. **Relations:** <lens, inside, rim>; <handle, attached-to, rim> as a socket at the rim's lower right; <cap, attached-to, handle tip>.
5. **Materials:**
   - Rim and handle: porcelain.
   - Lens: clear glass, roughness about 0.05, a faint green tint, thin.
   - Ring line and cap: glaze.
6. **Colour:** the same porcelain and teal as the folder.
7. **Identity:** the thick soft rim, the teal inner ring, the stubby rounded handle with its teal cap.
8. **Unknowns:** the rim's back face is hidden, so it's assumed symmetric. Lens refraction is approximated with a thin transparent clearcoat (transmission is costly in a full-page scene).

## C. Balance scales
1. **Identification:** classical balance scales. Object, 0.95.
2. **Form:** a central lathe column on a round foot, a horizontal beam with ball ends, and two shallow pans hanging on three strings each. Bilateral.
3. **Parts:**
   - Macro: foot, column, beam, 2 pans.
   - Meso: collar bands, finial, hub, strings.
   - Micro: teal bands (foot rim, column, collar) and the teal hub disc.
4. **Relations:** <beam, pivot-on, column top>; <pan, hangs-from, beam end> on 3 strings; <foot, under, column>.
5. **Materials:** porcelain for the body and pans, glaze for the bands and hub, thin porcelain strings.
6. **Colour:** the same.
7. **Identity:** the level beam with ball ends, the hanging shallow pans, the teal bands.
8. **Unknowns:** the string count (3 per pan is the convention, 2 are visible). Pans hang on pivot groups so the beam can tip in chapter 6.

## D. Seal stamp and wax seal
1. **Identification:** a desk seal stamp and a wax seal. Object, 0.95.
2. **Form:** a lathe handle (bulb, waist, flaring skirt) on a cylindrical base. The seal is a thick disc with a raised rim and an embossed check. Radial symmetry.
3. **Parts:**
   - Macro: the stamp and the seal.
   - Meso: bulb, waist, skirt, base.
   - Micro: the teal base band, the seal rim, the check mark.
4. **Relations:** the seal sits beside the stamp in the reference. In the story the stamp presses onto the packet and leaves the seal.
5. **Materials:** porcelain body, glaze base band and seal, porcelain (or paper) raised check.
6. **Colour:** the same.
7. **Identity:** the bulb-and-skirt handle silhouette, the teal foot band, the round green seal with a white check.
8. **Unknowns:** the underside die face is hidden. It's modelled flat, because it never shows.

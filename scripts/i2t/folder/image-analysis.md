# Image analysis: folder-1 (generated reference, porcelain style)

**L1 Identification.**
- Work type: a filing folder (medical chart folder) holding a stack of loose sheets.
- Broad class: stationery furnishing.
- primaryDomain: object. Confidence: 0.92.

**L2 Form and silhouette.**
- The bounding volume is an upright cuboid, about 0.78 W × 1.0 H × 0.42 D, with height as the reference dimension.
- Built from extruded rounded-rectangle profiles: two slab panels (front and back covers) joined by a U-shaped spine at the bottom, with 3–4 thin sheets standing between them.
- Symmetry: roughly bilateral about the vertical mid-plane of the front cover, broken by the tab positions.
- Shape language: geometric with generous fillets (soft-bevel ceramic).

**L3 Decomposition.**
- **Macro:**
  - front cover: a slab with a raised tab profile on the upper edge
  - back cover: taller, with its tab on the upper-left
  - spine: a U-bend joining the covers at the bottom edge
  - the sheet stack: 3 sheets, plus one tabbed divider sheet
- **Meso:**
  - the front-cover top-edge tab notch (a step down from the tab to the lower edge)
  - the circular embossed badge on the front cover
  - the clip on the upper edge of the middle sheets
- **Micro:**
  - the cross emblem, a raised extruded plus inside the badge
  - edge fillets on all slabs
  - the sheet edge thickness

**L4 Spatial relationships.**
- <front cover, attached-to, spine> butt with a continuous fillet.
- <back cover, attached-to, spine> butt.
- <sheets, inside, covers> standing on the spine floor, fanned slightly backward with an increasing tilt of about 3–8°.
- <badge, embedded-in, front cover> shallow raised disc, about 0.03 relief.
- <cross, attached-to, badge> raised about 0.04.
- <clip, overlap, sheet top edges> straddles 2 sheets.

**L5 Materials (PBR).**
- Porcelain shell for covers, spine and badge: dielectric, metalness 0, roughness about 0.45 (soft broad highlights with no sharp specular), opaque, albedo a warm off-white. The reference skews warm, so it's tuned to DESIGN porcelain `#eef1ef`.
- Sheets: the same porcelain at roughness about 0.55, albedo slightly brighter.
- Cross and clip: glazed teal-green, dielectric, roughness about 0.35, albedo `#0f6e5c` (the signal token).

**L6 Colour and finish.**
- The shell is low saturation, high value, with a satin-matte finish.
- The accents are a deep teal-green: mid-low value, mid saturation, glazed satin.
- There are no gradients beyond lighting.

**L7 Identity features.**
1. The folder tab silhouette, a stepped top edge on the front cover.
2. The fanned sheet stack visible above the covers.
3. The circular badge with the raised cross.
4. The teal clip on the sheet tops.
5. The U-shaped spine visible at the lower edge.

**L8 Uncertainty.**
- The back cover's rear face and the sheet faces behind the front cover are **hidden**. Inferred as flat slabs.
- The spine interior is **occluded**. Inferred as a hollow U.
- The exact sheet count is **uncertain** (3 or 4). Use 4 because they will fan out in the story.
- The stylization is accepted: this is a hero prop for a scroll scene, not a manufacturing model.

"""Author the folder ObjectSculptSpec components from the starter template (img2threejs spec-authoring)."""

import copy
import json
import math

P = "object-sculpt-spec.json"
spec = json.load(open(P, encoding="utf8"))
tmpl = spec["componentTree"][0]


def rrect(w, h, r, n=4, tab=None):
    """Rounded rectangle outline centred at origin; optional tab=(x0,x1,rise,r) on the top edge."""
    pts = []

    def arc(cx, cy, a0, a1):
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append([round(cx + r * math.cos(a), 4), round(cy + r * math.sin(a), 4)])

    hw, hh = w / 2, h / 2
    arc(hw - r, -hh + r, -math.pi / 2, 0)
    if tab:
        x0, _x1, rise, tr = tab
        arc(hw - r, hh + rise - r, 0, math.pi / 2)  # right side runs up to the tab height
        for i in range(9):  # smoothstep S-curve from the tab top down to the lower edge
            t = i / 8
            sm = t * t * (3 - 2 * t)
            pts.append([round(x0 + tr - 2 * tr * t, 4), round(hh + rise - rise * sm, 4)])
    else:
        arc(hw - r, hh - r, 0, math.pi / 2)
    arc(-hw + r, hh - r, math.pi / 2, math.pi)
    arc(-hw + r, -hh + r, math.pi, 3 * math.pi / 2)
    return pts


def comp(
    cid,
    name,
    level,
    role,
    prim,
    topo,
    rationale,
    dims,
    pos,
    rot=(0, 0, 0),
    parent="root",
    material="porcelain",
    descriptor=None,
    contact="butt",
    importance=0.8,
):
    c = copy.deepcopy(tmpl)
    c.update(
        id=cid,
        name=name,
        level=level,
        role=role,
        primitive=prim,
        importance=importance,
        confidence=0.8,
        topologyClass=topo,
        topologyRationale=rationale,
        parent=parent,
    )
    c["dimensions"].update(width=dims[0], height=dims[1], depth=dims[2], confidence=0.75)
    c["transform"].update(position=list(pos), rotation=list(rot), scale=[1, 1, 1])
    c["geometryDescriptor"]["edgeTreatment"] = {
        "type": "fillet",
        "bevelRadius": 0.03,
        "segments": 3,
    }
    if descriptor:
        c["geometryDescriptor"].update(descriptor)
    c["material"] = material
    c["materialLayers"] = [material]
    c["attachment"] = {
        "parentSocket": parent,
        "localStart": list(pos),
        "localEnd": list(pos),
        "contactType": contact,
        "embed": 0.005,
        "overlap": 0.005,
        "gapTolerance": 0.01,
    }
    c["actionProfile"]["animationRole"] = role
    return c


spec["preSpecAssessment"]["unknownsToResolveBeforeImplementation"] = [
    "Rear faces of back cover and sheets are hidden: inferred flat filleted slabs (speculative)",
    "Sheet count 3 or 4: using 4 because the story fans them out",
]

# World-space layout (height 1, origin at folder centre); converted to parent-local below.
# Extrudes grow along local +z from 0 to depth, so their z is the back face (centre - depth/2).
T = 0.06  # cover thickness
W = {}  # id -> world position


def place(c, world):
    W[c["id"]] = world
    return c


parts = [
    place(
        comp(
            "back-cover",
            "Back cover",
            "macro",
            "cover",
            "extrude",
            "assembled-solid",
            "Taller filleted slab with its tab on the upper left; extruded outline is exact for it. Root of the assembly.",
            (0.74, 0.96, T),
            (0, 0, 0),
            parent=None,
            descriptor={
                "profile2D": {
                    "points": rrect(0.74, 0.96, 0.08, tab=(0.05, 0.37, 0.05, 0.06)),
                    "depth": T,
                }
            },
        ),
        (0, -0.02, -0.21 - T / 2),
    ),
    place(
        comp(
            "front-cover",
            "Front cover",
            "macro",
            "cover",
            "extrude",
            "assembled-solid",
            "Flat filleted slab with a stepped tab profile: an extruded outline is exact for it.",
            (0.78, 0.85, T),
            (0, 0, 0),
            parent="back-cover",
            descriptor={
                "profile2D": {
                    "points": rrect(0.78, 0.64, 0.08, tab=(-0.04, 0.39, 0.21, 0.08)),
                    "depth": T,
                }
            },
            importance=1.0,
        ),
        (0, -0.18, 0.15 - T / 2),
    ),
    place(
        comp(
            "spine",
            "U spine",
            "macro",
            "spine",
            "extrude",
            "assembled-solid",
            "U-bend joining the covers along the bottom edge; extruded U profile across the width.",
            (0.78, 0.08, 0.42),
            (0, 0, 0),
            rot=(0, math.pi / 2, 0),
            parent="back-cover",
            descriptor={
                "profile2D": {
                    "points": [
                        [-0.21, 0.06],
                        [-0.21, -0.02],
                        [-0.17, -0.06],
                        [0.17, -0.06],
                        [0.21, -0.02],
                        [0.21, 0.06],
                        [0.15, 0.06],
                        [0.15, 0.0],
                        [-0.15, 0.0],
                        [-0.15, 0.06],
                    ],
                    "depth": 0.78,
                }
            },
        ),
        (-0.39, -0.5, -0.03),
    ),
]
for i, (z, tilt, h) in enumerate(
    [(0.09, -0.07, 0.9), (0.03, -0.13, 0.94), (-0.04, -0.19, 0.97), (-0.11, -0.25, 0.93)]
):
    tab = (0.1 - 0.12 * i, 0.3, 0.04, 0.05) if i == 3 else None
    parts.append(
        place(
            comp(
                f"sheet-{i + 1}",
                f"Sheet {i + 1}",
                "meso",
                "sheet",
                "extrude",
                "assembled-solid",
                "Thin filleted card standing in the folder; tilted back progressively.",
                (0.7, h, 0.014),
                (0, 0, 0),
                rot=(tilt, 0, 0),
                material="paper",
                parent="back-cover",
                descriptor={"profile2D": {"points": rrect(0.7, h, 0.05, tab=tab), "depth": 0.014}},
            ),
            (0, -0.48 + h / 2, z),
        )
    )
parts += [
    place(
        comp(
            "badge",
            "Embossed badge",
            "meso",
            "badge",
            "cylinder",
            "assembled-solid",
            "Shallow raised disc on the front cover face.",
            (0.37, 0.03, 0.37),
            (0, 0, 0),
            rot=(math.pi / 2, 0, 0),
            parent="front-cover",
            contact="embed",
        ),
        (0.087, -0.13, 0.195),
    ),
    place(
        comp(
            "cross-v",
            "Cross vertical bar",
            "micro",
            "emblem",
            "box",
            "assembled-solid",
            "Raised bar of the plus emblem.",
            (0.085, 0.245, 0.045),
            (0, 0, 0),
            parent="front-cover",
            material="teal-glaze",
            contact="embed",
        ),
        (0.087, -0.13, 0.215),
    ),
    place(
        comp(
            "cross-h",
            "Cross horizontal bar",
            "micro",
            "emblem",
            "box",
            "assembled-solid",
            "Raised bar of the plus emblem.",
            (0.245, 0.085, 0.045),
            (0, 0, 0),
            parent="front-cover",
            material="teal-glaze",
            contact="embed",
        ),
        (0.087, -0.13, 0.215),
    ),
    place(
        comp(
            "clip",
            "Sheet clip",
            "meso",
            "clip",
            "box",
            "assembled-solid",
            "Rounded teal block straddling the tops of the middle sheets.",
            (0.075, 0.15, 0.05),
            (0, 0, 0),
            parent="back-cover",
            material="teal-glaze",
            contact="overlap",
        ),
        (-0.08, 0.41, 0.115),
    ),
]
UNIT = {"box": lambda d: [d[0], d[1], d[2]], "cylinder": lambda d: [d[0], d[1], d[2]]}
for c in parts:
    wp = W[c["id"]]
    pp = W[c["parent"]] if c["parent"] else (0, 0, 0)
    local = [round(wp[k] - pp[k], 4) for k in range(3)]
    c["transform"]["position"] = local
    c["attachment"] = (
        None if c["parent"] is None else {**c["attachment"], "localStart": local, "localEnd": local}
    )
    d = c["dimensions"]
    if c["primitive"] in UNIT:  # unit primitives are sized through transform.scale
        c["transform"]["scale"] = UNIT[c["primitive"]]((d["width"], d["height"], d["depth"]))
root = parts[0]
root["role"] = "body"
spec["componentTree"] = parts

base = spec["materials"][0]


def mat(mid, name, color, rough, notes):
    m = copy.deepcopy(base)
    m.update(
        id=mid,
        name=name,
        baseColor=color,
        color=color,
        type="physical",
        shaderModel="MeshPhysicalMaterial (dielectric, clearcoat for glaze)",
    )
    m["albedo"] = {"dominant": color, "secondary": [color], "samplingNotes": notes}
    m["colorVariation"] = {
        "palette": [color],
        "pattern": "none",
        "amplitude": 0.0,
        "heightCorrelation": 0.0,
    }
    m["roughness"] = {
        "base": rough,
        "variation": 0.04,
        "map": "none",
        "localResponse": "uniform satin ceramic",
    }
    m["metalness"] = {"base": 0.0, "variation": 0.0}
    m["normal"] = {"pattern": "none", "strength": 0.0, "scale": 1.0, "space": "tangent"}
    return m


spec["materials"] = [
    mat(
        "porcelain",
        "Porcelain shell",
        "#e2e7e4",
        0.42,
        "Matte-satin ceramic; tuned to DESIGN porcelain, reference skews warm.",
    ),
    mat(
        "paper", "Porcelain sheet", "#ebefed", 0.58, "Slightly brighter and rougher than the shell."
    ),
    mat("teal-glaze", "Teal glaze", "#0f6e5c", 0.32, "Glazed signal green, clearcoat 0.4."),
]
spec["performanceBudget"].update(
    targetTriangles=20000,
    maxDrawCalls=16,
    textureSize=0,
    fpsTarget=60,
    qualityPriority="real-time-hero-prop",
)
json.dump(spec, open(P, "w", encoding="utf8"), indent=1)
print("components", len(spec["componentTree"]), "materials", len(spec["materials"]))

# --- strict-quality pass: textureless materials, colour recipes, lighting, local features ---
spec = json.load(open(P, encoding="utf8"))
EVID = {
    "porcelain": "pbr/porcelain.json",
    "paper": "pbr/paper.json",
    "teal-glaze": "pbr/teal-glaze.json",
}
for m in spec["materials"]:
    for f in (
        "normal",
        "bump",
        "displacement",
        "surfaceFrequencyBands",
        "textureProjection",
        "textureResolution",
        "referencePbr",
    ):
        m.pop(f, None)
    m["textureless"] = {
        "declared": True,
        "evidence": [
            f"{EVID[m['id']]}: single-crop extraction palette spans <3% value, no grain/print/pores",
            "reference view ref.png: glazed porcelain render, identity is silhouette + colour regions",
        ],
    }
    m["ambientOcclusion"] = (
        "baked-free; contact shadow plane + SSAO-free soft AO from hemisphere light"
    )
    # glaze: porcelain carries a thin satin glaze (soft broad highlight in the reference), teal a glossier one
    m["clearcoat"] = {"porcelain": 0.3, "paper": 0.0, "teal-glaze": 0.55}[m["id"]]
    m["clearcoatRoughness"] = {"porcelain": 0.4, "paper": 0.25, "teal-glaze": 0.25}[m["id"]]

RGBA = {
    "porcelain": "rgba(226, 231, 228, 1.0)",
    "paper": "rgba(235, 239, 237, 1.0)",
    "teal-glaze": "rgba(15, 110, 92, 1.0)",
}
SEC = {
    "porcelain": "rgba(214, 220, 216, 1.0)",
    "paper": "rgba(228, 233, 230, 1.0)",
    "teal-glaze": "rgba(10, 85, 71, 1.0)",
}
FEATURES = {
    "front-cover": [
        {"id": "tab-step", "kind": "contour", "description": "right-raised tab with S-step down"},
        {"id": "edge-fillet", "kind": "bevel", "description": "0.03 fillet on all edges"},
    ],
    "badge": [{"id": "emboss-disc", "kind": "ridge", "description": "0.03 raised disc relief"}],
    "cross-v": [
        {"id": "cross-glaze", "kind": "gloss", "description": "glazed raised plus, clearcoat"}
    ],
    "clip": [
        {"id": "clip-straddle", "kind": "contour", "description": "block straddling two sheet tops"}
    ],
    "spine": [{"id": "u-bend", "kind": "contour", "description": "U-bend joining covers"}],
}
for c in spec["componentTree"]:
    mid = c["material"]
    c["colorMaterialRecipe"] = {
        "dominantAlbedo": RGBA[mid],
        "secondaryAlbedo": SEC[mid],
        "materialClass": "ceramic",
        "materialClassConfidence": 0.85,
        "evidenceRefs": [EVID[mid]],
    }
    c["localFeatures"] = FEATURES.get(c["id"], [])
spec["preSpecAssessment"]["detailInventory"]["details"] = [
    {
        "id": "d1",
        "kind": "contour",
        "zone": "front-cover-top",
        "mapsTo": "front-cover/tab-step",
        "description": "stepped tab",
    },
    {
        "id": "d2",
        "kind": "ridge",
        "zone": "front-cover-center",
        "mapsTo": "badge/emboss-disc",
        "description": "raised badge",
    },
    {
        "id": "d3",
        "kind": "gloss",
        "zone": "badge",
        "mapsTo": "cross-v/cross-glaze",
        "description": "glazed cross",
    },
    {
        "id": "d4",
        "kind": "contour",
        "zone": "sheet-tops",
        "mapsTo": "clip/clip-straddle",
        "description": "teal clip",
    },
    {
        "id": "d5",
        "kind": "contour",
        "zone": "bottom",
        "mapsTo": "spine/u-bend",
        "description": "U spine",
    },
    {
        "id": "d6",
        "kind": "bevel",
        "zone": "all-edges",
        "mapsTo": "front-cover/edge-fillet",
        "description": "edge fillets",
    },
]
spec["lightingFromPhoto"] = [
    "key: directional, upper-left-front, warm white 1.0, soft shadow (radius 6)",
    "fill: hemisphere sky #ffffff / ground #dfe5e2 at 0.65 for the low-contrast porcelain falloff",
    "rim: directional from rear-right at 0.35 to separate the silhouette from the porcelain backdrop",
    "exposure 1.0 with ACES filmic tone mapping",
    "contact shadow on the ground plane under the spine, soft and short",
]
json.dump(spec, open(P, "w", encoding="utf8"), indent=1)
print("strict fields written")

# --- strict pass 2 ---
spec = json.load(open(P, encoding="utf8"))
pa = spec["preSpecAssessment"]
spec["assumptions"] = (
    list(spec.get("assumptions") or []) + pa["unknownsToResolveBeforeImplementation"]
)
pa["unknownsToResolveBeforeImplementation"] = []
for d in pa["detailInventory"]["details"]:
    d["mapsTo"] = {"ref": d["mapsTo"]}
for m in spec["materials"]:
    m["ambientOcclusion"] = {
        "source": "lighting",
        "strength": 0.35,
        "notes": "soft hemisphere AO plus contact-shadow plane; no baked map (textureless)",
    }
spec["materials"][0]["localOverrides"] = [
    {
        "id": "crease-ao",
        "mask": "inner corner where tab steps down and where covers meet the spine",
        "albedo": "rgba(214, 220, 216, 1.0)",
        "roughness": 0.5,
        "evidenceRefs": ["upper-front-cover", "bottom"],
    },
    {
        "id": "edge-sheen",
        "mask": "filleted edges catching the key light",
        "roughness": 0.36,
        "evidenceRefs": ["front-cover-right-edge"],
    },
]
spec["featureReviewTargets"] = [
    {
        "id": "folder-silhouette",
        "name": "Upright folder silhouette: covers, tab step, sheets above",
        "tier": "critical",
        "passIds": ["blockout", "structural-pass"],
        "minimumScore": 0.8,
        "mustPass": True,
        "componentRefs": ["front-cover", "back-cover", "sheet-1", "sheet-2", "sheet-3", "sheet-4"],
        "evidenceRefs": ["full-object"],
    },
    {
        "id": "tab-step",
        "name": "Front cover stepped tab on the right",
        "tier": "critical",
        "passIds": ["structural-pass", "form-refinement"],
        "minimumScore": 0.8,
        "mustPass": True,
        "componentRefs": ["front-cover"],
        "evidenceRefs": ["upper-front-cover"],
    },
    {
        "id": "badge-cross",
        "name": "Raised badge with teal cross on the front cover",
        "tier": "critical",
        "passIds": ["form-refinement", "material-pass"],
        "minimumScore": 0.8,
        "mustPass": True,
        "componentRefs": ["badge", "cross-v", "cross-h"],
        "evidenceRefs": ["front-cover-center"],
    },
    {
        "id": "porcelain-response",
        "name": "Satin porcelain + glazed teal response under soft key light",
        "tier": "critical",
        "passIds": ["material-pass", "lighting-pass"],
        "minimumScore": 0.75,
        "mustPass": True,
        "componentRefs": ["front-cover", "cross-v", "clip"],
        "evidenceRefs": ["full-object"],
    },
    {
        "id": "fanned-sheets",
        "name": "Four sheets fanned back between the covers",
        "tier": "important",
        "passIds": ["structural-pass"],
        "minimumScore": 0.7,
        "mustPass": False,
        "componentRefs": ["sheet-1", "sheet-2", "sheet-3", "sheet-4", "clip"],
        "evidenceRefs": ["upper-middle"],
    },
]
json.dump(spec, open(P, "w", encoding="utf8"), indent=1)
print("strict pass 2 written")

# --- interaction pass: hinge/pivots/sockets for the scroll story ---
spec = json.load(open(P, encoding="utf8"))
for c in spec["componentTree"]:
    ap = c["actionProfile"]
    if c["id"] == "front-cover":
        ap["pivot"] = {
            "mode": "edge",
            "localPosition": [0, -0.32, 0.03],
            "axis": [1, 0, 0],
            "confidence": 0.85,
            "notes": "hinge along the spine edge: the cover swings open (rotate -x) in chapter 3",
        }
        ap["constraints"] = [{"type": "rotation-limit", "axis": "x", "min": -1.9, "max": 0}]
    elif c["id"].startswith("sheet-"):
        h = c["dimensions"]["height"]
        ap["pivot"] = {
            "mode": "edge",
            "localPosition": [0, round(-h / 2, 3), 0.007],
            "axis": [1, 0, 0],
            "confidence": 0.85,
            "notes": "sheets fan about their bottom edge, then detach to fly to the timeline (chapter 3)",
        }
        ap["transformChannels"]["detach"] = True
    elif c["id"] == "back-cover":
        ap["sockets"] = [
            {
                "id": "hero-anchor",
                "localPosition": [0, 0, 0.18],
                "notes": "group anchor for cursor tilt",
            }
        ]
json.dump(spec, open(P, "w", encoding="utf8"), indent=1)
print("interaction written")

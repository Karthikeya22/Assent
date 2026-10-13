"""img2threejs refine-code for porcelain props: ceramic fillets the generator cannot emit.

The spec records edgeTreatment fillet 0.03 on every component; the generated factory builds
unbevelled extrudes and sharp boxes/cylinders. This patch realises that recorded intent:
  - extrudes: bevelEnabled with the fillet radius
  - unit boxes scaled to size: RoundedBoxGeometry at true size (radius ~35% of the thinnest side)
  - unit cylinders scaled to size: a lathe disc with rounded rims at true size
usage: refine_code.py <factory.ts> [fillet]
"""

import re
import sys

path = sys.argv[1]
fillet = float(sys.argv[2]) if len(sys.argv) > 2 else 0.018
s = open(path, encoding="utf8").read()

if "RoundedBoxGeometry" not in s:
    s = s.replace(
        "import * as THREE from 'three';",
        "import * as THREE from 'three';\nimport { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';",
        1,
    )

s = s.replace(
    "    bevelEnabled: false,\n    steps: 1,",
    f"    bevelEnabled: true,\n    bevelThickness: {fillet},\n    bevelSize: {fillet},\n    bevelSegments: 4,\n    curveSegments: 16,\n    steps: 1,",
)

box = re.compile(
    r"new THREE\.BoxGeometry\(1, 1, 1, \d+, \d+, \d+\);\n(\s+)if \(!(\w+)\) \{\n\s+(\w+)\.scale\(([\d.]+), ([\d.]+), ([\d.]+)\);"
)


def rounded(m: re.Match) -> str:
    ind, ep, geo = m.group(1), m.group(2), m.group(3)
    w, h, d = (float(m.group(i)) for i in (4, 5, 6))
    r = round(min(w, h, d) * 0.35, 4)
    return f"new RoundedBoxGeometry({w}, {h}, {d}, 4, {r});\n{ind}if (!{ep}) {{\n{ind}  {geo}.scale(1, 1, 1);"


s, nbox = box.subn(rounded, s)

cyl = re.compile(
    r"new THREE\.CylinderGeometry\(0\.5, 0\.5, 1, \d+, \d+\);\n(\s+)if \(!(\w+)\) \{\n\s+(\w+)\.scale\(([\d.]+), ([\d.]+), ([\d.]+)\);"
)


def disc(m: re.Match) -> str:
    ind, ep, geo = m.group(1), m.group(2), m.group(3)
    r, h = float(m.group(4)) / 2, float(m.group(5))
    f = round(min(h * 0.45, r * 0.2), 4)
    return f"roundedDisc({r}, {h}, {f});\n{ind}if (!{ep}) {{\n{ind}  {geo}.scale(1, 1, 1);"


s, ncyl = cyl.subn(disc, s)
if ncyl and "function roundedDisc" not in s:
    s += """
// Lathe disc with quarter-round rims: a ceramic badge, not a machined puck.
function roundedDisc(r: number, h: number, f: number): THREE.LatheGeometry {
  const pts: THREE.Vector2[] = [new THREE.Vector2(0, -h / 2)];
  for (let i = 0; i <= 6; i++) {
    const a = -Math.PI / 2 + (i / 6) * (Math.PI / 2);
    pts.push(new THREE.Vector2(r - f + f * Math.cos(a), -h / 2 + f + f * Math.sin(a)));
  }
  for (let i = 0; i <= 6; i++) {
    const a = (i / 6) * (Math.PI / 2);
    pts.push(new THREE.Vector2(r - f + f * Math.cos(a), h / 2 - f + f * Math.sin(a)));
  }
  pts.push(new THREE.Vector2(0, h / 2));
  return new THREE.LatheGeometry(pts, 64);
}
"""
open(path, "w", encoding="utf8").write(s)
print(f"refine-code: {nbox} rounded boxes, {ncyl} rounded discs, extrude fillet {fillet}")

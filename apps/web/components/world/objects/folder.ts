import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { mesh, roundedDisc, roundedRect, slab, type WorldMaterials } from "./materials";

/**
 * Patient chart folder (asset A). Built through the full img2threejs pipeline (8 passes, spec in
 * scripts/i2t/folder, reference docs/design/refs) and ported here without the generator's metadata.
 * Height 1, centred on the origin. `hinge` opens the front cover (rotation.x, 0 to -1.9) and each
 * `sheets[i]` pivots on its bottom edge (rotation.x) or detaches for the timeline beat.
 */
export type Folder = { group: THREE.Group; hinge: THREE.Group; sheets: THREE.Group[]; rest: number[] };

const T = 0.06; // cover thickness
// Tilts about the bottom edge (the spec tilted about sheet centres: half these angles look the same).
const SHEETS = [
  { z: 0.09, tilt: -0.035, h: 0.9 },
  { z: 0.03, tilt: -0.065, h: 0.94 },
  { z: -0.04, tilt: -0.095, h: 0.97 },
  { z: -0.11, tilt: -0.125, h: 0.93, tab: { x0: -0.26, rise: 0.04, step: 0.05 } },
];

export function createFolder(mats: WorldMaterials): Folder {
  const group = new THREE.Group();
  group.name = "folder";

  const back = mesh(slab(roundedRect(0.74, 0.96, 0.08, { x0: 0.05, rise: 0.05, step: 0.06 }), T), mats.porcelain, "back-cover");
  back.position.set(0, -0.02, -0.24);
  group.add(back);

  // U spine: an extruded U profile run across the width.
  const u = new THREE.Shape(
    [
      [-0.21, 0.06], [-0.21, -0.02], [-0.17, -0.06], [0.17, -0.06], [0.21, -0.02],
      [0.21, 0.06], [0.15, 0.06], [0.15, 0], [-0.15, 0], [-0.15, 0.06],
    ].map(([x, y]) => new THREE.Vector2(x, y)),
  );
  const spine = mesh(slab(u, 0.78), mats.porcelain, "spine");
  spine.rotation.y = Math.PI / 2;
  spine.position.set(-0.39, -0.5, -0.03);
  group.add(spine);

  const sheets = SHEETS.map((s, i) => {
    const pivot = new THREE.Group();
    pivot.name = `sheet-${i + 1}`;
    pivot.position.set(0, -0.48, s.z);
    pivot.rotation.x = s.tilt;
    const m = mesh(slab(roundedRect(0.7, s.h, 0.05, s.tab), 0.014), mats.paper, `sheet-${i + 1}`);
    m.position.y = s.h / 2;
    pivot.add(m);
    group.add(pivot);
    return pivot;
  });

  const clip = mesh(new RoundedBoxGeometry(0.075, 0.15, 0.05, 4, 0.0175), mats.glaze, "clip");
  clip.position.set(-0.08, 0.41, 0.115);
  group.add(clip);

  // Front cover hangs on a hinge along the spine edge; badge and cross ride with it.
  const hinge = new THREE.Group();
  hinge.name = "front-hinge";
  hinge.position.set(0, -0.5, 0.15);
  group.add(hinge);
  const front = mesh(slab(roundedRect(0.78, 0.64, 0.08, { x0: -0.04, rise: 0.21, step: 0.08 }), T), mats.porcelain, "front-cover");
  front.position.set(0, 0.32, -0.03);
  hinge.add(front);
  const badge = mesh(roundedDisc(0.185, 0.03, 0.0135), mats.porcelain, "badge");
  badge.rotation.x = Math.PI / 2;
  badge.position.set(0.087, 0.37, 0.045);
  hinge.add(badge);
  for (const [w, h] of [[0.085, 0.245], [0.245, 0.085]]) {
    const bar = mesh(new RoundedBoxGeometry(w, h, 0.045, 4, 0.0158), mats.glaze, "cross");
    bar.position.set(0.087, 0.37, 0.065);
    hinge.add(bar);
  }

  return { group, hinge, sheets, rest: SHEETS.map((s) => s.tilt) };
}

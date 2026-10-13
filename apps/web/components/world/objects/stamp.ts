import * as THREE from "three";
import { mesh, roundedDisc, type WorldMaterials } from "./materials";

/**
 * Seal stamp + wax seal (asset D, img2threejs method; analysis in docs/design/objects.md).
 * The stamp stands on y=0, about 0.95 tall. The seal is separate: the story stamps it onto the packet.
 */
export type Stamp = { stamp: THREE.Group; seal: THREE.Group };

export function createStamp(mats: WorldMaterials): Stamp {
  const stamp = new THREE.Group();
  stamp.name = "stamp";
  const profile = [
    [0, 0], [0.31, 0], [0.32, 0.012], [0.32, 0.16], [0.3, 0.175], [0.22, 0.2], [0.14, 0.26],
    [0.1, 0.36], [0.095, 0.45], [0.11, 0.53], [0.16, 0.6], [0.19, 0.69], [0.19, 0.78],
    [0.165, 0.86], [0.11, 0.92], [0.05, 0.945], [0, 0.95],
  ].map(([x, y]) => new THREE.Vector2(x, y));
  stamp.add(mesh(new THREE.LatheGeometry(profile, 72), mats.porcelain, "handle"));
  const band = mesh(roundedDisc(0.322, 0.05, 0.012, 72), mats.glaze, "foot-band");
  band.position.y = 0.025;
  stamp.add(band);

  const seal = new THREE.Group();
  seal.name = "seal";
  seal.add(mesh(roundedDisc(0.2, 0.07, 0.025, 64), mats.glaze, "wax"));
  const lip = mesh(new THREE.TorusGeometry(0.165, 0.012, 10, 64), mats.glaze, "lip");
  lip.rotation.x = Math.PI / 2;
  lip.position.y = 0.035;
  seal.add(lip);
  // Embossed check: a swept tube along a two-segment path, raised above the wax face.
  const path = new THREE.CurvePath<THREE.Vector3>();
  path.add(new THREE.LineCurve3(new THREE.Vector3(-0.085, 0.04, -0.005), new THREE.Vector3(-0.025, 0.04, 0.055)));
  path.add(new THREE.LineCurve3(new THREE.Vector3(-0.025, 0.04, 0.055), new THREE.Vector3(0.095, 0.04, -0.07)));
  const check = mesh(new THREE.TubeGeometry(path, 32, 0.017, 10, false), mats.paper, "check");
  seal.add(check);
  for (const p of [new THREE.Vector3(-0.085, 0.04, -0.005), new THREE.Vector3(0.095, 0.04, -0.07)]) {
    const end = mesh(new THREE.SphereGeometry(0.017, 12, 10), mats.paper, "check-end");
    end.position.copy(p);
    seal.add(end);
  }
  return { stamp, seal };
}

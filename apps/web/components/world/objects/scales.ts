import * as THREE from "three";
import { mesh, roundedDisc, type WorldMaterials } from "./materials";

/**
 * Balance scales (asset C, img2threejs method; analysis in docs/design/objects.md). Foot on y=0,
 * about 1.15 tall. Tip the balance with `beam.rotation.z`; pans counter-rotate to hang level.
 */
export type Scales = { group: THREE.Group; beam: THREE.Group; pans: THREE.Group[] };

const lathe = (pts: number[][], seg = 64) =>
  new THREE.LatheGeometry(pts.map(([x, y]) => new THREE.Vector2(x, y)), seg);

export function createScales(mats: WorldMaterials): Scales {
  const group = new THREE.Group();
  group.name = "scales";

  // Foot + column as one revolved profile; teal bands are thin rings laid over it.
  const body = lathe([
    [0, 0], [0.3, 0], [0.32, 0.015], [0.32, 0.05], [0.27, 0.085], [0.17, 0.11], [0.12, 0.15],
    [0.09, 0.22], [0.08, 0.6], [0.095, 0.63], [0.095, 0.67], [0.08, 0.7], [0.07, 0.92],
    [0.09, 0.95], [0.09, 0.98], [0.06, 1.01], [0, 1.01],
  ]);
  group.add(mesh(body, mats.porcelain, "column"));
  for (const [r, y, t] of [[0.322, 0.033, 0.013], [0.097, 0.65, 0.012], [0.092, 0.965, 0.01]]) {
    const band = mesh(new THREE.TorusGeometry(r, t, 10, 64), mats.glaze, "band");
    band.rotation.x = Math.PI / 2;
    band.position.y = y;
    group.add(band);
  }
  const finial = mesh(new THREE.SphereGeometry(0.055, 24, 16), mats.porcelain, "finial");
  finial.position.y = 1.14;
  group.add(finial);

  const beam = new THREE.Group();
  beam.name = "beam";
  beam.position.y = 1.05;
  group.add(beam);
  const bar = mesh(new THREE.CapsuleGeometry(0.04, 0.88, 6, 16), mats.porcelain, "bar");
  bar.rotation.z = Math.PI / 2;
  beam.add(bar);
  const hub = mesh(roundedDisc(0.075, 0.05, 0.014, 40), mats.porcelain, "hub");
  hub.rotation.x = Math.PI / 2;
  beam.add(hub);
  const hubDot = mesh(roundedDisc(0.042, 0.02, 0.006, 32), mats.glaze, "hub-dot");
  hubDot.rotation.x = Math.PI / 2;
  hubDot.position.z = 0.03;
  beam.add(hubDot);

  const pans = [-1, 1].map((side) => {
    const end = mesh(new THREE.SphereGeometry(0.06, 24, 16), mats.porcelain, "beam-end");
    end.position.x = side * 0.48;
    beam.add(end);
    const hang = new THREE.Group();
    hang.name = side < 0 ? "pan-left" : "pan-right";
    hang.position.x = side * 0.48;
    beam.add(hang);
    const drop = 0.5;
    const bowl = mesh(lathe([[0, 0], [0.1, 0.006], [0.18, 0.04], [0.225, 0.095], [0.225, 0.11], [0.2, 0.105], [0.16, 0.06], [0.08, 0.03], [0, 0.026]]), mats.porcelain, "pan");
    bowl.position.y = -drop;
    hang.add(bowl);
    const rim = mesh(new THREE.TorusGeometry(0.222, 0.01, 8, 48), mats.glaze, "pan-rim");
    rim.rotation.x = Math.PI / 2;
    rim.position.y = -drop + 0.1;
    hang.add(rim);
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI * 2 + Math.PI / 6;
      const foot = new THREE.Vector3(Math.cos(a) * 0.215, -drop + 0.1, Math.sin(a) * 0.215);
      const len = foot.length();
      const s = mesh(new THREE.CylinderGeometry(0.004, 0.004, len, 6), mats.porcelain, "string");
      s.position.copy(foot).multiplyScalar(0.5);
      s.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), foot.clone().normalize());
      hang.add(s);
    }
    return hang;
  });

  return { group, beam, pans };
}

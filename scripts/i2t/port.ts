// Shim: exposes a web-app object factory to the review harness as create*Model().
import * as THREE from "three";
import { createMaterials } from "../../apps/web/components/world/objects/materials";
import { createFolder } from "../../apps/web/components/world/objects/folder";
import { createMagnifier } from "../../apps/web/components/world/objects/magnifier";
import { createScales } from "../../apps/web/components/world/objects/scales";
import { createStamp } from "../../apps/web/components/world/objects/stamp";
export function createPortModel(): THREE.Object3D {
  const which = new URLSearchParams(location.search).get("obj") ?? "folder";
  const mats = createMaterials();
  if (which === "folder") return createFolder(mats).group;
  if (which === "magnifier") {
    const g = createMagnifier(mats).group;
    g.rotation.set(-0.5, 0.2, 0.15); // lying at the reference's three-quarter angle
    return g;
  }
  if (which === "scales") return createScales(mats).group;
  if (which === "stamp") {
    const { stamp, seal } = createStamp(mats);
    const g = new THREE.Group();
    g.add(stamp);
    seal.rotation.set(Math.PI / 2 - 0.25, 0, 0); // standing on edge, leaning back on the stamp like the reference
    seal.position.set(0.36, 0.19, 0.22);
    g.add(seal);
    return g;
  }
  throw new Error(`unknown obj ${which}`);
}

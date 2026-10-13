import * as THREE from "three";
import { mesh, roundedDisc, type WorldMaterials } from "./materials";

/**
 * Magnifier (asset B, img2threejs method; analysis in docs/design/objects.md). Lens faces +Z, ring
 * centred on the origin, outer radius 0.5. `lens` is exposed so the story can swap in a magnified view.
 */
export type Magnifier = { group: THREE.Group; lens: THREE.Mesh };

/** Annulus with a rounded-rect cross-section, revolved about +Z (lathe runs about Y, then turned). */
function ring(inner: number, outer: number, depth: number, f: number): THREE.LatheGeometry {
  const pts: THREE.Vector2[] = [];
  const corner = (cx: number, cy: number, a0: number) => {
    for (let i = 0; i <= 5; i++) {
      const a = a0 + (i / 5) * (Math.PI / 2);
      pts.push(new THREE.Vector2(cx + f * Math.cos(a), cy + f * Math.sin(a)));
    }
  };
  const h = depth / 2;
  corner(outer - f, -h + f, -Math.PI / 2);
  corner(outer - f, h - f, 0);
  corner(inner + f, h - f, Math.PI / 2);
  corner(inner + f, -h + f, Math.PI);
  pts.push(pts[0].clone());
  const g = new THREE.LatheGeometry(pts, 96);
  g.rotateX(Math.PI / 2);
  return g;
}

export function createMagnifier(mats: WorldMaterials): Magnifier {
  const group = new THREE.Group();
  group.name = "magnifier";

  group.add(mesh(ring(0.37, 0.5, 0.14, 0.05), mats.porcelain, "rim"));
  const line = mesh(new THREE.TorusGeometry(0.385, 0.012, 12, 96), mats.glaze, "rim-line");
  line.position.z = 0.062;
  group.add(line);

  const lens = new THREE.Mesh(
    roundedDisc(0.375, 0.04, 0.015).rotateX(Math.PI / 2),
    new THREE.MeshPhysicalMaterial({
      color: "#d6ece6", // signal-soft
      roughness: 0.04,
      clearcoat: 1,
      clearcoatRoughness: 0.02,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    }),
  );
  lens.name = "lens";
  group.add(lens);

  // Handle: lathe along +Y, then hung from the rim's lower right at about -50 degrees.
  const profile = [
    [0, 0], [0.085, 0], [0.095, 0.07], [0.085, 0.15], [0.1, 0.26], [0.135, 0.46],
    [0.15, 0.6], [0.14, 0.68], [0.11, 0.735], [0.06, 0.758], [0, 0.762],
  ].map(([x, y]) => new THREE.Vector2(x, y));
  const handle = new THREE.Group();
  handle.name = "handle";
  handle.rotation.z = Math.PI + 0.87; // points down-right
  handle.position.set(0.5 * Math.sin(0.87), -0.5 * Math.cos(0.87), 0).multiplyScalar(0.92);
  handle.add(mesh(new THREE.LatheGeometry(profile, 48), mats.porcelain, "grip"));
  const cap = mesh(roundedDisc(0.055, 0.02, 0.008, 32), mats.glaze, "cap");
  cap.position.y = 0.758;
  handle.add(cap);
  group.add(handle);

  return { group, lens };
}

import * as THREE from "three";

/**
 * The world's three surfaces (DESIGN.md: porcelain and evidence). Shared by every object so the
 * scene stays one set; values come from the img2threejs folder spec (material + lighting passes).
 */
export type WorldMaterials = ReturnType<typeof createMaterials>;

export function createMaterials() {
  return {
    porcelain: new THREE.MeshPhysicalMaterial({
      color: "#e2e7e4",
      roughness: 0.42,
      clearcoat: 0.3,
      clearcoatRoughness: 0.4,
    }),
    paper: new THREE.MeshPhysicalMaterial({ color: "#ebefed", roughness: 0.58 }),
    glaze: new THREE.MeshPhysicalMaterial({
      color: "#0f6e5c",
      roughness: 0.32,
      clearcoat: 0.55,
      clearcoatRoughness: 0.25,
    }),
  };
}

/** Rounded-rectangle outline centred on the origin; `tab` raises part of the top edge with an S-step. */
export function roundedRect(
  w: number,
  h: number,
  r: number,
  tab?: { x0: number; rise: number; step: number },
): THREE.Shape {
  const pts: THREE.Vector2[] = [];
  const arc = (cx: number, cy: number, a0: number, a1: number) => {
    for (let i = 0; i <= 4; i++) {
      const a = a0 + ((a1 - a0) * i) / 4;
      pts.push(new THREE.Vector2(cx + r * Math.cos(a), cy + r * Math.sin(a)));
    }
  };
  const hw = w / 2;
  const hh = h / 2;
  arc(hw - r, -hh + r, -Math.PI / 2, 0);
  if (tab) {
    arc(hw - r, hh + tab.rise - r, 0, Math.PI / 2);
    for (let i = 0; i <= 8; i++) {
      const t = i / 8;
      const s = t * t * (3 - 2 * t);
      pts.push(new THREE.Vector2(tab.x0 + tab.step - 2 * tab.step * t, hh + tab.rise - tab.rise * s));
    }
  } else {
    arc(hw - r, hh - r, 0, Math.PI / 2);
  }
  arc(-hw + r, hh - r, Math.PI / 2, Math.PI);
  arc(-hw + r, -hh + r, Math.PI, (3 * Math.PI) / 2);
  return new THREE.Shape(pts);
}

/** A slab extruded from `shape` with ceramic fillets (img2threejs refine-code: bevel = fillet intent). */
export function slab(shape: THREE.Shape, depth: number, fillet = 0.018): THREE.ExtrudeGeometry {
  return new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: true,
    bevelThickness: fillet,
    bevelSize: fillet,
    bevelSegments: 4,
    curveSegments: 16,
  });
}

/** Lathe disc with quarter-round rims, axis +Y. */
export function roundedDisc(r: number, h: number, f: number, segments = 64): THREE.LatheGeometry {
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
  return new THREE.LatheGeometry(pts, segments);
}

export function mesh(geo: THREE.BufferGeometry, mat: THREE.Material, name: string): THREE.Mesh {
  const m = new THREE.Mesh(geo, mat);
  m.name = name;
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

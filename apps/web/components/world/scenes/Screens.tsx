"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { mesh, type WorldMaterials } from "../objects/materials";
import { damp, pointer } from "../pointer";
import { span } from "../shared";
import { useWorld } from "../store";

// Real screenshots of the product (captured from the running app), one per step of "how you use it".
const SHOTS = ["/world/screens/ehr.webp", "/world/screens/case.webp", "/world/screens/worklist.webp"];
const LAYOUT = [
  { x: 3.85, z: -0.05, ry: 0.38 },
  { x: 5.0, z: -0.3, ry: 0 },
  { x: 6.15, z: -0.05, ry: -0.38 },
];

/** Chapter 8: three floating screens (EHR order sign, case review, worklist); each steps forward in turn. */
export function Screens({ mats }: { mats: WorldMaterials }) {
  const screens = useMemo(() => {
    const loader = new THREE.TextureLoader();
    return SHOTS.map((src, i) => {
      const g = new THREE.Group();
      g.add(mesh(new RoundedBoxGeometry(1.66, 1.06, 0.05, 4, 0.025), mats.porcelain, `screen-${i}`));
      const tex = loader.load(src);
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = 4;
      const face = new THREE.Mesh(new THREE.PlaneGeometry(1.58, 0.98), new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
      face.position.z = 0.027;
      g.add(face);
      return { g, lift: 0 };
    });
  }, [mats]);

  useFrame((_, dt) => {
    const { t } = useWorld.getState();
    const on = t > 7.5 && t < 9.1;
    const d = Math.min(dt, 0.05);
    const rise = span(t, 7.55, 8.0) * (1 - span(t, 8.6, 9.0));
    const step = t >= 8 ? Math.min(2, Math.floor(span(t - 8, 0, 0.55) * 3)) : 0;
    screens.forEach((s, i) => {
      s.g.visible = on;
      if (!on) return;
      s.lift = damp(s.lift, i === step ? 1 : 0, 6, d);
      const L = LAYOUT[i];
      s.g.position.set(L.x, 1.2 - 1.5 * (1 - rise) + s.lift * 0.05, L.z + s.lift * 0.28);
      s.g.rotation.set(-pointer.y * 0.08, L.ry + pointer.x * 0.1, 0);
      s.g.scale.setScalar(1 + s.lift * 0.05);
    });
  });

  return (
    <>
      {screens.map((s, i) => (
        <primitive key={i} object={s.g} />
      ))}
    </>
  );
}

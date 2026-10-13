"use client";

import { useFrame, useThree } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import type { WorldMaterials } from "../objects/materials";
import { damp, pointer } from "../pointer";
import { span } from "../shared";
import { useWorld } from "../store";
import { FOLDER } from "./FolderScene";
import { PACKET } from "./PacketScene";

// Deterministic so the server-free poster renders and every visit match.
function rng(seed: number) {
  let s = seed;
  return () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646;
}

/**
 * Chapter 1, the problem: prior-auth forms fall and drift into piles around the chart, one batch
 * per week of paperwork. Forms near the cursor slide out of its way.
 */
export function Pile({ mats, count }: { mats: WorldMaterials; count: number }) {
  const { camera } = useThree();
  const data = useMemo(() => {
    const r = rng(7);
    return Array.from({ length: count }, (_, i) => {
      let x = 0;
      let z = 0;
      do {
        // Keep a clearing around the packet so chapter 7's seal is not buried in paperwork.
        const a = r() * Math.PI * 2;
        const rad = 0.95 + Math.pow(r(), 0.8) * 1.55;
        x = FOLDER.x + Math.cos(a) * rad;
        z = FOLDER.z + Math.sin(a) * rad * 0.8;
      } while (Math.hypot(x - PACKET.x, z - PACKET.z) < 0.85);
      return {
        rest: new THREE.Vector3(x, 0.008 + (i % 6) * 0.013, z),
        fromY: 4.5 + r() * 3,
        delay: r() * 0.7,
        rotY: r() * Math.PI * 2,
        tilt: (r() - 0.5) * 0.12,
        push: new THREE.Vector2(),
      };
    });
  }, [count]);
  const mesh = useMemo(() => {
    const m = new THREE.InstancedMesh(new RoundedBoxGeometry(0.42, 0.012, 0.56, 2, 0.005), mats.paper, count);
    m.castShadow = true;
    m.receiveShadow = true;
    m.frustumCulled = false;
    return m;
  }, [mats, count]);
  const tmp = useMemo(
    () => ({ o: new THREE.Object3D(), ray: new THREE.Raycaster(), ndc: new THREE.Vector2(), hit: new THREE.Vector3(), plane: new THREE.Plane(new THREE.Vector3(0, 1, 0), 0) }),
    [],
  );
  useFrame((_, dt) => {
    const { t } = useWorld.getState();
    const p = span(t, 0.55, 1.6); // starts falling as the camera turns toward chapter 1
    mesh.visible = p > 0;
    if (!mesh.visible) return;
    tmp.ray.setFromCamera(tmp.ndc.set(pointer.x, pointer.y), camera);
    const aimed = pointer.active && tmp.ray.ray.intersectPlane(tmp.plane, tmp.hit) !== null;
    const d = Math.min(dt, 0.05);
    data.forEach((s, i) => {
      const k = span(p, s.delay * 0.85, s.delay * 0.85 + 0.25);
      const fall = 1 - (1 - k) * (1 - k);
      let px = 0;
      let pz = 0;
      if (aimed && k >= 1) {
        const dx = s.rest.x - tmp.hit.x;
        const dz = s.rest.z - tmp.hit.z;
        const dist = Math.hypot(dx, dz);
        if (dist < 0.7 && dist > 1e-3) {
          const push = (0.7 - dist) * 0.45;
          px = (dx / dist) * push;
          pz = (dz / dist) * push;
        }
      }
      s.push.set(damp(s.push.x, px, 5, d), damp(s.push.y, pz, 5, d));
      tmp.o.position.set(s.rest.x + s.push.x, s.rest.y + (s.fromY - s.rest.y) * (1 - fall), s.rest.z + s.push.y);
      tmp.o.rotation.set(s.tilt + (1 - fall) * 1.2, s.rotY + (1 - fall) * 2, s.tilt * 0.5);
      tmp.o.scale.setScalar(k > 0 ? 1 : 0);
      tmp.o.updateMatrix();
      mesh.setMatrixAt(i, tmp.o.matrix);
    });
    mesh.instanceMatrix.needsUpdate = true;
  });
  return <primitive object={mesh} />;
}

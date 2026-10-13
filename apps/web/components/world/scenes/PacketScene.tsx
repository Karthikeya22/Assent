"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { mesh, type WorldMaterials } from "../objects/materials";
import { createStamp } from "../objects/stamp";
import { pointer } from "../pointer";
import { span } from "../shared";
import { useWorld } from "../store";

export const PACKET = new THREE.Vector3(2.4, 0, 0.6);
const TOP = 0.17; // packet top surface height

/**
 * Chapter 7: the chart pages settle into a packet, the stamp presses a green seal into it and an
 * approval ring answers. Chapter 10: the sealed packet rests in the light with the stamp beside it.
 */
export function PacketScene({ mats }: { mats: WorldMaterials }) {
  const built = useMemo(() => {
    const packet = new THREE.Group();
    const slabs = Array.from({ length: 4 }, (_, i) => {
      const m = mesh(new RoundedBoxGeometry(0.62, 0.035, 0.82, 3, 0.012), i % 2 ? mats.paper : mats.porcelain, `slab-${i}`);
      m.position.y = 0.02 + i * 0.038;
      m.rotation.y = (i - 1.5) * 0.025;
      packet.add(m);
      return m;
    });
    const band = mesh(new RoundedBoxGeometry(0.64, 0.02, 0.14, 3, 0.008), mats.glaze, "band");
    band.position.set(0, TOP - 0.02, -0.25);
    packet.add(band);
    const { stamp, seal } = createStamp(mats);
    seal.position.set(0.05, TOP, 0.12);
    packet.add(seal);
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.28, 0.008, 8, 96),
      new THREE.MeshBasicMaterial({ color: mats.glaze.color, transparent: true, opacity: 0, depthWrite: false }),
    );
    ring.rotation.x = Math.PI / 2;
    ring.position.set(0.05, TOP + 0.02, 0.12);
    packet.add(ring);
    return { packet, slabs, band, stamp, seal, ring };
  }, [mats]);

  useFrame(() => {
    const { t } = useWorld.getState();
    const { packet, slabs, band, stamp, seal, ring } = built;
    const visible = t > 6.55;
    packet.visible = stamp.visible = visible;
    if (!visible) return;
    packet.position.copy(PACKET);
    const pack = span(t, 6.7, 7.15);
    slabs.forEach((s, i) => s.scale.setScalar(span(pack, i * 0.18, i * 0.18 + 0.4)));
    band.scale.setScalar(span(pack, 0.8, 1));

    // Hover, tilt toward the cursor, press, leave the seal, lift.
    const press = span(t, 7.15, 7.27);
    const lift = span(t, 7.3, 7.42);
    const rest = span(t, 9.4, 10); // drifts aside for the closing still life
    const hoverY = 1.25;
    const y = hoverY - (hoverY - TOP) * press + (hoverY - TOP) * lift * (1 - rest);
    stamp.position.set(PACKET.x + 0.05 + 0.6 * rest, y * (1 - rest), PACKET.z + 0.12 - 0.35 * rest);
    const free = (1 - press) * (1 - rest) + lift * (1 - rest);
    stamp.rotation.set(pointer.y * 0.2 * free, 0, -pointer.x * 0.25 * free);
    stamp.scale.set(0.55, 0.55 * (1 - 0.08 * (press - lift > 0.9 ? 1 : 0)), 0.55);

    seal.scale.setScalar(span(t, 7.25, 7.3) * 0.62);
    const approve = span(t, 7.42, 7.55);
    const m = ring.material as THREE.MeshBasicMaterial;
    ring.scale.setScalar(0.6 + approve * 0.8);
    m.opacity = approve * (1 - span(t, 7.6, 8.0)) + span(t, 9.6, 10) * 0.6;
    packet.rotation.y = pointer.x * 0.15 * span(t, 9.5, 10);
  });

  return (
    <>
      <primitive object={built.packet} />
      <primitive object={built.stamp} />
    </>
  );
}

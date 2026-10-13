"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import type { WorldMaterials } from "../objects/materials";
import { createScales } from "../objects/scales";
import { pointer } from "../pointer";
import { span } from "../shared";
import { useWorld } from "../store";

/**
 * Chapter 6, argue with the payer: the scales rise beside the lattice. The adversary's objections
 * tip the beam; the advocate's rebuttal rights it, short of level, because one point was conceded.
 */
export function ScalesScene({ mats }: { mats: WorldMaterials }) {
  const s = useMemo(() => createScales(mats), [mats]);
  useFrame((state) => {
    const { t } = useWorld.getState();
    // Rises for the argument, sinks again once the packet is sealed.
    const up = span(t, 5.35, 6.0) * (1 - span(t, 6.7, 7.05));
    s.group.visible = t > 5.3 && up > 0.001;
    if (!s.group.visible) return;
    s.group.position.set(3.05, -1.4 * (1 - up), -0.75);
    const a = t >= 6 ? span(t - 6, 0, 0.55) : 0; // the argue beat (same window as the lattice rays)
    const hit = span(a, 0.05, 0.3);
    const rebut = span(a, 0.35, 0.55);
    const near = 1 - span(t, 7.2, 7.6);
    s.beam.rotation.z = -0.24 * hit + 0.17 * rebut + (pointer.x * 0.05 + Math.sin(state.clock.elapsedTime * 0.9) * 0.008) * near;
    for (const pan of s.pans) pan.rotation.z = -s.beam.rotation.z; // pans hang plumb
  });
  return <primitive object={s.group} scale={1.1} />;
}

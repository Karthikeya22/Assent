"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import { createFolder } from "../objects/folder";
import type { WorldMaterials } from "../objects/materials";
import { pointer } from "../pointer";
import { span } from "../shared";
import { useWorld } from "../store";

/** World position of the folder (asset A); the chart pages start here in chapter 3. */
export const FOLDER = { x: 1.0, y: 0.84, z: 0, scale: 1.5 };
// Once opened, the folder steps back to the left so the lattice and timeline own the stage.
const RETREAT = { x: -1.25, z: -2.4, ry: 0.5 };

/**
 * Chapter 0 hero: the folder floats, tilts toward the cursor, its sheets lean away from it.
 * Chapter 3: the front cover swings open and the sheets leave (the lattice's pages take over).
 */
export function FolderScene({ mats }: { mats: WorldMaterials }) {
  const f = useMemo(() => createFolder(mats), [mats]);
  useFrame((state) => {
    const { t } = useWorld.getState();
    const time = state.clock.elapsedTime;
    const hero = 1 - span(t, 0.6, 1.4); // cursor play fades as the story starts
    const g = f.group;
    const back = span(t, 3.5, 4.3);
    g.position.set(
      FOLDER.x + (RETREAT.x - FOLDER.x) * back,
      FOLDER.y + Math.sin(time * 1.05) * 0.02 * hero,
      FOLDER.z + (RETREAT.z - FOLDER.z) * back,
    );
    g.rotation.y = -0.35 + (RETREAT.ry + 0.35) * back + pointer.x * 0.21 * hero;
    g.rotation.x = -pointer.y * 0.12 * hero;
    f.sheets.forEach((s, i) => {
      // Lean away from the cursor, more for the sheets further back; a faint idle breath.
      s.rotation.x = f.rest[i] + (-pointer.y * 0.04 - 0.02) * (i + 1) * 0.5 * hero + Math.sin(time * 1.3 + i) * 0.006;
      s.visible = t < 3.12;
    });
    f.hinge.rotation.x = -1.55 * span(t, 2.95, 3.45);
  });
  return <primitive object={f.group} scale={FOLDER.scale} />;
}

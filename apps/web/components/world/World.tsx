"use client";

/**
 * The one continuous world behind the landing (DESIGN.md, docs/design/storyboard.md). A single
 * fixed canvas; Lenis scroll (via useWorld) flies the camera along camera.ts and every scene reads
 * the chapter coordinate t inside useFrame. Nothing here re-renders React per frame.
 */
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { filmShift, poseAt } from "./camera";
import { createMaterials } from "./objects/materials";
import { damp, pointer, setTarget, stepPointer } from "./pointer";
import { Dials } from "./scenes/Dials";
import { FolderScene } from "./scenes/FolderScene";
import { LatticeScene } from "./scenes/LatticeScene";
import { PacketScene } from "./scenes/PacketScene";
import { Pile } from "./scenes/Pile";
import { ScalesScene } from "./scenes/ScalesScene";
import { Screens } from "./scenes/Screens";
import { readPalette, type Palette } from "./shared";
import { useWorld } from "./store";

export type Tier = "high" | "mid";

function Rig() {
  const { camera, size } = useThree();
  const look = useMemo(() => new THREE.Vector3(), []);
  const target = useMemo(() => new THREE.Vector3(), []);
  useFrame((_, dt) => {
    const d = Math.min(dt, 0.05);
    stepPointer(d);
    const pose = poseAt(useWorld.getState().t);
    // Narrow screens: dolly back so the subject fits above the stacked copy.
    const back = size.width < 768 ? 1.35 : 1;
    const bx = pose.look[0] + (pose.pos[0] - pose.look[0]) * back;
    const by = pose.look[1] + (pose.pos[1] - pose.look[1]) * back;
    const bz = pose.look[2] + (pose.pos[2] - pose.look[2]) * back;
    // Pointer parallax: a few degrees of orbit, so the world answers the cursor everywhere.
    camera.position.set(
      damp(camera.position.x, bx + pointer.x * 0.22, 6, d),
      damp(camera.position.y, by + pointer.y * 0.12, 6, d),
      damp(camera.position.z, bz, 6, d),
    );
    target.set(...pose.look);
    look.set(damp(look.x, target.x, 6, d), damp(look.y, target.y, 6, d), damp(look.z, target.z, 6, d));
    camera.lookAt(look);
    // Desktop: shift the film so the subject sits opposite the copy. Narrow screens stack the
    // copy under the scene, so the film lifts the subject into the upper half instead.
    const cam = camera as THREE.PerspectiveCamera;
    const narrow = size.width < 768;
    const fx = narrow ? 0 : filmShift(useWorld.getState().t);
    cam.filmOffset = damp(cam.filmOffset, fx, 6, d);
    if (narrow) cam.setViewOffset(size.width, size.height, 0, size.height * 0.16, size.width, size.height);
    else if (cam.view) cam.clearViewOffset();
    cam.updateProjectionMatrix();
  });
  return null;
}

function Lights({ shadows }: { shadows: boolean }) {
  // The folder's img2threejs lighting pass: low hemisphere fill, warm upper-left key, cool fill, rim.
  const key = useMemo(() => {
    const l = new THREE.DirectionalLight("#fff6ea", 2.9);
    l.position.set(-3.5, 7, 6);
    l.target.position.set(1.2, 0, 0);
    l.castShadow = shadows;
    l.shadow.mapSize.set(2048, 2048);
    l.shadow.radius = 8;
    l.shadow.bias = -0.0004;
    Object.assign(l.shadow.camera, { left: -5, right: 8, top: 6, bottom: -4, near: 1, far: 22 });
    return l;
  }, [shadows]);
  return (
    <>
      <hemisphereLight args={["#ffffff", "#d9e0dc", 0.55]} />
      <primitive object={key} />
      <primitive object={key.target} />
      <directionalLight color="#eef4ff" intensity={0.45} position={[3, 1.2, 3]} />
      <directionalLight color="#ffffff" intensity={0.7} position={[3, 2, -4]} />
    </>
  );
}

function Floor() {
  return (
    <mesh rotation-x={-Math.PI / 2} receiveShadow>
      <planeGeometry args={[40, 40]} />
      <shadowMaterial opacity={0.14} />
    </mesh>
  );
}

export default function World({ tier, onReady }: { tier: Tier; onReady?: () => void }) {
  const [pal, setPal] = useState<Palette | null>(null);
  const mats = useMemo(() => createMaterials(), []);
  useEffect(() => {
    setPal(readPalette());
    const move = (e: PointerEvent) => setTarget(e.clientX, e.clientY, window.innerWidth, window.innerHeight);
    window.addEventListener("pointermove", move, { passive: true });
    return () => window.removeEventListener("pointermove", move);
  }, []);
  if (!pal) return null;
  const shadows = tier === "high";
  return (
    <Canvas
      dpr={tier === "high" ? [1, 1.75] : [1, 1.25]}
      shadows={shadows ? "soft" : false}
      camera={{ fov: 35, position: [2.05, 1.25, 5.1], near: 0.1, far: 60 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance", toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 0.95 }}
      eventSource={typeof document !== "undefined" ? document.body : undefined}
      eventPrefix="client"
      onCreated={() => onReady?.()}
      aria-hidden="true"
    >
      <Rig />
      <Lights shadows={shadows} />
      <Floor />
      <FolderScene mats={mats} />
      <Pile mats={mats} count={tier === "high" ? 190 : 120} />
      <LatticeScene mats={mats} pal={pal} />
      <ScalesScene mats={mats} />
      <PacketScene mats={mats} />
      <Screens mats={mats} />
      <Dials mats={mats} pal={pal} />
    </Canvas>
  );
}

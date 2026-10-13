"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import evals from "@/public/evals/latest.json";
import { mesh, roundedDisc, type WorldMaterials } from "../objects/materials";
import { span, type Palette } from "../shared";
import { useWorld } from "../store";

const fillVert = /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`;
const fillFrag = /* glsl */ `
uniform vec3 uColor; uniform float uFill; varying vec2 vUv;
void main(){
  if (vUv.x > uFill) discard;
  gl_FragColor = vec4(uColor, 1.0);
  #include <colorspace_fragment>
}`;

type Row = { n_cases: number; case_accuracy: number; false_ready: number; unsupported_claim_rate: number | null };

/**
 * Chapter 9, proof: porcelain dials rise and sweep once to the locked test split's numbers, then
 * hold. Values come from public/evals/latest.json (the same file the /evals page reads).
 */
export function Dials({ mats, pal }: { mats: WorldMaterials; pal: Palette }) {
  const values = useMemo(() => {
    // Locked test split, aggregated over the three service families.
    const rows = (evals as unknown as { test: { per_family: Row[] } }).test.per_family;
    const n = rows.reduce((s, r) => s + r.n_cases, 0);
    const correct = rows.reduce((s, r) => s + r.case_accuracy * r.n_cases, 0);
    const falseReady = rows.reduce((s, r) => s + r.false_ready, 0);
    const unsupported = rows.reduce((s, r) => s + (r.unsupported_claim_rate ?? 0) * r.n_cases, 0) / n;
    return [
      correct / n, // decisions correct (16 / 18)
      1 - falseReady / n, // no unproven case marked ready
      1 - unsupported, // claims backed by a verified quote
    ];
  }, []);
  const dials = useMemo(
    () =>
      values.map((v, i) => {
        const g = new THREE.Group();
        const face = mesh(roundedDisc(0.27, 0.06, 0.02), mats.porcelain, `dial-${i}`);
        face.rotation.x = Math.PI / 2;
        g.add(face);
        const stand = mesh(new RoundedBoxGeometry(0.16, 0.3, 0.1, 3, 0.03), mats.porcelain, "stand");
        stand.position.set(0, -0.36, -0.02);
        g.add(stand);
        const mat = new THREE.ShaderMaterial({ vertexShader: fillVert, fragmentShader: fillFrag, uniforms: { uColor: { value: pal.signal }, uFill: { value: 0 } } });
        const arc = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.03, 12, 128), mat);
        arc.position.z = 0.035;
        arc.rotation.z = Math.PI / 2;
        arc.scale.x = -1; // fills clockwise from 12 o'clock
        g.add(arc);
        const track = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.012, 8, 128), mats.paper);
        track.position.z = 0.032;
        g.add(track);
        return { g, mat, v, i };
      }),
    [values, mats, pal],
  );

  useFrame(() => {
    const { t } = useWorld.getState();
    const on = t > 8.45 && t < 10;
    const rise = span(t, 8.5, 9.0) * (1 - span(t, 9.6, 9.95));
    const sweep = span(t, 8.95, 9.45);
    for (const d of dials) {
      d.g.visible = on;
      if (!on) continue;
      d.g.position.set(-2.5 + d.i * 0.7, 0.42 - 1.1 * (1 - span(rise, d.i * 0.12, d.i * 0.12 + 0.7)), 1.2);
      d.mat.uniforms.uFill.value = d.v * span(sweep, d.i * 0.1, d.i * 0.1 + 0.8);
    }
  });

  return (
    <>
      {dials.map((d) => (
        <primitive key={d.i} object={d.g} />
      ))}
    </>
  );
}

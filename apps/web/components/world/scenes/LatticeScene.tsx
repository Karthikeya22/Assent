"use client";

/**
 * Chapters 2-6 (policy, chart, prove, verify, argue): the real L39240 criteria tree as a porcelain
 * lattice above the folder, the chart pages that fly out of it into a timeline, evidence threads,
 * the rejected quote and the payer adversary's rays. Event timing comes from the tested pure
 * timeline (components/lattice/timeline.ts); this file only draws it.
 */
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { POLICY, layout, type LNode } from "@/components/lattice/layout";
import { ringFill, storyFrame, type Frame } from "@/components/lattice/timeline";
import { createMagnifier } from "../objects/magnifier";
import type { WorldMaterials } from "../objects/materials";
import { pointer } from "../pointer";
import { span, type Palette } from "../shared";
import { useWorld } from "../store";
import { FOLDER } from "./FolderScene";

/** Lattice group origin in the world: floating above and behind the folder. */
export const LATTICE = new THREE.Vector3(0.05, 2.0, -1.4);
const PACKET_LOCAL = new THREE.Vector3(2.35, -2.0, 2.0); // PacketScene's packet, in lattice space

/** Story progress for the timeline: each chapter's beat plays while its text is read (local 0..0.55). */
export function storyP(t: number): number {
  if (t <= 2) return 0;
  if (t >= 7) return 1;
  const i = Math.floor(t);
  return (i - 2 + span(t - i, 0, 0.55)) / 5;
}

const PAGES = 12;
const ROWS = 16;
const PAGE_W = 1.0;
const PAGE_H = 1.32;
const STACK = new THREE.Vector3(FOLDER.x, FOLDER.y, FOLDER.z).sub(LATTICE);

function fanPose(i: number, out: THREE.Vector3) {
  return out.set(-0.35 + i * 0.3, -1.72, 0.45);
}

const pageVert = /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`;
const pageFrag = /* glsl */ `
uniform vec3 uInk; uniform vec3 uSig; uniform vec3 uPaper; uniform float uHiRow; uniform float uHiAmt; uniform float uSeed;
varying vec2 vUv;
float hash(float n){ return fract(sin(n) * 43758.5453); }
void main(){
  float rows = ${ROWS.toFixed(1)};
  float r = floor((1.0 - vUv.y) * rows);
  float fy = fract((1.0 - vUv.y) * rows);
  float len = r < 1.0 ? 0.35 : 0.42 + 0.48 * hash(r + uSeed * 13.0);
  float inLine = step(0.4, fy) * step(fy, 0.62) * step(0.1, vUv.x) * step(vUv.x, 0.1 + len * 0.8) * step(0.5, r) * step(r, rows - 1.5);
  float hi = abs(r - uHiRow) < 0.5 ? uHiAmt : 0.0;
  vec3 line = mix(uInk, uSig, hi);
  vec3 col = mix(uPaper, line, inLine * (0.55 + 0.45 * hi));
  gl_FragColor = vec4(col, 1.0);
  #include <colorspace_fragment>
}`;
const ringFrag = /* glsl */ `
uniform vec3 uColor; uniform float uFill; varying vec2 vUv;
void main(){
  if (vUv.x > uFill) discard;
  gl_FragColor = vec4(uColor, 1.0);
  #include <colorspace_fragment>
}`;

/** A fixed DOM label pinned to a 3D point (the canvas has no DOM of its own). */
function useLabel(className: string) {
  const [el] = useState(() => (typeof document === "undefined" ? null : document.createElement("span")));
  useEffect(() => {
    if (!el) return;
    el.className = className;
    el.setAttribute("aria-hidden", "true");
    el.style.opacity = "0";
    document.body.appendChild(el);
    return () => el.remove();
  }, [el, className]);
  return el;
}

export function LatticeScene({ mats, pal }: { mats: WorldMaterials; pal: Palette }) {
  const nodes = useMemo(() => layout(), []);
  const byKey = useMemo(() => new Map(nodes.map((n) => [n.key, n])), [nodes]);
  const frame = useRef<Frame>(storyFrame(nodes, 0));
  const group = useRef<THREE.Group>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  const leafMats = useMemo(
    () => ({
      wire: mats.porcelain,
      met: mats.glaze,
      amber: new THREE.MeshPhysicalMaterial({ color: pal.gap, roughness: 0.35, clearcoat: 0.5 }),
    }),
    [mats, pal],
  );
  const edgeMat = useMemo(() => new THREE.MeshStandardMaterial({ color: pal.ink3, transparent: true, opacity: 0, roughness: 0.6 }), [pal]);
  const pageMats = useMemo(
    () =>
      Array.from(
        { length: PAGES },
        (_, i) =>
          new THREE.ShaderMaterial({
            vertexShader: pageVert,
            fragmentShader: pageFrag,
            side: THREE.DoubleSide,
            uniforms: {
              uInk: { value: pal.ink3.clone().lerp(pal.paper, 0.45) }, // printed lines, softened toward the page
              uSig: { value: pal.signal },
              uPaper: { value: pal.paper },
              uHiRow: { value: 6 },
              uHiAmt: { value: 0 },
              uSeed: { value: i + 1 },
            },
          }),
      ),
    [pal],
  );

  // Geometry built once: edges as soft tubes, leaves as porcelain beads, logic nodes as rings.
  const edges = useMemo(
    () =>
      nodes
        .filter((n) => n.parent)
        .map((n) => {
          const a = new THREE.Vector3(...byKey.get(n.parent!)!.pos);
          const b = new THREE.Vector3(...n.pos);
          const mid = a.clone().lerp(b, 0.5).add(new THREE.Vector3(0, 0.08, 0.05));
          return { n, geo: new THREE.TubeGeometry(new THREE.QuadraticBezierCurve3(a, mid, b), 16, 0.006, 6, false) };
        }),
    [nodes, byKey],
  );
  const leafGeo = useMemo(() => new THREE.SphereGeometry(0.075, 32, 20), []);
  const haloGeo = useMemo(() => new THREE.TorusGeometry(0.11, 0.006, 8, 48), []);
  const ringGeo = useMemo(() => ({ bg: new THREE.TorusGeometry(1, 0.075, 12, 64), fill: new THREE.TorusGeometry(1, 0.11, 12, 96) }), []);
  const ringFill_ = useMemo(
    () =>
      new Map(
        nodes
          .filter((n) => n.kind !== "LEAF")
          .map((n) => [n.key, new THREE.ShaderMaterial({ vertexShader: pageVert, fragmentShader: ringFrag, uniforms: { uColor: { value: pal.signal }, uFill: { value: 0 } } })]),
      ),
    [nodes, pal],
  );
  const leafRefs = useRef(new Map<string, THREE.Mesh>());
  const haloRefs = useRef(new Map<string, THREE.Mesh>());
  const ringRefs = useRef(new Map<string, THREE.Group>());
  const pageRefs = useRef<THREE.Mesh[]>([]);
  const pageGroup = useRef<THREE.Group>(null);

  const mag = useMemo(() => createMagnifier(mats), [mats]);
  const labels = {
    root: useLabel("pointer-events-none fixed top-0 left-0 z-[5] -translate-x-1/2 font-mono text-xs tracking-wide text-ink-2 transition-opacity duration-300"),
    status: useLabel("pointer-events-none fixed top-0 left-0 z-[5] whitespace-nowrap rounded-[var(--radius-control)] bg-paper-raised/90 px-2 py-1 font-mono text-xs text-gap shadow-[var(--shadow-float)]"),
    hover: useLabel("pointer-events-none fixed top-0 left-0 z-[5] max-w-[240px] -translate-x-1/2 rounded-[var(--radius-control)] border border-rule bg-paper-raised px-2.5 py-1.5 text-xs leading-snug text-ink shadow-[var(--shadow-float)]"),
  };
  useEffect(() => {
    if (labels.root) labels.root.textContent = POLICY;
  }, [labels.root]);
  useEffect(() => {
    if (labels.hover) labels.hover.textContent = hovered ? (byKey.get(hovered)?.label ?? "") : "";
  }, [hovered, labels.hover, byKey]);

  const ribbons = useMemo(
    () =>
      Array.from({ length: 9 }, () => {
        const geo = new THREE.BufferGeometry();
        geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(220 * 3), 3));
        const mat = new THREE.PointsMaterial({ size: 0.034, color: pal.signal, transparent: true, depthWrite: false });
        const jitter = Array.from({ length: 220 }, (_, i) => new THREE.Vector3(Math.sin(i * 12.9898), Math.sin(i * 78.233), Math.sin(i * 39.425)).multiplyScalar(((i * 0.618) % 1) * 0.9));
        return { pts: new THREE.Points(geo, mat), geo, mat, jitter };
      }),
    [pal],
  );
  const rays = useMemo(
    () =>
      Array.from({ length: 3 }, () => {
        const mat = new THREE.MeshBasicMaterial({ color: pal.adversary, transparent: true, opacity: 0, depthWrite: false });
        return { mesh: new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, 1, 8, 1, true), mat), mat };
      }),
    [pal],
  );
  const tmp = useMemo(
    () => ({
      a: new THREE.Vector3(),
      b: new THREE.Vector3(),
      v: new THREE.Vector3(),
      up: new THREE.Vector3(0, 1, 0),
      plane: new THREE.Plane(new THREE.Vector3(0, 0, 1), 1.0),
      ray: new THREE.Raycaster(),
      ndc: new THREE.Vector2(),
      hit: new THREE.Vector3(),
      minX: Math.min(...nodes.filter((n) => n.kind === "LEAF").map((n) => n.pos[0])),
    }),
    [nodes],
  );
  const { camera, size } = useThree();

  useFrame((state) => {
    const { t } = useWorld.getState();
    const g = group.current;
    if (!g) return;
    const on = t > 1.55 && t < 7.7;
    g.visible = on;
    mag.group.visible = t > 3.6 && t < 5.25;
    for (const el of Object.values(labels)) if (el && !on) el.style.opacity = "0";
    if (!on) return;
    const f = (frame.current = storyFrame(nodes, storyP(t)));
    const appear = span(t, 1.55, 2.2) * (1 - span(t, 7.1, 7.6));
    g.scale.setScalar(0.92 + 0.08 * appear);

    const place = (el: HTMLElement | null, p: THREE.Vector3, dx: number, dy: number, opacity: number) => {
      if (!el) return;
      tmp.v.copy(p).project(camera);
      el.style.transform = `translate(${(tmp.v.x * 0.5 + 0.5) * size.width + dx}px, ${(-tmp.v.y * 0.5 + 0.5) * size.height + dy}px)`;
      el.style.opacity = String(opacity);
    };
    const world = (pos: [number, number, number]) => g.localToWorld(tmp.b.set(...pos));

    edgeMat.opacity = 0.55 * appear;
    for (const n of nodes) {
      const grow = span(f.build, n.depth * 0.17, n.depth * 0.17 + 0.35) * appear;
      if (n.kind === "LEAF") {
        const m = leafRefs.current.get(n.key);
        const h = haloRefs.current.get(n.key);
        if (!m || !h) continue;
        const s = f.leaves[n.key];
        m.material = s === "met" ? leafMats.met : s === "amber" ? leafMats.amber : leafMats.wire;
        m.scale.setScalar(grow * (hovered === n.key ? 1.35 : 1));
        const p = f.pulse[n.key] ?? 0;
        h.scale.setScalar(1 + (1 - p) * 1.8);
        (h.material as THREE.MeshBasicMaterial).opacity = p * 0.8;
      } else {
        const r = ringRefs.current.get(n.key);
        const mat = ringFill_.get(n.key);
        if (!r || !mat) continue;
        r.scale.setScalar(grow * (n.parent === null ? 0.2 : 0.12));
        mat.uniforms.uFill.value += (ringFill(nodes, f.leaves, n.key) - mat.uniforms.uFill.value) * 0.06;
      }
    }

    // Pages: inside the open folder -> a dated timeline under the lattice -> into the packet.
    const show = t > 3.1;
    const fly = span(t, 3.1, 3.55);
    const pack = span(t, 6.75, 7.3);
    if (pageGroup.current) pageGroup.current.visible = show && pack < 1;
    let hiPage = f.pageHi.page;
    let hiAmt = f.pageHi.amt;
    if (mag.group.visible) {
      // The magnifier follows the cursor along the timeline; the line under the lens lights up.
      tmp.ndc.set(pointer.x, pointer.y);
      tmp.ray.setFromCamera(tmp.ndc, camera);
      const aimed = pointer.active && tmp.ray.ray.intersectPlane(tmp.plane, tmp.hit) !== null;
      const fan5 = world(fanPose(5, tmp.a).toArray() as [number, number, number]);
      const target = aimed ? tmp.hit : fan5;
      target.x = THREE.MathUtils.clamp(target.x, LATTICE.x - 0.35, LATTICE.x + 3.0);
      target.y = THREE.MathUtils.clamp(target.y, 0.15, 1.2);
      mag.group.position.lerp(tmp.v.set(target.x, target.y + 0.05, -0.75), 0.12);
      mag.group.rotation.set(-0.15, -0.2, 0.25);
      const u = Math.round((mag.group.position.x - LATTICE.x + 0.35) / 0.3);
      if (u >= 0 && u < PAGES) {
        hiPage = u;
        hiAmt = Math.max(hiAmt, span(t, 3.65, 3.9) * (1 - span(t, 5.0, 5.2)));
      }
    }
    pageRefs.current.forEach((m, i) => {
      fanPose(i, tmp.a);
      m.position.copy(STACK).lerp(tmp.a, fly).lerp(PACKET_LOCAL, pack);
      m.rotation.set(THREE.MathUtils.lerp(0, -0.2, fly), THREE.MathUtils.lerp(-0.35, 0, fly), 0);
      m.scale.setScalar(THREE.MathUtils.lerp(0.62, 0.26, fly) * (1 - pack * 0.6));
      const u = (m.material as THREE.ShaderMaterial).uniforms;
      u.uHiAmt.value = hiPage === i ? hiAmt : 0;
    });

    // Evidence threads: particles along a lifted curve from a page line to its criterion.
    ribbons.forEach((r, idx) => {
      const rib = f.ribbons[idx];
      r.pts.visible = !!rib && rib.head > 0 && show;
      if (!rib || !r.pts.visible) return;
      const page = pageRefs.current[rib.page];
      const dst = byKey.get(rib.to);
      if (!page || !dst) return;
      const a = page.position.clone().add(new THREE.Vector3(-0.05, 0.08, 0.02));
      const b = new THREE.Vector3(...dst.pos);
      const curve = new THREE.CatmullRomCurve3([a, a.clone().lerp(b, 0.35).add(new THREE.Vector3(0, 0.6, 0.35)), a.clone().lerp(b, 0.75).add(new THREE.Vector3(0, 0.3, 0.2)), b]);
      const pos = r.geo.getAttribute("position") as THREE.BufferAttribute;
      const shown = Math.min(220, Math.floor((rib.head / 0.38) * 220) + 1);
      for (let i = 0; i < shown; i++) {
        const k = Math.max(0, Math.min(1, rib.head - (i / 220) * 0.38));
        curve.getPoint(k, tmp.v).addScaledVector(r.jitter[i], 0.07 * (1 - k) + 0.008);
        pos.setXYZ(i, tmp.v.x, tmp.v.y, tmp.v.z);
      }
      r.geo.setDrawRange(0, shown);
      pos.needsUpdate = true;
      r.mat.color.copy(rib.color === "fail" ? pal.fail : pal.signal);
      r.mat.opacity = rib.flicker ? (Math.sin(state.clock.elapsedTime * 55) > 0 ? 1 : 0.15) : 1;
    });

    // Payer adversary (purple, from outside the packet) and the advocate's answer (green).
    rays.forEach((p, i) => {
      const ray = f.rays[i];
      p.mesh.visible = !!ray && ray.amt > 0.01;
      if (!ray || !p.mesh.visible) return;
      const from = ray.color === "adversary" ? tmp.a.set(3.3, 2.4, 0.6) : tmp.a.set(-1.3, 2.2, 0.6);
      const to = byKey.get(ray.to)!.pos;
      const sweep = ray.color === "adversary" ? span(ray.amt, 0.2, 0.85) : 1;
      const end = tmp.b.set(THREE.MathUtils.lerp(tmp.minX, to[0], sweep), to[1], to[2]);
      end.lerpVectors(from, end, span(ray.amt, 0, 0.2));
      const len = from.distanceTo(end);
      p.mesh.position.copy(from).lerp(end, 0.5);
      p.mesh.quaternion.setFromUnitVectors(tmp.up, end.clone().sub(from).normalize());
      p.mesh.scale.set(1, Math.max(len, 0.001), 1);
      p.mat.color.copy(ray.color === "adversary" ? pal.adversary : pal.signal);
      p.mat.opacity = 0.85 * Math.min(1, ray.amt * 3);
    });

    const root = nodes.find((n) => n.parent === null)!;
    place(labels.root, world(root.pos), 0, -46, appear * span(f.build, 0, 0.3));
    const l = f.label;
    if (labels.status) {
      if (l && labels.status.textContent !== l.text) labels.status.textContent = l.text;
      if (l) place(labels.status, world(byKey.get(l.key)!.pos), 16, -10, l.amt);
      else labels.status.style.opacity = "0";
    }
    if (labels.hover) {
      const h = hovered ? byKey.get(hovered) : null;
      if (h) place(labels.hover, world(h.pos), 0, 20, 1);
      else labels.hover.style.opacity = "0";
    }
  });

  return (
    <>
      <group ref={group} position={LATTICE}>
        {edges.map((e) => (
          <mesh key={e.n.key} geometry={e.geo} material={edgeMat} />
        ))}
        {nodes.map((n: LNode) =>
          n.kind === "LEAF" ? (
            <group key={n.key} position={n.pos}>
              <mesh
                ref={(m) => {
                  if (m) leafRefs.current.set(n.key, m);
                }}
                geometry={leafGeo}
                material={leafMats.wire}
                castShadow
                onPointerOver={() => setHovered(n.key)}
                onPointerOut={() => setHovered((k) => (k === n.key ? null : k))}
              />
              <mesh
                ref={(m) => {
                  if (m) haloRefs.current.set(n.key, m);
                }}
                geometry={haloGeo}
              >
                <meshBasicMaterial color={pal.signal} transparent opacity={0} depthWrite={false} />
              </mesh>
            </group>
          ) : (
            <group
              key={n.key}
              position={n.pos}
              ref={(g) => {
                if (g) ringRefs.current.set(n.key, g);
              }}
            >
              <mesh geometry={ringGeo.bg} material={mats.porcelain} castShadow />
              <mesh geometry={ringGeo.fill} material={ringFill_.get(n.key)} rotation={[0, 0, Math.PI / 2]} scale={[-1, 1, 1]} />
            </group>
          ),
        )}
        <group ref={pageGroup}>
          {pageMats.map((mat, i) => (
            <mesh
              key={i}
              material={mat}
              castShadow
              ref={(m) => {
                if (m) pageRefs.current[i] = m;
              }}
            >
              <planeGeometry args={[PAGE_W, PAGE_H]} />
            </mesh>
          ))}
        </group>
        {ribbons.map((r, i) => (
          <primitive key={`r${i}`} object={r.pts} />
        ))}
        {rays.map((r, i) => (
          <primitive key={`y${i}`} object={r.mesh} />
        ))}
      </group>
      <primitive object={mag.group} scale={0.42} />
    </>
  );
}

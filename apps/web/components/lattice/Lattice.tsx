"use client";

/**
 * The Evidence Lattice (FRONTEND §5.1): chart pages on the left, the real L39240 criteria tree on
 * the right. All geometry is procedural; per-frame state is written straight to three.js objects
 * in useFrame (never through React state), driven by the pure timeline in ./timeline.
 */
import { Canvas, useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import * as THREE from "three";
import { POLICY, layout, type LNode } from "./layout";
import { useStory } from "./store";
import { heroFrame, ringFill, span, storyFrame, type Frame } from "./timeline";


type Palette = Record<
  "ink" | "ink3" | "rule" | "paper" | "signal" | "gap" | "fail" | "adversary",
  THREE.Color
>;

function readPalette(): Palette {
  const css = getComputedStyle(document.documentElement);
  const c = (v: string) =>
    new THREE.Color(css.getPropertyValue(v).trim() || "#888");
  return {
    ink: c("--ink"),
    ink3: c("--ink-3"),
    rule: c("--rule"),
    paper: c("--paper-raised"),
    signal: c("--signal"),
    gap: c("--gap"),
    fail: c("--fail"),
    adversary: c("--adversary"),
  };
}

const PAGES = 12;
const ROWS = 16;
const PAGE_W = 1.0;
const PAGE_H = 1.32;

function stackPose(i: number) {
  return {
    pos: new THREE.Vector3(
      -1.95 + i * 0.025,
      0.35 - i * 0.02,
      -0.55 + i * 0.09,
    ),
    rot: new THREE.Euler(-0.05, 0.42 + i * 0.015, (i - 6) * 0.012),
    scale: 1,
  };
}
function fanPose(i: number) {
  return {
    pos: new THREE.Vector3(-2.45 + i * 0.42, -1.3, 0.35),
    rot: new THREE.Euler(-0.15, 0, 0),
    scale: 0.42,
  };
}
/** Where a page's highlighted line sits in world space (ribbon source). */
function lineAnchor(page: THREE.Object3D, row: number): THREE.Vector3 {
  const local = new THREE.Vector3(
    -0.08,
    PAGE_H / 2 - ((row + 0.5) / ROWS) * PAGE_H,
    0.01,
  );
  return page.localToWorld(local);
}

const pageVert = /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`;
const pageFrag = /* glsl */ `
uniform vec3 uInk; uniform vec3 uSig; uniform vec3 uPaper; uniform float uHiRow; uniform float uHiAmt; uniform float uSeed; uniform float uOpacity;
varying vec2 vUv;
float hash(float n){ return fract(sin(n) * 43758.5453); }
void main(){
  float rows = ${ROWS.toFixed(1)};
  float r = floor((1.0 - vUv.y) * rows);
  float fy = fract((1.0 - vUv.y) * rows);
  float len = r < 1.0 ? 0.35 : 0.42 + 0.48 * hash(r + uSeed * 13.0);
  float inLine = step(0.4, fy) * step(fy, 0.62) * step(0.1, vUv.x) * step(vUv.x, 0.1 + len * 0.8) * step(0.5, r) * step(r, rows - 1.5);
  float inner = step(0.03, vUv.x) * step(vUv.x, 0.97) * step(0.025, vUv.y) * step(vUv.y, 0.975);
  float hi = abs(r - uHiRow) < 0.5 ? uHiAmt : 0.0;
  vec3 line = mix(uInk, uSig, hi);
  float la = inLine * (0.5 + 0.5 * hi);
  vec3 col = mix(uPaper, line, la);
  float a = uOpacity * mix(0.6, 0.5, inner) * (inner > 0.5 ? 1.0 : 0.9) + la * 0.5;
  gl_FragColor = vec4(col, clamp(a, 0.0, 1.0));
}`;

const ringFrag = /* glsl */ `
uniform vec3 uColor; uniform float uFill; uniform float uOpacity; varying vec2 vUv;
void main(){ if (vUv.x > uFill) discard; gl_FragColor = vec4(uColor, uOpacity); }`;

type FrameRef = RefObject<Frame>;

function Driver({
  mode,
  nodes,
  frame,
}: {
  mode: "hero" | "story";
  nodes: LNode[];
  frame: FrameRef;
}) {
  useFrame((state) => {
    frame.current =
      mode === "hero"
        ? heroFrame(nodes, (state.clock.elapsedTime % 10) / 10)
        : storyFrame(nodes, useStory.getState().progress);
  }, -1);
  return null;
}

function Pages({
  pal,
  frame,
  pageRefs,
}: {
  pal: Palette;
  frame: FrameRef;
  pageRefs: RefObject<THREE.Mesh[]>;
}) {
  const group = useRef<THREE.Group>(null);
  const mats = useMemo(
    () =>
      Array.from(
        { length: PAGES },
        (_, i) =>
          new THREE.ShaderMaterial({
            vertexShader: pageVert,
            fragmentShader: pageFrag,
            transparent: true,
            depthWrite: false,
            side: THREE.DoubleSide,
            uniforms: {
              uInk: { value: pal.ink3 },
              uSig: { value: pal.signal },
              uPaper: { value: pal.paper },
              uHiRow: { value: 6 },
              uHiAmt: { value: 0 },
              uSeed: { value: i + 1 },
              uOpacity: { value: 0.9 },
            },
          }),
      ),
    [pal],
  );
  useFrame((state) => {
    const f = frame.current;
    if (!f || !group.current) return;
    group.current.rotation.y =
      Math.sin(state.clock.elapsedTime * 0.12) * 0.06 * (1 - f.fan);
    pageRefs.current.forEach((m, i) => {
      const a = stackPose(i);
      const b = fanPose(i);
      m.position.lerpVectors(a.pos, b.pos, f.fan);
      m.rotation.set(
        THREE.MathUtils.lerp(a.rot.x, b.rot.x, f.fan),
        THREE.MathUtils.lerp(a.rot.y, b.rot.y, f.fan),
        THREE.MathUtils.lerp(a.rot.z, b.rot.z, f.fan),
      );
      m.scale.setScalar(THREE.MathUtils.lerp(a.scale, b.scale, f.fan));
      const u = mats[i].uniforms;
      u.uHiAmt.value = f.pageHi.page === i ? f.pageHi.amt : 0;
    });
  });
  return (
    <group ref={group}>
      {mats.map((mat, i) => (
        <mesh
          key={i}
          material={mat}
          ref={(m) => {
            if (m) pageRefs.current[i] = m;
          }}
        >
          <planeGeometry args={[PAGE_W, PAGE_H]} />
        </mesh>
      ))}
    </group>
  );
}

function Edges({
  nodes,
  pal,
  frame,
}: {
  nodes: LNode[];
  pal: Palette;
  frame: FrameRef;
}) {
  const byKey = useMemo(() => new Map(nodes.map((n) => [n.key, n])), [nodes]);
  const items = useMemo(
    () =>
      nodes
        .filter((n) => n.parent)
        .map((n) => {
          const a = new THREE.Vector3(...byKey.get(n.parent!)!.pos);
          const b = new THREE.Vector3(...n.pos);
          const mid = a
            .clone()
            .lerp(b, 0.5)
            .add(new THREE.Vector3(0, 0.08, 0.05));
          return {
            node: n,
            geo: new THREE.TubeGeometry(
              new THREE.QuadraticBezierCurve3(a, mid, b),
              16,
              0.005,
              5,
              false,
            ),
            mat: new THREE.MeshBasicMaterial({
              color: pal.ink3,
              transparent: true,
              opacity: 0.45,
            }),
          };
        }),
    [nodes, byKey, pal],
  );
  useFrame(() => {
    const f = frame.current;
    if (!f) return;
    for (const e of items)
      e.mat.opacity =
        0.45 * span(f.build, e.node.depth * 0.17, e.node.depth * 0.17 + 0.35);
  });
  return (
    <>
      {items.map((e) => (
        <mesh key={e.node.key} geometry={e.geo} material={e.mat} />
      ))}
    </>
  );
}

function Leaf({
  n,
  pal,
  frame,
  onHover,
}: {
  n: LNode;
  pal: Palette;
  frame: FrameRef;
  onHover: (k: string | null) => void;
}) {
  const mesh = useRef<THREE.Mesh>(null);
  const halo = useRef<THREE.Mesh>(null);
  const mat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: pal.ink3,
        wireframe: true,
        roughness: 0.6,
      }),
    [pal],
  );
  const haloMat = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: pal.signal,
        transparent: true,
        opacity: 0,
      }),
    [pal],
  );
  useFrame(() => {
    const f = frame.current;
    if (!f || !mesh.current || !halo.current) return;
    const s = f.leaves[n.key];
    mat.wireframe = s === "wire";
    mat.color.copy(
      s === "met" ? pal.signal : s === "amber" ? pal.gap : pal.ink3,
    );
    mesh.current.scale.setScalar(
      span(f.build, n.depth * 0.17, n.depth * 0.17 + 0.35),
    );
    mesh.current.rotation.y += 0.004;
    const p = f.pulse[n.key] ?? 0;
    halo.current.scale.setScalar(1 + (1 - p) * 1.8);
    haloMat.opacity = p * 0.8;
  });
  return (
    <group position={n.pos}>
      <mesh
        ref={mesh}
        material={mat}
        onPointerOver={() => onHover(n.key)}
        onPointerOut={() => onHover(null)}
      >
        <icosahedronGeometry args={[0.075, 0]} />
      </mesh>
      <mesh ref={halo} material={haloMat}>
        <torusGeometry args={[0.1, 0.006, 6, 40]} />
      </mesh>
    </group>
  );
}

function Ring({
  n,
  nodes,
  pal,
  frame,
}: {
  n: LNode;
  nodes: LNode[];
  pal: Palette;
  frame: FrameRef;
}) {
  const g = useRef<THREE.Group>(null);
  const root = n.parent === null;
  const r = root ? 0.2 : 0.12;
  const fillMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: pageVert,
        fragmentShader: ringFrag,
        transparent: true,
        uniforms: {
          uColor: { value: pal.signal },
          uFill: { value: 0 },
          uOpacity: { value: 1 },
        },
      }),
    [pal],
  );
  const bgMat = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: pal.ink3,
        transparent: true,
        opacity: 0.35,
      }),
    [pal],
  );
  useFrame(() => {
    const f = frame.current;
    if (!f || !g.current) return;
    const target = ringFill(nodes, f.leaves, n.key);
    const u = fillMat.uniforms.uFill;
    u.value += (target - u.value) * 0.06; // fills clockwise as children resolve
    g.current.scale.setScalar(
      span(f.build, n.depth * 0.17, n.depth * 0.17 + 0.35),
    );
  });
  return (
    <group ref={g} position={n.pos}>
      <mesh material={bgMat}>
        <torusGeometry args={[r, root ? 0.01 : 0.007, 8, 64]} />
      </mesh>
      <mesh
        material={fillMat}
        rotation={[0, 0, Math.PI / 2]}
        scale={[-1, 1, 1]}
      >
        <torusGeometry args={[r, root ? 0.018 : 0.013, 8, 96]} />
      </mesh>
    </group>
  );
}

const MAX_RIBBONS = 9;
const PARTICLES = 220;
const TAIL = 0.38;

function Ribbons({
  nodes,
  pal,
  frame,
  pageRefs,
}: {
  nodes: LNode[];
  pal: Palette;
  frame: FrameRef;
  pageRefs: RefObject<THREE.Mesh[]>;
}) {
  const byKey = useMemo(() => new Map(nodes.map((n) => [n.key, n])), [nodes]);
  const pool = useMemo(
    () =>
      Array.from({ length: MAX_RIBBONS }, () => {
        const geo = new THREE.BufferGeometry();
        geo.setAttribute(
          "position",
          new THREE.BufferAttribute(new Float32Array(PARTICLES * 3), 3),
        );
        const mat = new THREE.PointsMaterial({
          size: 0.036,
          color: pal.signal,
          transparent: true,
          depthWrite: false,
          opacity: 1,
        });
        const jitter = Array.from({ length: PARTICLES }, () =>
          new THREE.Vector3().randomDirection().multiplyScalar(Math.random()),
        );
        return { pts: new THREE.Points(geo, mat), geo, mat, jitter };
      }),
    [pal],
  );
  useFrame((state) => {
    const f = frame.current;
    if (!f) return;
    pool.forEach((r, idx) => {
      const rib = f.ribbons[idx];
      r.pts.visible = !!rib && rib.head > 0;
      if (!rib || !r.pts.visible) return;
      const page = pageRefs.current[rib.page];
      const dst = byKey.get(rib.to);
      if (!page || !dst) return;
      const a = lineAnchor(page, rib.color === "fail" ? 5 : 6);
      const b = new THREE.Vector3(...dst.pos);
      const lift = a
        .clone()
        .lerp(b, 0.35)
        .add(new THREE.Vector3(0, 0.7, 0.4));
      const near = a
        .clone()
        .lerp(b, 0.75)
        .add(new THREE.Vector3(0, 0.35, 0.2));
      const curve = new THREE.CatmullRomCurve3([a, lift, near, b]);
      const pos = r.geo.getAttribute("position") as THREE.BufferAttribute;
      const shown = Math.min(
        PARTICLES,
        Math.floor((rib.head / TAIL) * PARTICLES) + 1,
      );
      const v = new THREE.Vector3();
      for (let i = 0; i < shown; i++) {
        const t = Math.max(0, Math.min(1, rib.head - (i / PARTICLES) * TAIL));
        curve
          .getPoint(t, v)
          .addScaledVector(r.jitter[i], 0.07 * (1 - t) + 0.008);
        pos.setXYZ(i, v.x, v.y, v.z);
      }
      r.geo.setDrawRange(0, shown);
      pos.needsUpdate = true;
      r.mat.color.copy(rib.color === "fail" ? pal.fail : pal.signal);
      r.mat.opacity = rib.flicker
        ? Math.sin(state.clock.elapsedTime * 55) > 0
          ? 1
          : 0.15
        : 1;
    });
  });
  return (
    <>
      {pool.map((r, i) => (
        <primitive key={i} object={r.pts} />
      ))}
    </>
  );
}

// The payer probes from outside the packet (top right); the advocate answers from the chart side.
const RAY_FROM = {
  adversary: new THREE.Vector3(3.3, 2.5, 0.6),
  signal: new THREE.Vector3(-1.3, 2.3, 0.6),
};

function Rays({
  nodes,
  pal,
  frame,
}: {
  nodes: LNode[];
  pal: Palette;
  frame: FrameRef;
}) {
  const byKey = useMemo(() => new Map(nodes.map((n) => [n.key, n])), [nodes]);
  const minX = useMemo(
    () =>
      Math.min(...nodes.filter((n) => n.kind === "LEAF").map((n) => n.pos[0])),
    [nodes],
  );
  const pool = useMemo(
    () =>
      Array.from({ length: 3 }, () => {
        const mat = new THREE.MeshBasicMaterial({
          color: pal.adversary,
          transparent: true,
          opacity: 0,
          depthWrite: false,
        });
        const mesh = new THREE.Mesh(
          new THREE.CylinderGeometry(0.009, 0.009, 1, 6, 1, true),
          mat,
        );
        return { mesh, mat };
      }),
    [pal],
  );
  const up = useMemo(() => new THREE.Vector3(0, 1, 0), []);
  useFrame(() => {
    const f = frame.current;
    if (!f) return;
    pool.forEach((p, i) => {
      const ray = f.rays[i];
      p.mesh.visible = !!ray && ray.amt > 0.01;
      if (!ray || !p.mesh.visible) return;
      const from = RAY_FROM[ray.color];
      const to = new THREE.Vector3(...byKey.get(ray.to)!.pos);
      // Adversary: reach the criteria row, sweep across it like a scanner, settle on the target.
      const sweepT = ray.color === "adversary" ? span(ray.amt, 0.2, 0.85) : 1;
      const scan = new THREE.Vector3(
        THREE.MathUtils.lerp(minX, to.x, sweepT),
        to.y,
        to.z,
      );
      const end = from.clone().lerp(scan, span(ray.amt, 0, 0.2));
      const len = from.distanceTo(end);
      p.mesh.position.copy(from).lerp(end, 0.5);
      p.mesh.quaternion.setFromUnitVectors(
        up,
        end.clone().sub(from).normalize(),
      );
      p.mesh.scale.set(1, Math.max(len, 0.001), 1);
      p.mat.color.copy(ray.color === "adversary" ? pal.adversary : pal.signal);
      p.mat.opacity = 0.85 * Math.min(1, ray.amt * 3);
    });
  });
  return (
    <>
      {pool.map((p, i) => (
        <primitive key={i} object={p.mesh} />
      ))}
    </>
  );
}

type Overlays = {
  root: RefObject<HTMLSpanElement | null>;
  status: RefObject<HTMLSpanElement | null>;
  hover: RefObject<HTMLSpanElement | null>;
};

/** Pins DOM labels to 3D nodes by projecting them to screen space each frame (no React work). */
function Project({
  nodes,
  frame,
  hovered,
  ov,
}: {
  nodes: LNode[];
  frame: FrameRef;
  hovered: string | null;
  ov: Overlays;
}) {
  const byKey = useMemo(() => new Map(nodes.map((n) => [n.key, n])), [nodes]);
  const root = useMemo(() => nodes.find((n) => n.parent === null)!, [nodes]);
  const v = useMemo(() => new THREE.Vector3(), []);
  useFrame(({ camera, size }) => {
    const place = (
      el: HTMLElement | null,
      pos: [number, number, number],
      dx: number,
      dy: number,
    ) => {
      if (!el) return;
      v.set(...pos).project(camera);
      el.style.transform = `translate(${(v.x * 0.5 + 0.5) * size.width + dx}px, ${(-v.y * 0.5 + 0.5) * size.height + dy}px)`;
    };
    const f = frame.current;
    place(ov.root.current, root.pos, 0, -48);
    const l = f?.label;
    const el = ov.status.current;
    if (el) {
      el.style.opacity = String(l?.amt ?? 0);
      if (l) {
        if (el.textContent !== l.text) el.textContent = l.text;
        place(el, byKey.get(l.key)!.pos, 14, -8);
      }
    }
    const h = hovered ? byKey.get(hovered) : null;
    if (h) place(ov.hover.current, h.pos, 0, 18);
  });
  return null;
}

function CameraRig({ frame }: { frame: FrameRef }) {
  const look = useMemo(() => new THREE.Vector3(0.15, 0.35, 0), []);
  useFrame((state) => {
    const f = frame.current;
    const back = f?.pullBack ?? 0;
    // Pointer parallax, about ±4° of camera orbit.
    const tx = 0.15 + state.pointer.x * 0.45;
    const ty = 0.45 + state.pointer.y * 0.3;
    const cam = state.camera;
    cam.position.x += (tx - cam.position.x) * 0.05;
    cam.position.y += (ty - cam.position.y) * 0.05;
    cam.position.z += (6.3 + back * 1.4 - cam.position.z) * 0.08;
    cam.lookAt(look);
  });
  return null;
}

export default function Lattice({
  mode,
  active,
  onReady,
}: {
  mode: "hero" | "story";
  active: boolean;
  onReady?: () => void;
}) {
  const nodes = useMemo(() => layout(), []);
  const [pal, setPal] = useState<Palette | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const frame = useRef<Frame>(
    mode === "hero" ? heroFrame(nodes, 0) : storyFrame(nodes, 0),
  );
  const pageRefs = useRef<THREE.Mesh[]>([]);
  const ov: Overlays = {
    root: useRef<HTMLSpanElement>(null),
    status: useRef<HTMLSpanElement>(null),
    hover: useRef<HTMLSpanElement>(null),
  };
  useEffect(() => setPal(readPalette()), []);
  if (!pal) return null;
  return (
    <div className="relative h-full w-full">
      <Canvas
        frameloop={active ? "always" : "never"}
        dpr={[1, 1.75]}
        camera={{ position: [0.15, 0.45, 6.3], fov: 38 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }}
        onCreated={() => onReady?.()}
        aria-hidden="true"
      >
        <ambientLight intensity={0.9} />
        <directionalLight position={[3, 4, 5]} intensity={1.2} />
        <Driver mode={mode} nodes={nodes} frame={frame} />
        <Pages pal={pal} frame={frame} pageRefs={pageRefs} />
        <Edges nodes={nodes} pal={pal} frame={frame} />
        {nodes.map((n) =>
          n.kind === "LEAF" ? (
            <Leaf
              key={n.key}
              n={n}
              pal={pal}
              frame={frame}
              onHover={setHovered}
            />
          ) : (
            <Ring key={n.key} n={n} nodes={nodes} pal={pal} frame={frame} />
          ),
        )}
        <Ribbons nodes={nodes} pal={pal} frame={frame} pageRefs={pageRefs} />
        <Rays nodes={nodes} pal={pal} frame={frame} />
        <Project nodes={nodes} frame={frame} hovered={hovered} ov={ov} />
        <CameraRig frame={frame} />
      </Canvas>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <span
          ref={ov.root}
          className="absolute top-0 left-0 -translate-x-1/2 font-mono text-[11px] tracking-wide text-ink-2"
        >
          {POLICY}
        </span>
        <span
          ref={ov.status}
          className="absolute top-0 left-0 font-mono text-[10.5px] whitespace-nowrap text-gap"
          style={{ opacity: 0 }}
        />
        <span
          ref={ov.hover}
          className={`absolute top-0 left-0 max-w-[220px] -translate-x-1/2 rounded-[var(--radius-control)] border border-rule bg-paper-raised px-2 py-1 text-[11px] leading-snug text-ink shadow-[var(--shadow-float)] ${hovered ? "" : "hidden"}`}
        >
          {hovered ? nodes.find((n) => n.key === hovered)?.label : ""}
        </span>
      </div>
    </div>
  );
}

// img2threejs review harness: renders one factory at ?az=&el= on the porcelain backdrop (plain renderer, no post FX).
import * as THREE from "three";
import * as F from "./factory";

const q = new URLSearchParams(location.search);
const W = 1024;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(W, W);
renderer.setPixelRatio(1);
renderer.shadowMap.enabled = true;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.style.margin = "0";
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(q.get("bg") ? `#${q.get("bg")}` : "#e6ebe8");
const f = F as unknown as Record<string, (...a: unknown[]) => unknown>;
const create = Object.entries(f).find(([k]) => /^create.*Model$/.test(k))![1];
const model = create() as THREE.Object3D;
model.traverse((o) => {
  if ((o as THREE.Mesh).isMesh) (o as THREE.Mesh).castShadow = (o as THREE.Mesh).receiveShadow = true;
});
scene.add(model);
if (q.get("unlit")) {
  // map-stripped evidence: flat albedo only, no lights, no textures
  model.traverse((o) => {
    const m = o as THREE.Mesh;
    if (m.isMesh) m.material = new THREE.MeshBasicMaterial({ color: (m.material as THREE.MeshStandardMaterial).color });
  });
}

const box = new THREE.Box3().setFromObject(model);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.ShadowMaterial({ opacity: 0.18 }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = box.min.y;
ground.receiveShadow = true;
scene.add(ground);

// Lighting pass (spec lightingFromPhoto): low hemisphere fill so form falloff survives, warm key
// upper-left-front, soft rim from rear-right, ACES at exposure 0.95. ?lp=0 restores the old flat rig.
const lp = q.get("lp") !== "0";
scene.add(new THREE.HemisphereLight("#ffffff", "#d9e0dc", lp ? 0.55 : 1.4));
const key = new THREE.DirectionalLight("#fff6ea", lp ? 2.9 : 2.2);
key.position.set(-3.2, 4.2, 3.6);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.radius = 8;
key.shadow.bias = -0.0004;
scene.add(key);
const fill = new THREE.DirectionalLight("#eef4ff", lp ? 0.45 : 0);
fill.position.set(3, 1.2, 3);
scene.add(fill);
const rim = new THREE.DirectionalLight("#ffffff", lp ? 0.7 : 0.8);
rim.position.set(3, 2, -4);
scene.add(rim);
renderer.toneMappingExposure = lp ? 0.95 : 1;

const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100);
const frame = Object.entries(f).find(([k]) => /^frame.*Camera$/.test(k));
const az = Number(q.get("az") ?? 30);
const el = Number(q.get("el") ?? 18);
const margin = Number(q.get("m") ?? 1.35);
if (frame) frame[1](camera, model, { margin, azimuthDeg: az, elevationDeg: el });
else {
  const b = new THREE.Box3().setFromObject(model);
  const size = b.getSize(new THREE.Vector3());
  const c = b.getCenter(new THREE.Vector3());
  const dist = (Math.max(size.x, size.y, size.z) * margin) / 2 / Math.tan((35 * Math.PI) / 360);
  const a = (az * Math.PI) / 180;
  const e = (el * Math.PI) / 180;
  camera.position.set(c.x + dist * Math.sin(a) * Math.cos(e), c.y + dist * Math.sin(e), c.z + dist * Math.cos(a) * Math.cos(e));
  camera.lookAt(c);
}
renderer.render(scene, camera);
const parts: { name: string; kind: string; triangles: number }[] = [];
model.traverse((o) => {
  const m = o as THREE.Mesh;
  if (m.isMesh) { const g = m.geometry; parts.push({ name: m.name, kind: "part", triangles: (g.index ? g.index.count : g.attributes.position.count) / 3 }); }
});
(window as unknown as { __info: unknown }).__info = { tris: renderer.info.render.triangles, calls: renderer.info.render.calls, parts };
(window as unknown as { __done: boolean }).__done = true;

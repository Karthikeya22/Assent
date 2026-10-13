/**
 * The camera path through the one world. Pure: chapter coordinate t (index + local) -> pose.
 * Each chapter HOLDS its pose while its text is read (local 0..HOLD), then glides to the next
 * chapter's pose during the rest of the scroll. Continuous by construction: a chapter's end pose
 * is the next chapter's start pose.
 */
export type V3 = [number, number, number];
export type Pose = { pos: V3; look: V3 };

export const HOLD = 0.55;

// One pose per chapter (storyboard order). Values tuned against renders in Phase E.
export const POSES: Pose[] = [
  { pos: [2.05, 1.25, 5.1], look: [0.85, 0.82, 0] }, // hero: folder right of the headline
  { pos: [0.9, 3.6, 6.4], look: [0.9, 0.2, 0] }, // problem: looking down into the pile
  { pos: [1.05, 2.35, 4.4], look: [1.2, 2.15, -1.4] }, // policy: up at the lattice
  { pos: [1.2, 1.6, 4.8], look: [1.2, 1.35, -0.9] }, // chart: pages fan into a timeline
  { pos: [1.35, 1.75, 3.7], look: [1.25, 1.45, -1.15] }, // prove: closer, threads to leaves
  { pos: [1.8, 1.95, 3.3], look: [1.45, 1.55, -1.3] }, // verify: push in on the weak leaf
  { pos: [2.0, 1.9, 5.4], look: [1.95, 1.3, -0.85] }, // argue: scales and lattice together
  { pos: [2.9, 1.55, 3.6], look: [2.4, 0.35, 0.6] }, // packet: stamp and seal
  { pos: [5.0, 1.35, 4.3], look: [5.0, 0.95, 0] }, // use: three screens, above the steps panel
  { pos: [-1.8, 1.75, 5.0], look: [-1.8, 0.5, 1.2] }, // proof: dials
  { pos: [2.4, 1.75, 3.6], look: [2.4, 0.95, 0.6] }, // close: the sealed packet, low in frame under the line
];

/**
 * Which side each chapter's text sits on (-1 left, 0 centre, 1 right). The film offset moves the
 * 3D subject to the opposite side of the frame from the copy (filmOffset > 0 slides the image left).
 */
export const TEXT_SIDE = [-1, 0, -1, 1, -1, 1, -1, 1, 0, -1, 0];

/** Horizontal film offset (mm, 35 mm gauge) for chapter coordinate t; blends with the camera. */
export function filmShift(t: number, sides: number[] = TEXT_SIDE, mm = 6.5): number {
  const last = sides.length - 1;
  const c = Math.min(last, Math.max(0, t));
  const i = Math.min(last, Math.floor(c));
  if (i === last) return sides[last] * mm;
  const k = travel(c - i);
  return (sides[i] + (sides[i + 1] - sides[i]) * k) * mm;
}

const ease = (x: number) => x * x * (3 - 2 * x);
const mix = (a: V3, b: V3, k: number): V3 => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];

/** How far (0..1) the camera has travelled from chapter floor(t) toward the next one. */
export function travel(local: number): number {
  return ease(Math.min(1, Math.max(0, (local - HOLD) / (1 - HOLD))));
}

export function poseAt(t: number, poses: Pose[] = POSES): Pose {
  const last = poses.length - 1;
  const clamped = Math.min(last, Math.max(0, t));
  const i = Math.min(last, Math.floor(clamped));
  if (i === last) return poses[last];
  const k = travel(clamped - i);
  // Lift the camera a little mid-glide so moves read as a dolly arc, not a straight slide.
  const arc = Math.sin(Math.PI * k) * 0.25;
  const pos = mix(poses[i].pos, poses[i + 1].pos, k);
  pos[1] += arc;
  return { pos, look: mix(poses[i].look, poses[i + 1].look, k) };
}

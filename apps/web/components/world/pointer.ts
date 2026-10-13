/**
 * Cursor input for the world: a target set by pointermove (normalised -1..1, y up) and a value
 * that follows it with frame-rate independent damping, so every reaction feels weighted.
 */
export function damp(current: number, target: number, lambda: number, dt: number): number {
  return target + (current - target) * Math.exp(-lambda * dt);
}

export type Pointer = { tx: number; ty: number; x: number; y: number; active: boolean };

export const pointer: Pointer = { tx: 0, ty: 0, x: 0, y: 0, active: false };

export function setTarget(clientX: number, clientY: number, w: number, h: number): void {
  pointer.tx = (clientX / w) * 2 - 1;
  pointer.ty = 1 - (clientY / h) * 2;
  pointer.active = true;
}

/** Advance the damped value; call once per frame. Lambda 4 settles in about half a second. */
export function stepPointer(dt: number, lambda = 4): void {
  pointer.x = damp(pointer.x, pointer.tx, lambda, dt);
  pointer.y = damp(pointer.y, pointer.ty, lambda, dt);
}

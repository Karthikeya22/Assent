// Motion tokens (FRONTEND.md §2.4), mirrored from globals.css for JS-driven animation.
export const ease = {
  out: [0.2, 0.8, 0.2, 1],
  inOut: [0.65, 0, 0.35, 1],
} as const;

export const dur = { 1: 0.12, 2: 0.22, 3: 0.42, 4: 0.9 } as const; // seconds

export const spring = { type: "spring", stiffness: 380, damping: 32 } as const;

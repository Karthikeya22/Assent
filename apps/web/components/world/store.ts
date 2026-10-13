import { create } from "zustand";
import type { Place } from "./chapters";

/**
 * Where the reader is in the story. Written by ScrollDriver on every Lenis scroll event; the world
 * reads it with getState() inside useFrame (no React work), the DOM subscribes to `index` only.
 * Its own module so marketing pages can use it without loading three.js.
 */
export const useWorld = create<Place>(() => ({ index: 0, local: 0, t: 0 }));

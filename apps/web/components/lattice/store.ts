import { create } from "zustand";

/** Story scroll progress (0..1). Its own module so the page can write it without loading three.js. */
export const useStory = create<{ progress: number }>(() => ({ progress: 0 }));

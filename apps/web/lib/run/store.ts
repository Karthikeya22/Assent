import { create } from "zustand";
import { initialRunState, reduce, type RunEvent, type RunState } from "./reducer";

type RunStore = {
  run: RunState;
  dispatch: (e: RunEvent) => void;
  reset: (to?: RunState) => void;
};

// Components select their own slice (e.g. one leaf), so a verdict re-renders one node only.
export const useRunStore = create<RunStore>((set) => ({
  run: initialRunState,
  dispatch: (e) => set((s) => ({ run: reduce(s.run, e) })),
  reset: (to = initialRunState) => set({ run: to }),
}));

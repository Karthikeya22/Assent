import type { components } from "@/lib/api/schema";
import type { LogicState, Verdict } from "./reducer";

type Criterion = components["schemas"]["CriterionOut"];

/**
 * Client mirror of the server's three-valued logic engine, used to show logic-node states for
 * runs loaded from the DB (live runs get them from `logic_update` events instead).
 */
export function evaluateTree(root: Criterion, leaves: Record<string, Verdict | undefined>) {
  const states: Record<string, LogicState> = {};
  const ev = (n: Criterion): LogicState => {
    if (n.kind === "LEAF") return (states[n.key] = leaves[n.key] ?? "insufficient");
    const kids = n.children.map(ev);
    const met = kids.filter((k) => k === "met").length;
    const ins = kids.filter((k) => k === "insufficient").length;
    const need = n.kind === "AND" ? kids.length : n.kind === "OR" ? 1 : (n.n_required ?? kids.length);
    const s: LogicState = met >= need ? "met" : met + ins < need ? "not_met" : "insufficient";
    return (states[n.key] = s);
  };
  ev(root);
  return states;
}

/**
 * Leaves that actually block the decision: not met, with no satisfied ancestor. An unchosen OR
 * alternative (e.g. "herpes zoster" when radiculopathy already satisfies the diagnosis) is not
 * a gap.
 */
export function gapKeys(root: Criterion, states: Record<string, LogicState | undefined>): string[] {
  const out: string[] = [];
  const walk = (n: Criterion, covered: boolean) => {
    const done = covered || states[n.key] === "met";
    if (n.kind === "LEAF") {
      if (!done && states[n.key]) out.push(n.key);
      return;
    }
    n.children.forEach((c) => walk(c, done));
  };
  walk(root, false);
  return out;
}

export function leavesOf(c: Criterion): Criterion[] {
  return c.kind === "LEAF" ? [c] : c.children.flatMap(leavesOf);
}

import lattice from "@/content/lattice.json";

export type Kind = "AND" | "OR" | "N_OF_M" | "LEAF";
export type LNode = {
  key: string;
  kind: Kind;
  label: string;
  parent: string | null;
  depth: number;
  pos: [number, number, number];
};

export const POLICY = lattice.policy;
export const GRAPH_X = 1.15; // the graph sits right of the chart pages
const WIDTH = 2.9;

/** Lay the real criteria tree out in 3D: leaves spread on x, logic flows up to the root ring. */
export function layout(nodes = lattice.nodes as Omit<LNode, "depth" | "pos">[]): LNode[] {
  const byKey = new Map(nodes.map((n) => [n.key, n]));
  const kids = new Map<string, string[]>();
  for (const n of nodes) if (n.parent) kids.set(n.parent, [...(kids.get(n.parent) ?? []), n.key]);
  const depth = (k: string): number => {
    const p = byKey.get(k)?.parent;
    return p ? depth(p) + 1 : 0;
  };
  const leaves = nodes.filter((n) => n.kind === "LEAF");
  const x = new Map<string, number>();
  leaves.forEach((n, i) => x.set(n.key, GRAPH_X - WIDTH / 2 + (WIDTH * i) / (leaves.length - 1)));
  const xOf = (k: string): number => {
    if (!x.has(k)) {
      const c = kids.get(k) ?? [];
      x.set(k, c.reduce((s, ck) => s + xOf(ck), 0) / c.length);
    }
    return x.get(k)!;
  };
  return nodes.map((n, i) => {
    const d = depth(n.key);
    // Leaves sit low (depth 4 tree): y from 1.45 (root) down; z jitter gives the scene depth.
    return { ...n, depth: d, pos: [xOf(n.key), 1.45 - d * 0.62, Math.sin(i * 1.7) * 0.28] as [number, number, number] };
  });
}

export function children(nodes: LNode[], key: string): LNode[] {
  return nodes.filter((n) => n.parent === key);
}

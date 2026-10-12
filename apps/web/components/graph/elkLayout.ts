import type { Edge, Node } from "@xyflow/react";

// ELK is ~400 KB; load it on first layout instead of in the page bundle.
let elk: Promise<InstanceType<typeof import("elkjs/lib/elk.bundled.js").default>> | null = null;

/** Top-down layered layout for a criteria tree (FRONTEND §6.3). */
export async function layout(nodes: Node[], edges: Edge[]): Promise<Node[]> {
  elk ??= import("elkjs/lib/elk.bundled.js").then(({ default: ELK }) => new ELK());
  const g = await (await elk).layout({
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "DOWN",
      "elk.layered.spacing.nodeNodeBetweenLayers": "56",
      "elk.spacing.nodeNode": "20",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
      "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED", // parents centred over children
    },
    children: nodes.map((n) => ({ id: n.id, width: n.width ?? 200, height: n.height ?? 60 })),
    // Rendered edges run child → parent (evidence flows up); ELK needs parent → child to put
    // the policy root on top.
    edges: edges.map((e) => ({ id: e.id, sources: [e.target], targets: [e.source] })),
  });
  const pos = new Map(g.children?.map((c) => [c.id, { x: c.x ?? 0, y: c.y ?? 0 }]));
  return nodes.map((n) => ({ ...n, position: pos.get(n.id) ?? { x: 0, y: 0 } }));
}

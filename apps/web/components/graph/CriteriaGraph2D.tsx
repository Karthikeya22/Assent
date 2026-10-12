"use client";

import {
  BaseEdge,
  type Edge,
  type EdgeProps,
  getSmoothStepPath,
  type Node,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/base.css";
import { useEffect, useMemo, useState } from "react";
import type { components } from "@/lib/api/schema";
import { useRunStore } from "@/lib/run/store";
import { layout } from "./elkLayout";
import { LeafNode, LogicNode, RootNode } from "./nodes";

type Criterion = components["schemas"]["CriterionOut"];

const EVIDENCE: Record<string, string> = {
  diagnosis: "diagnosis",
  duration: "duration",
  assessment: "assessment",
  imaging_finding: "imaging",
  prior_therapy: "prior therapy",
  contraindication: "contraindication",
  procedure_history: "procedure history",
};

/** Edge from a child to its parent; it turns signal-colored once the child is satisfied. */
function FlowEdge(p: EdgeProps) {
  const state = useRunStore((s) => s.run.leaves[p.source]?.verdict ?? s.run.logic[p.source]);
  const [path] = getSmoothStepPath({ ...p, borderRadius: 8 });
  const stroke = state === "met" ? "var(--signal)" : state === "not_met" ? "var(--fail)" : "var(--rule)";
  return (
    <BaseEdge
      path={path}
      style={{ stroke, strokeWidth: state === "met" ? 1.75 : 1.25, transition: "stroke var(--dur-3) var(--ease-out)" }}
    />
  );
}

const nodeTypes = { leaf: LeafNode, logic: LogicNode, root: RootNode };
const edgeTypes = { flow: FlowEdge };

function toFlow(root: Criterion, sourceId: string, title: string, selected: string | null) {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  let index = 0;
  const walk = (c: Criterion, parent: string | null) => {
    if (c.kind === "LEAF") {
      index += 1;
      nodes.push({
        id: c.key, type: "leaf", position: { x: 0, y: 0 }, width: 240, height: 92,
        data: { label: c.label, evidence: EVIDENCE[c.evidence_type ?? ""] ?? c.evidence_type, index, selected: c.key === selected },
      });
    } else if (parent === null) {
      nodes.push({ id: c.key, type: "root", position: { x: 0, y: 0 }, width: 300, height: 92, data: { sourceId, title } });
    } else {
      nodes.push({
        id: c.key, type: "logic", position: { x: 0, y: 0 }, width: 110, height: 36,
        data: { kind: c.kind, nRequired: c.n_required, childKeys: c.children.map((k) => k.key) },
      });
    }
    if (parent) edges.push({ id: `${c.key}->${parent}`, source: c.key, target: parent, type: "flow" });
    c.children.forEach((k) => walk(k, c.key));
  };
  walk(root, null);
  return { nodes, edges };
}

function Graph({ root, sourceId, title, selected, onSelect }: Props) {
  const { nodes: raw, edges } = useMemo(() => toFlow(root, sourceId, title, selected), [root, sourceId, title, selected]);
  const [nodes, setNodes] = useState<Node[]>([]);

  useEffect(() => {
    let live = true;
    layout(raw, edges).then((laid) => {
      if (!live) return;
      setNodes((prev) =>
        // Keep positions stable across selection changes; only data changes then.
        prev.length === laid.length ? laid.map((n, i) => ({ ...n, position: prev[i].position })) : laid,
      );
    });
    return () => {
      live = false;
    };
  }, [raw, edges]);

  // Mount React Flow only once ELK has placed the nodes, and let its built-in fitView (which
  // waits for measurement) frame them; fitting from an effect raced the layout.
  if (!nodes.length) return null;
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      fitView
      fitViewOptions={{ padding: 0.06, maxZoom: 1 }}
      onNodeClick={(_, n) => n.type === "leaf" && onSelect(n.id)}
      nodesDraggable={false}
      nodesConnectable={false}
      edgesFocusable={false}
      minZoom={0.3}
      maxZoom={1.5}
      proOptions={{ hideAttribution: true }}
      aria-label="Criteria graph"
    />
  );
}

type Props = {
  root: Criterion;
  sourceId: string;
  title: string;
  selected: string | null;
  onSelect: (key: string) => void;
};

export function CriteriaGraph2D(props: Props) {
  return (
    <ReactFlowProvider>
      <Graph {...props} />
    </ReactFlowProvider>
  );
}

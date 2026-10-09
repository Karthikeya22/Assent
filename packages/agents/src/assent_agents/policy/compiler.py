"""Policy Compiler (PRODUCT §4.1): LCD prose → Criteria Graph, by self-consistency over N samples.

segment → extract xN (parallel, Send) → merge (majority vote on quoted policy spans) → draft tree.
A human approves the draft in the policy editor before it is used (ARCHITECTURE §6.3).
"""

import json
import operator
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel

from assent_agents import llm as llm_mod
from assent_agents import prompts
from assent_agents.policy.ingest import LcdSnapshot
from assent_agents.policy.tree import CriteriaTree, EvidenceType, Kind, Node

PROMPT = "policy_compiler_v1"
_STARTS = ("Covered Indications", "Coverage Indications", "Indications")
_ENDS = ("Provider Qualifications", "Documentation Requirements", "Definitions")


class FlatNode(BaseModel):
    """Flat form for the LLM: strict structured outputs handle a list far better than recursion."""

    key: str
    parent_key: str | None
    kind: Kind
    label: str
    n_required: int | None
    evidence_type: EvidenceType | None
    threshold_json: str | None
    lookback_days: int | None
    source_quote: str | None


class Extraction(BaseModel):
    nodes: list[FlatNode]


@dataclass
class CompileResult:
    tree: CriteriaTree
    dropped: list[str]
    samples_ok: int
    prompt_version: str = PROMPT


def coverage_section(text: str) -> str:
    starts = [i for s in _STARTS if (i := text.find(s)) >= 0]
    start = min(starts) if starts else 0
    ends = [i for e in _ENDS if (i := text.find(e, start + 1)) > start]
    return text[start : min(ends) if ends else len(text)].strip()


def build_tree(ex: Extraction, source_id: str, version: int) -> CriteriaTree:
    roots = [n for n in ex.nodes if n.parent_key is None]
    if len(roots) != 1:
        raise ValueError(f"need exactly one root, got {len(roots)}")
    kids: dict[str, list[FlatNode]] = {}
    for n in ex.nodes:
        if n.parent_key is not None:
            kids.setdefault(n.parent_key, []).append(n)

    def make(f: FlatNode, seen: frozenset[str]) -> Node:
        if f.key in seen:
            raise ValueError(f"cycle at {f.key}")
        threshold = json.loads(f.threshold_json) if f.threshold_json else None
        return Node(
            key=f.key,
            kind=f.kind,
            label=f.label,
            n_required=f.n_required,
            evidence_type=f.evidence_type,
            threshold=threshold,
            lookback_days=f.lookback_days,
            source_quote=f.source_quote,
            children=[make(c, seen | {f.key}) for c in kids.get(f.key, [])],
        )

    return CriteriaTree(source_id=source_id, version=version, root=make(roots[0], frozenset()))


def _span(text: str, quote: str | None) -> tuple[int, int] | None:
    if not quote or (i := text.find(quote)) < 0:
        return None
    return (i, i + len(quote))


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    inter = min(a[1], b[1]) - max(a[0], b[0])
    return inter > 0 and inter / min(a[1] - a[0], b[1] - b[0]) >= 0.6


def _prune(node: Node, keep: set[str], dropped: list[str], tag: str) -> Node | None:
    if node.kind == "LEAF":
        return node if node.key in keep else None
    children = [c for ch in node.children if (c := _prune(ch, keep, dropped, tag)) is not None]
    if not children:
        return None
    n_req = node.n_required
    if node.kind == "N_OF_M" and n_req is not None and n_req > len(children):
        dropped.append(f"{tag}{node.key}: n_required {n_req} → {len(children)} after pruning")
        n_req = len(children)
    return node.model_copy(update={"children": children, "n_required": n_req})


def merge_trees(trees: list[CriteriaTree], text: str) -> tuple[CriteriaTree, list[str]]:
    """Majority vote: keep leaves whose quoted span appears in > half the samples."""
    dropped: list[str] = []
    leaves: list[tuple[tuple[int, int], int, Node]] = []
    for i, t in enumerate(trees):
        for leaf in t.leaves():
            if (sp := _span(text, leaf.source_quote)) is None:
                dropped.append(f"{leaf.key}: quote not found verbatim: {leaf.source_quote!r}")
            else:
                leaves.append((sp, i, leaf))

    # Cluster in text order so the result doesn't depend on sample order.
    clusters: list[list[tuple[tuple[int, int], int, Node]]] = []
    for item in sorted(leaves, key=lambda x: (x[0], x[2].key)):
        home = next((c for c in clusters if _overlaps(c[0][0], item[0])), None)
        (home.append(item) if home else clusters.append([item]))
    need = len(trees) // 2 + 1
    winners = [c for c in clusters if len({i for _, i, _ in c}) >= need]
    for c in clusters:
        if c not in winners:
            dropped.append(f"{c[0][2].key}: only {len({i for _, i, _ in c})}/{len(trees)} samples")

    def score(i: int) -> tuple[int, str]:
        has = sum(any(j == i for _, j, _ in c) for c in winners)
        return (-has, trees[i].model_dump_json())

    best = min(range(len(trees)), key=score)
    keep = {leaf.key for c in winners for _, j, leaf in c if j == best}
    root = _prune(trees[best].root, keep, dropped, "")
    if root is None:
        raise ValueError("no criteria survived the majority vote")
    return trees[best].model_copy(update={"root": root}), dropped


def compare_trees(gold: CriteriaTree, compiled: CriteriaTree, text: str) -> dict[str, Any]:
    """Leaf precision/recall of a compiled tree against the hand-approved gold tree."""
    g = [(sp, n.key) for n in gold.leaves() if (sp := _span(text, n.source_quote))]
    c = [(sp, n.key) for n in compiled.leaves() if (sp := _span(text, n.source_quote))]
    used: set[int] = set()
    pairs = []
    for gsp, gkey in g:
        j = next((j for j, (csp, _) in enumerate(c) if j not in used and _overlaps(gsp, csp)), None)
        if j is not None:
            used.add(j)
            pairs.append((gkey, c[j][1]))
    p = len(pairs) / len(compiled.leaves()) if compiled.leaves() else 0.0
    r = len(pairs) / len(gold.leaves()) if gold.leaves() else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f1, "pairs": pairs}


# --- graph ---------------------------------------------------------------------


class _State(TypedDict, total=False):
    snapshot: LcdSnapshot
    section: str
    trees: Annotated[list[CriteriaTree], operator.add]
    errors: Annotated[list[str], operator.add]
    result: CompileResult


def build_graph(llm: llm_mod.StructuredLLM, n_samples: int) -> Any:
    system = prompts.load(PROMPT)

    def segment(state: _State) -> dict[str, Any]:
        return {"section": coverage_section(state["snapshot"].raw_text)}

    def fan_out(state: _State) -> list[Send]:
        return [
            Send("extract", {"snapshot": state["snapshot"], "section": state["section"]})
            for _ in range(n_samples)
        ]

    async def extract(state: _State) -> dict[str, Any]:
        snap = state["snapshot"]
        msgs = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Policy: {snap.title} ({snap.source_id} v{snap.version})"
                f"\n\n<policy>\n{state['section']}\n</policy>",
            },
        ]
        try:
            ex: Extraction = await llm("reasoning", msgs, Extraction)
            return {"trees": [build_tree(ex, snap.source_id, snap.version)]}
        except ValueError as e:  # a malformed sample is dropped, not fatal: the vote absorbs it
            return {"errors": [f"sample failed: {e}"]}

    def merge(state: _State) -> dict[str, Any]:
        trees = state.get("trees", [])
        if not trees:
            raise ValueError("all compiler samples failed: " + "; ".join(state.get("errors", [])))
        tree, dropped = merge_trees(trees, state["snapshot"].raw_text)
        return {"result": CompileResult(tree, state.get("errors", []) + dropped, len(trees))}

    g = StateGraph(_State)
    g.add_node("segment", segment)
    g.add_node("extract", extract)
    g.add_node("merge", merge)
    g.add_edge(START, "segment")
    g.add_conditional_edges("segment", fan_out, ["extract"])
    g.add_edge("extract", "merge")
    g.add_edge("merge", END)
    return g.compile()


async def compile_policy(
    snap: LcdSnapshot, *, llm: llm_mod.StructuredLLM | None = None, n_samples: int = 3
) -> CompileResult:
    graph = build_graph(llm or llm_mod.structured, n_samples)
    out = await graph.ainvoke({"snapshot": snap})
    result: CompileResult = out["result"]
    return result

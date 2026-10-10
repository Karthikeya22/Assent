"""Record a real run's event stream for offline replay (demo, Storybook, Playwright).

Run: `uv run python -m assent_evals.record_fixture esi-001 [--llm oracle|openai]`
Writes data/fixtures/run_<case>.jsonl: one ARCHITECTURE §5 event per line, original order.
"""

import argparse
import asyncio
import json
from datetime import date

from assent_agents import llm as llm_mod
from assent_agents.case_graph import CaseInput, run_case
from assent_agents.cassette import Cassette
from assent_agents.events import Collector, event
from assent_agents.evidence.agent import CaseContext
from assent_agents.policy.tree import CriteriaTree
from assent_api.db import SessionLocal
from assent_evals.bench import CASSETTES, _case_row
from assent_evals.oracle import make_oracle
from assent_evals.synth.build import BENCH, BUNDLES, GOLD_TREE, REPO
from assent_fhir.source import FileFhirSource

FIXTURES = REPO / "data" / "fixtures"


async def main(case_id: str, which: str) -> None:
    tree = CriteriaTree.model_validate_json(GOLD_TREE.read_text("utf-8"))
    facts = json.loads((BENCH / f"{case_id}.json").read_text("utf-8"))["facts"]
    llm = Cassette(CASSETTES, llm_mod.structured) if which == "openai" else make_oracle(facts, tree)
    inp = CaseInput(
        case_id=await _case_row(case_id, facts),
        chart_ref=case_id,
        tree=tree,
        patient_names=[facts["patient"]["name"]],
        ctx=CaseContext(
            order_date=date.fromisoformat(facts["order_date"]),
            service="Epidural steroid injection",
            cpt=facts["cpt"],
            icd10=facts["icd10"],
        ),
    )
    sink = Collector()
    await sink(
        event(
            "run_started",
            case_id=case_id,
            policy=f"{tree.source_id} v{tree.version}",
            leaves=[n.key for n in tree.leaves()],
        )
    )
    await run_case(inp, SessionLocal, FileFhirSource(BUNDLES), llm, emit=sink)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    out = FIXTURES / f"run_{case_id}.jsonl"
    out.write_text("".join(json.dumps(e) + "\n" for e in sink.events), "utf-8", newline="\n")
    print(f"wrote {out.relative_to(REPO)}: {len(sink.events)} events")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id")
    ap.add_argument("--llm", default="oracle", choices=["oracle", "openai"])
    a = ap.parse_args()
    asyncio.run(main(a.case_id, a.llm))

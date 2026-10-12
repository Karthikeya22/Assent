import base64
import json
import random
from datetime import date
from pathlib import Path
from typing import Any

from assent_evals.adversary_eval import gold_verdicts, seed
from assent_evals.injection_eval import ATTACKS, InjectedSource, report
from assent_evals.synth.build import FAMILIES


class _Base:
    def everything(self, ref: str) -> list[dict[str, Any]]:
        return [{"resourceType": "Patient", "id": "p1"}]


def test_injected_note_carries_the_rotating_attack() -> None:
    src = InjectedSource(_Base(), {"pva-007": date(2026, 9, 10)})
    note = src.everything("pva-007")[-1]
    body = base64.b64decode(note["content"][0]["attachment"]["data"]).decode()
    assert ATTACKS[7 % len(ATTACKS)] in body and note["date"].startswith("2026-09-07")


def test_report_scores_injected_runs_against_gold(tmp_path: Path) -> None:
    log = tmp_path / "i.jsonl"
    rec = {
        "case_id": "esi-003",
        "gold_decision": "not_ready",
        "decision": "not_ready",
        "leaf_pairs": [["insufficient", "met"], ["met", "met"], ["not_met", "not_met"]],
    }
    log.write_text(json.dumps(rec) + "\n", "utf-8")
    out = report([log])
    assert (out["false_met_leaves"], out["decision_flips_to_ready"]) == (1, 0)


def test_each_seeded_defect_corrupts_exactly_one_met_criterion() -> None:
    fam = FAMILIES["hgns"]
    m = next(
        m
        for m in json.loads((fam.bench / "manifest.json").read_text("utf-8"))
        if m["decision"] == "ready"
    )
    facts = json.loads((fam.bench / f"{m['case_id']}.json").read_text("utf-8"))["facts"]
    clean = gold_verdicts(facts)
    for defect in ("weak", "wrong", "none"):
        bad, key = seed(facts, "hgns", defect, random.Random(defect))
        changed = [k for k in clean if bad[k].citations != clean[k].citations]
        assert changed == [key] and bad[key].verdict == "met", defect

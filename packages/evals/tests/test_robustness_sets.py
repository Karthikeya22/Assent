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


def _log(path: Path, cid: str, preds: list[str], decision: str) -> None:
    rec = {"case_id": cid, "decision": decision, "leaf_pairs": [["met", p] for p in preds]}
    path.write_text(json.dumps(rec) + "\n", "utf-8")


def test_report_counts_only_moves_toward_met(tmp_path: Path) -> None:
    clean, inj = tmp_path / "c.jsonl", tmp_path / "i.jsonl"
    _log(clean, "esi-003", ["insufficient", "met", "not_met"], "not_ready")
    _log(inj, "esi-003", ["met", "not_met", "not_met"], "not_ready")  # one up, one down
    out = report([(clean, inj)])
    assert (out["leaf_flips_to_met"], out["decision_flips_to_ready"]) == (1, 0)


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

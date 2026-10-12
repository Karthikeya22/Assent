import json
from pathlib import Path

import pytest

from assent_phi.deid import Deidentifier

BENCH = Path(__file__).resolve().parents[3] / "data" / "bench" / "esi"


@pytest.fixture(scope="module")
def deid() -> Deidentifier:
    return Deidentifier(known_names=["Gaston Durgan"])


def test_names_mrn_phone_get_consistent_surrogates(deid: Deidentifier) -> None:
    text = (
        "Patient: Gaston Durgan, 87-year-old male. MRN: 00482913. Call 617-555-0143.\n"
        "Mr. Durgan reports pain. Gaston agrees with the plan."
    )
    out = deid.deidentify(text)
    for raw in ("Gaston", "Durgan", "00482913", "617-555-0143"):
        assert raw not in out
    assert out.count("[NAME_1]") >= 2  # same person, same surrogate
    assert "[MRN_1]" in out and "[PHONE_1]" in out
    assert "87-year-old male" in out  # age kept (synthetic; ≤ 89 is not a safe-harbor identifier)


def test_dates_are_kept(deid: Deidentifier) -> None:
    text = "Symptoms began on 06/09/2026, 16 weeks before this visit."
    assert deid.deidentify(text) == text


def test_every_gold_fact_sentence_survives_byte_for_byte(deid: Deidentifier) -> None:
    sentences = {
        s["text"]
        for p in sorted(BENCH.glob("esi-*.json"))
        for s in json.loads(p.read_text("utf-8"))["facts"]["statements"]
    }
    assert len(sentences) > 100
    changed = [s for s in sentences if deid.deidentify(s) != s]
    assert changed == []

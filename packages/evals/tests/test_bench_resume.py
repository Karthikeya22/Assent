import json
from pathlib import Path

from assent_evals.bench import free_ram_gb, load_done, summarize


def _rec(cid: str, diff: str, pairs: list[list[str]], decision: str) -> dict:  # type: ignore[type-arg]
    return {
        "case_id": cid,
        "difficulty": diff,
        "gold_decision": "ready",
        "decision": decision,
        "readiness": 1.0,
        "chunks": 3,
        "seconds": 2.0,
        "cost_usd": 0.01,
        "misses": {},
        "downgrades": {},
        "leaf_pairs": pairs,
        "claims": 2,
        "downgraded": 0,
        "citations": 2,
        "valid_citations": 2,
        "verbatim_citations": 2,
    }


def test_log_is_resumable_and_summary_comes_from_all_lines(tmp_path: Path) -> None:
    log = tmp_path / "oracle-dev.jsonl"
    a = _rec("esi-001", "clean", [["met", "met"], ["insufficient", "insufficient"]], "ready")
    b = _rec("esi-002", "buried", [["met", "insufficient"]], "not_ready")
    log.write_text(json.dumps(a) + "\n" + json.dumps(b) + "\n\n", "utf-8")

    done = load_done(log)
    assert set(done) == {"esi-001", "esi-002"}  # a restart skips both
    assert load_done(tmp_path / "missing.jsonl") == {}

    s = summarize([done["esi-001"], done["esi-002"]], "dev", "oracle")
    assert s["n_cases"] == 2 and s["case_accuracy"] == 0.5
    assert s["citation_precision"] == 1.0 and s["cost_per_case_usd"] == 0.01
    assert set(s["per_difficulty_f1"]) == {"clean", "buried"}
    assert all("leaf_pairs" not in c for c in s["cases"])


def test_free_ram_is_readable_here() -> None:
    free = free_ram_gb()
    assert free is None or 0 < free < 1024

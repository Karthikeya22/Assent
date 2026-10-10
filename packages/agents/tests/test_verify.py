from assent_agents.evidence.models import Citation, Verdict
from assent_agents.verify import find_quote, verify

CHUNKS = {
    "c1": "Pain Management Consultation\nDate: 09/28/2026\n\n"
    "Symptoms began on 07/01/2026,  12 weeks\nbefore this visit. Denies fever.",
    "c2": "On re-interview, the leg pain began 3 weeks ago; the earlier history was inaccurate.",
}
LABEL = "Pain duration of at least 4 weeks"


def nli(premise: str, hypothesis: str) -> dict[str, float]:
    # Scripted NLI: "12 weeks" entails, "3 weeks" contradicts, anything else is neutral.
    if "12 weeks" in premise:
        return {"entailment": 0.93, "contradiction": 0.02, "neutral": 0.05}
    if "3 weeks" in premise:
        return {"entailment": 0.03, "contradiction": 0.9, "neutral": 0.07}
    return {"entailment": 0.1, "contradiction": 0.1, "neutral": 0.8}


def _v(verdict: str, *cites: tuple[str, str]) -> Verdict:
    return Verdict(
        criterion_key="dur.pain",
        verdict=verdict,
        confidence=0.9,
        rationale="r",  # type: ignore[arg-type]
        citations=[Citation(chunk_id=c, quote=q) for c, q in cites],
    )


def test_find_quote_tolerates_whitespace_only() -> None:
    text = CHUNKS["c1"]
    s, e = find_quote(text, "Symptoms began on 07/01/2026, 12 weeks before this visit.")  # type: ignore[misc]
    assert text[s:e] == "Symptoms began on 07/01/2026,  12 weeks\nbefore this visit."
    assert find_quote(text, "Symptoms began on 07/01/2026, 13 weeks before this visit.") is None


def test_met_with_entailing_verbatim_quote_is_kept() -> None:
    out = verify(
        _v("met", ("c1", "Symptoms began on 07/01/2026, 12 weeks before this visit.")),
        CHUNKS,
        LABEL,
        nli,
    )
    assert out.verdict == "met" and out.downgraded is None
    assert out.citations[0].verbatim_ok and out.citations[0].support == 0.93


def test_not_met_is_supported_by_contradiction() -> None:
    out = verify(_v("not_met", ("c2", "the leg pain began 3 weeks ago")), CHUNKS, LABEL, nli)
    assert out.verdict == "not_met" and out.citations[0].support == 0.9


def test_paraphrased_quote_downgrades_to_insufficient() -> None:
    out = verify(_v("met", ("c1", "Pain started 12 weeks before the visit.")), CHUNKS, LABEL, nli)
    assert out.verdict == "insufficient" and out.original == "met"
    assert out.downgraded and "verbatim" in out.downgraded
    assert out.citations[0].verbatim_ok is False  # kept and flagged, not deleted


def test_verbatim_but_not_entailed_downgrades() -> None:
    out = verify(_v("met", ("c1", "Denies fever.")), CHUNKS, LABEL, nli)
    assert out.verdict == "insufficient" and out.downgraded and "support" in out.downgraded


def test_met_without_citations_downgrades_and_unknown_chunk_fails() -> None:
    assert verify(_v("met"), CHUNKS, LABEL, nli).verdict == "insufficient"
    assert verify(_v("met", ("zz", "x")), CHUNKS, LABEL, nli).verdict == "insufficient"


def test_one_good_citation_is_enough() -> None:
    out = verify(
        _v(
            "met",
            ("c1", "Denies fever."),
            ("c1", "Symptoms began on 07/01/2026, 12 weeks before this visit."),
        ),
        CHUNKS,
        LABEL,
        nli,
    )
    assert out.verdict == "met"


def test_insufficient_passes_through() -> None:
    out = verify(_v("insufficient"), CHUNKS, LABEL, nli)
    assert out.verdict == "insufficient" and out.downgraded is None

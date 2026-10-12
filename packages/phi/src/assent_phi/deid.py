"""PHI de-identification before any external model call (ARCHITECTURE §7.1).

Names, MRNs, phone numbers, emails and SSNs become consistent surrogates ([NAME_1] ...). Dates
are kept on purpose: coverage criteria are intervals (≥4 weeks, 12-month windows) and all data
here is synthetic. Date-shifting is the v2 option for real data.
"""

import re
from functools import lru_cache
from typing import Any

_ENTITIES = {
    "PERSON": "NAME",
    "PHONE_NUMBER": "PHONE",
    "EMAIL_ADDRESS": "EMAIL",
    "US_SSN": "SSN",
    "MRN": "MRN",
}
# The small spaCy model tags spine levels ("L5-S1"), dates and acronyms as PERSON, all at the
# same 0.85 score, so filter by shape instead: 1-3 Title-case alphabetic words, no eponyms.
_EPONYMS = {
    "oswestry",
    "roland",
    "morris",
    "quebec",
    "promis",
    "babinski",
    "spurling",
    "lasegue",
    "hoffmann",
    "romberg",
    "patrick",
    "faber",
    "tinel",
    "phalen",
}
_NAME_WORD = re.compile(r"^[A-Z][a-z]+(?:['-][A-Z]?[a-z]+)?\.?$")


def _looks_like_name(raw: str) -> bool:
    words = raw.split()
    return (
        1 <= len(words) <= 3
        and all(_NAME_WORD.match(w) for w in words)
        and not any(w.lower().strip(".") in _EPONYMS for w in words)
    )


@lru_cache
def _analyzer() -> Any:
    # Heavy (spaCy model load): build once per process, only when first needed.
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    nlp = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            "ner_model_configuration": {
                "labels_to_ignore": [
                    "CARDINAL",
                    "ORDINAL",
                    "QUANTITY",
                    "PERCENT",
                    "MONEY",
                    "PRODUCT",
                    "WORK_OF_ART",
                    "LAW",
                    "LANGUAGE",
                    "EVENT",
                    "FAC",
                    "ORG",
                    "NORP",
                    "TIME",
                    "DATE",
                    "GPE",
                    "LOC",
                ]
            },
        }
    ).create_engine()
    engine = AnalyzerEngine(nlp_engine=nlp, supported_languages=["en"])
    engine.registry.add_recognizer(
        PatternRecognizer(
            supported_entity="MRN",
            patterns=[Pattern("mrn", r"(?i)(?<=MRN[:#\s])\s*\d{6,10}\b", 0.95)],
        )
    )
    return engine


class Deidentifier:
    """One instance per case, so the same person maps to the same surrogate across notes."""

    def __init__(self, known_names: list[str] | None = None) -> None:
        self.map: dict[tuple[str, str], str] = {}
        self.counts: dict[str, int] = {}
        # Known patient names are matched exactly (more reliable than NER), whole and in parts.
        parts = {p for n in known_names or [] for p in [n, *n.split()] if len(p) > 1}
        self._known = sorted(parts, key=len, reverse=True)
        self._first = {n.split()[0] for n in known_names or [] if n.split()}

    def _surrogate(self, kind: str, raw: str) -> str:
        key = (kind, "person" if kind == "NAME" and raw in self._known else raw.lower())
        if kind == "NAME":
            key = (kind, "patient") if raw in self._known else key
        if key not in self.map:
            self.counts[kind] = self.counts.get(kind, 0) + 1
            self.map[key] = f"[{kind}_{self.counts[kind]}]"
        return self.map[key]

    def deidentify(self, text: str) -> str:
        spans: list[tuple[int, int, str]] = []
        for name in self._known:
            for m in re.finditer(rf"\b{re.escape(name)}\b", text):
                spans.append((m.start(), m.end(), "NAME"))
        results = _analyzer().analyze(text=text, language="en", entities=list(_ENTITIES))
        for r in results:
            kind = _ENTITIES[r.entity_type]
            raw = text[r.start : r.end]
            if kind == "NAME" and not _looks_like_name(raw):
                continue
            spans.append((r.start, r.end, kind))
        # Apply right-to-left, skipping spans that overlap one already taken.
        out, taken_until = text, len(text) + 1
        for start, end, kind in sorted(spans, key=lambda s: (s[0], -(s[1] - s[0])), reverse=True):
            if end > taken_until:
                continue
            out = out[:start] + self._surrogate(kind, text[start:end]) + out[end:]
            taken_until = start
        return out

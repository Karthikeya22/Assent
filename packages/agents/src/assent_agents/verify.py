"""Citation Verifier (PRODUCT §4.4): verbatim span check, then NLI support. Enforced in code.

A met/not_met verdict needs at least one citation that (1) exists verbatim in its chunk,
whitespace aside, and (2) supports the verdict: P(entailment) for met, P(contradiction) for
not_met, at or above the threshold. Otherwise the verdict becomes `insufficient`; it is never
silently kept, and its citations stay attached with their flags for the audit trail.
"""

import re
from collections.abc import Callable

from assent_agents.evidence.models import Verdict

NLI = Callable[[str, str], dict[str, float]]  # (premise, hypothesis) -> label probabilities
THRESHOLD = 0.7


def find_quote(text: str, quote: str) -> tuple[int, int] | None:
    """Locate `quote` in `text` allowing only whitespace differences; return original offsets."""
    words = quote.split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(w) for w in words)
    m = re.search(pattern, text)
    return (m.start(), m.end()) if m else None


def verify(
    v: Verdict, chunks: dict[str, str], label: str, nli: NLI, threshold: float = THRESHOLD
) -> Verdict:
    if v.verdict == "insufficient":
        return v
    want = "entailment" if v.verdict == "met" else "contradiction"
    cites = []
    for c in v.citations:
        text = chunks.get(c.chunk_id)
        span = find_quote(text, c.quote) if text is not None else None
        if span is None:
            cites.append(c.model_copy(update={"verbatim_ok": False}))
            continue
        support = nli(text[span[0] : span[1]], label)[want]  # type: ignore[index]
        cites.append(
            c.model_copy(
                update={
                    "start": span[0],
                    "end": span[1],
                    "verbatim_ok": True,
                    "support": round(support, 4),
                }
            )
        )
    good = [c for c in cites if c.verbatim_ok and (c.support or 0) >= threshold]
    if good:
        return v.model_copy(update={"citations": cites})
    if not cites:
        reason = "no citations"
    elif not any(c.verbatim_ok for c in cites):
        reason = "no quote found verbatim"
    else:
        reason = f"no verbatim quote reached {want} support {threshold}"
    return v.model_copy(
        update={
            "citations": cites,
            "verdict": "insufficient",
            "original": v.verdict,
            "downgraded": reason,
        }
    )

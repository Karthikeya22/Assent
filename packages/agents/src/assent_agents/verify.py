"""Citation Verifier (PRODUCT §4.4). Enforced in code, not in the prompt.

A met/not_met verdict needs at least one citation that:
1. exists verbatim in its chunk (whitespace aside),
2. grounds the agent's stated claim: NLI(quote ⇒ claim) entailment at or above the threshold,
3. does not come from text flagged as prompt injection.
Otherwise the verdict becomes `insufficient`; it is never silently kept, and its citations stay
attached with their flags for the audit trail.

Why claim-grounding rather than quote ⇒ criterion: small NLI models cannot judge abstract,
disjunctive criteria or thresholds ("6 weeks" ⇒ "at least 4 weeks" scored ~0 on our benchmark).
Whether the grounded fact satisfies the criterion is the agent's reasoning, shown in its
rationale and challenged independently by the Payer Adversary (PRODUCT §4.5).
"""

import re
from collections.abc import Callable

from assent_agents.evidence.models import Verdict
from assent_agents.injection import suspicious_spans

NLI = Callable[[str, str], dict[str, float]]  # (premise, hypothesis) -> label probabilities
THRESHOLD = 0.7


def find_quote(text: str, quote: str) -> tuple[int, int] | None:
    """Locate `quote` in `text` allowing only whitespace differences; return original offsets."""
    words = quote.split()
    if not words:
        return None
    m = re.search(r"\s+".join(re.escape(w) for w in words), text)
    return (m.start(), m.end()) if m else None


def verify(v: Verdict, chunks: dict[str, str], nli: NLI, threshold: float = THRESHOLD) -> Verdict:
    if v.verdict == "insufficient":
        return v
    cites, reasons = [], []
    for c in v.citations:
        text = chunks.get(c.chunk_id)
        span = find_quote(text, c.quote) if text is not None else None
        if span is None:
            cites.append(c.model_copy(update={"verbatim_ok": False}))
            reasons.append("quote not found verbatim")
            continue
        assert text is not None
        if any(s < span[1] and span[0] < e for s, e in suspicious_spans(text)):
            cites.append(
                c.model_copy(
                    update={"start": span[0], "end": span[1], "verbatim_ok": True, "support": 0.0}
                )
            )
            reasons.append("quote is from text flagged as prompt injection")
            continue
        support = nli(text[span[0] : span[1]], c.claim or c.quote)["entailment"]
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
        if support < threshold:
            reasons.append(f"quote does not entail the claim (p={support:.2f})")
    if any(c.verbatim_ok and (c.support or 0) >= threshold for c in cites):
        return v.model_copy(update={"citations": cites})
    reason = "; ".join(dict.fromkeys(reasons)) or "no citations"
    return v.model_copy(
        update={
            "citations": cites,
            "verdict": "insufficient",
            "original": v.verdict,
            "downgraded": reason,
        }
    )

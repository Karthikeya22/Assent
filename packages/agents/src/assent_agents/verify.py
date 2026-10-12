"""Citation Verifier (PRODUCT §4.4). Enforced in code, not in the prompt.

A met/not_met verdict needs at least one citation that:
1. exists verbatim in its chunk (whitespace aside),
2. grounds the agent's stated claim: NLI(passage ⇒ claim) entailment at or above the threshold,
   where the passage is short sentence windows around the quote plus the chunk's date header,
   clinical abbreviations expanded (general NLI can't read "L radic 2/2 HNP"),
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

from pydantic import BaseModel, Field

from assent_agents import prompts
from assent_agents.abbrev import expand
from assent_agents.evidence.models import Verdict
from assent_agents.injection import suspicious_spans
from assent_agents.llm import StructuredLLM

NLI = Callable[[str, str], dict[str, float]]  # (premise, hypothesis) -> label probabilities
THRESHOLD = 0.7


def find_quote(text: str, quote: str) -> tuple[int, int] | None:
    """Locate `quote` in `text` allowing only whitespace differences; return original offsets."""
    words = quote.split()
    if not words:
        return None
    m = re.search(r"\s+".join(re.escape(w) for w in words), text)
    return (m.start(), m.end()) if m else None


WINDOW = 250  # chars of surrounding text the claim may also draw on (same note, same passage)


_SENT = re.compile(r"[^.!?\n]+[.!?]?")


def premises(text: str, span: tuple[int, int], header: str = "") -> list[str]:
    """What the claim may follow from: 3-sentence windows of the quote's local passage.

    NLI degrades on long premises, so (as in SummaC) the claim is scored against each short
    window and the best one counts; on our recorded runs this passed 32/40 grounded claims vs
    25/40 for one long window. Injection-flagged text is blanked first so a claim can't borrow
    support from it through a neighbouring quote. Abbreviations are expanded here only; the
    quote itself was already matched verbatim.
    """
    for s, e in suspicious_spans(text):
        text = text[:s] + " " * (e - s) + text[e:]
    local = text[max(0, span[0] - WINDOW) : span[1] + WINDOW]
    sents = [m.group().strip() for m in _SENT.finditer(local) if m.group().strip()]
    head = f"{header}. " if header else ""
    return [expand(head + " ".join(sents[max(0, i - 1) : i + 2])) for i in range(len(sents))] or [
        expand(head + local)
    ]


def verify(
    v: Verdict,
    chunks: dict[str, str],
    nli: NLI,
    threshold: float = THRESHOLD,
    headers: dict[str, str] | None = None,
) -> Verdict:
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
        claim = expand(c.claim or c.quote)
        support = max(
            nli(p, claim)["entailment"]
            for p in premises(text, span, (headers or {}).get(c.chunk_id, ""))
        )
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


class Judgement(BaseModel):
    supported: bool
    reason: str = Field(max_length=300)


JUDGE_PROMPT = "verify_judge_v1"
JUDGE_SUPPORT = 0.9  # recorded support for a judge-approved citation (>= THRESHOLD)
MAX_JUDGED = 2


async def judge_downgrade(
    v: Verdict, chunks: dict[str, str], llm: StructuredLLM, headers: dict[str, str] | None = None
) -> Verdict:
    """Second opinion when NLI rejected a verbatim, non-injection citation.

    Small NLI misses clinical paraphrase (on our dev run 24 of 31 wrong `insufficient` verdicts
    were NLI false rejections), so a fast LLM judge re-checks the same blanked passage. Only an
    explicit "supported" restores the agent's verdict; anything else keeps the downgrade.
    """
    if v.original is None or v.downgraded is None or "injection" in v.downgraded:
        return v
    cands = [
        i
        for i, c in enumerate(v.citations)
        if c.verbatim_ok
        and c.start is not None
        and c.end is not None
        and not any(
            s < c.end and c.start < e
            for s, e in suspicious_spans(chunks.get(c.chunk_id, ""))
        )
    ]
    for i in cands[:MAX_JUDGED]:
        c = v.citations[i]
        text = chunks[c.chunk_id]
        passage = " ".join(premises(text, (c.start, c.end), (headers or {}).get(c.chunk_id, "")))  # type: ignore[arg-type]
        msgs = [
            {"role": "system", "content": prompts.load(JUDGE_PROMPT)},
            {"role": "user", "content": f"<passage>\n{passage}\n</passage>\n\nClaim: {c.claim}"},
        ]
        j: Judgement = await llm("fast", msgs, Judgement)
        if j.supported:
            cites = list(v.citations)
            cites[i] = c.model_copy(update={"support": JUDGE_SUPPORT, "judged": True})
            return v.model_copy(
                update={
                    "citations": cites,
                    "verdict": v.original,
                    "original": None,
                    "downgraded": None,
                }
            )
    return v

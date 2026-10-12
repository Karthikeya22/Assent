"""Prompt-injection screen for chart text (ARCHITECTURE §7.4, defense in depth).

Chart text is always passed as delimited data; this additionally flags instruction-like spans so
the verifier refuses to accept them as evidence, even from a model that was fooled.
"""

import re

# shortcut: keyword heuristics catch the common phrasings in our injection test set; swap in a
# trained classifier if the Phase 5 injection eval shows misses.
_PATTERNS = [
    r"ignore (?:all |any |your |the )?(?:previous|prior|above|earlier) instructions",
    r"disregard (?:all |any |your |the )?(?:previous|prior|above) (?:instructions|rules)",
    r"(?:note|message|instruction)s? (?:to|for) (?:the )?(?:automated|ai|llm) "
    r"(?:reviewer|model|system)",
    r"mark (?:all|every) (?:criteria|criterion|items?)",
    r"(?:you|the model) (?:must|should) (?:answer|output|respond|mark|approve)",
    r"(?:system|assistant)\s*:",
]
_RX = re.compile("|".join(f"(?:{p})" for p in _PATTERNS), re.I)
_SENTENCE = re.compile(r"[^.!?\n]*[.!?]?")


def suspicious_spans(text: str) -> list[tuple[int, int]]:
    """Whole sentences that contain an instruction-like pattern, plus the sentence after it."""
    sents = [(m.start(), m.end()) for m in _SENTENCE.finditer(text) if m.group().strip()]
    out = []
    for i, (s, e) in enumerate(sents):
        if _RX.search(text[s:e]):
            out.append((s, sents[i + 1][1] if i + 1 < len(sents) else e))
    return out

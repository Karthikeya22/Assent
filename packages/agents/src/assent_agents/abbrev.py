"""Clinical shorthand → plain words, for the NLI premise only (quotes are still checked verbatim).

General-domain NLI can't read "L radic 2/2 L5-S1 HNP"; with these expansions it can.
"""

import re

# shortcut: a fixed list of the abbreviations seen in our notes and Synthea text; grow it from
# verifier downgrade logs (the bench records every downgrade reason).
ABBREV = {
    "radic": "radiculopathy",
    "HNP": "herniated nucleus pulposus (disc herniation)",
    "2/2": "secondary to",
    "w/": "with",
    "w/o": "without",
    "LBP": "low back pain",
    "LE": "lower extremity (leg)",
    "UE": "upper extremity (arm)",
    "sx": "symptoms",
    "D/C": "discharged",
    "d/c": "discharged",
    "PT": "physical therapy",
    "Pt": "patient",
    "pt": "patient",
    "HEP": "home exercise program",
    "Fx": "function",
    "h/o": "history of",
    "B/B": "bowel or bladder",
    "CA": "cancer",
    "ROS": "review of systems",
    "PSH": "past surgical history",
    "A/P": "assessment and plan",
    "d/t": "due to",
    "wks": "weeks",
    "wk": "week",
    "yo": "year old",
    "s/p": "status post",
    "ESI": "epidural steroid injection",
    "NRS": "numeric rating scale",
    "VAS": "visual analog scale",
    "ODI": "Oswestry disability index",
    "neg": "negative",
    "hx": "history",
    "f/u": "follow up",
    "abx": "antibiotics",
    "L": "left",
    "R": "right",
}
_RX = re.compile(
    r"(?<![\w/])(" + "|".join(sorted(map(re.escape, ABBREV), key=len, reverse=True)) + r")(?![\w/])"
)
_DURATION = re.compile(r"\bx\s?(\d+)\s?(weeks|wks|wk|months|mos|days)\b")


def expand(text: str) -> str:
    text = _DURATION.sub(lambda m: f"for {m.group(1)} {m.group(2)}", text)
    return _RX.sub(lambda m: ABBREV[m.group(1)], text)

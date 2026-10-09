"""Clinical notes for a fact sheet: LLM-written (benchmark) or templated (tests, no-key dev).

Either way every non-stale and stale fact sentence must appear verbatim, or the note is rejected.
"""

import random
from datetime import date
from typing import Literal

from pydantic import BaseModel

from assent_agents import prompts
from assent_agents.llm import StructuredLLM
from assent_evals.synth.facts import EsiFacts, Slot
from assent_evals.synth.phrases import AVOID

TITLES: dict[Slot, tuple[str, str]] = {
    "pcp": ("Primary Care Progress Note", "Primary care physician"),
    "pt": ("Physical Therapy Discharge Summary", "Physical therapist"),
    "radiology": ("Radiology Report", "Radiologist"),
    "consult": ("Pain Management Consultation", "Pain medicine physician"),
}
FILLER: dict[Slot, list[str]] = {
    "pcp": [
        "Vitals: BP 134/80, HR 74, T 36.8 C.",
        "Medications reconciled.",
        "Hypertension stable on current regimen.",
        "Return in 3 months for chronic care.",
    ],
    "pt": [
        "Treatment included manual therapy, core stabilization and gait training.",
        "Patient attended sessions as scheduled.",
        "Goals reviewed with patient.",
    ],
    "radiology": [
        "Technique: multiplanar sequences without contrast.",
        "Comparison: none available.",
        "Vertebral body heights are maintained.",
    ],
    "consult": [
        "Referred by primary care for evaluation of spine-related pain.",
        "Medications and allergies reviewed.",
        "Plan: request prior authorization for the ordered injection; follow up after "
        "the procedure.",
    ],
}


class Note(BaseModel):
    slot: Slot
    date: date
    title: str
    author: str
    text: str
    source: Literal["template", "llm"]


class _NoteText(BaseModel):
    text: str


def slots_for(f: EsiFacts) -> list[Slot]:
    used = {s.slot for s in f.statements}
    return [
        s for s in ("pcp", "pt", "radiology", "consult") if s in used or s in ("pcp", "consult")
    ]


def _required(f: EsiFacts, slot: Slot) -> list[str]:
    req = [s.text for s in f.statements if s.slot == slot]
    if f.injection and slot == "pcp":
        req.append(f.injection)
    return req


def template_note(f: EsiFacts, slot: Slot, rng: random.Random) -> Note:
    title, author = TITLES[slot]
    when = f.slot_dates()[slot]
    req = _required(f, slot)
    body = FILLER[slot][:]
    for sentence in req:
        # Buried facts go mid-note between filler, clean ones lead the note.
        pos = rng.randint(1, len(body)) if f.difficulty == "buried" else 0
        body.insert(pos, sentence)
    age = when.year - f.patient.birth_date.year
    head = (
        f"{title}\nDate: {when:%m/%d/%Y}\nPatient: {f.patient.name}, {age}-year-old "
        f"{f.patient.sex}\nAuthor: {author}\n"
    )
    return Note(
        slot=slot,
        date=when,
        title=title,
        author=author,
        text=head + "\n" + "\n".join(body) + "\n",
        source="template",
    )


async def llm_note(f: EsiFacts, slot: Slot, rng: random.Random, llm: StructuredLLM) -> Note:
    title, author = TITLES[slot]
    when = f.slot_dates()[slot]
    req = _required(f, slot)
    avoid = [AVOID[k] for k, v in f.gold.items() if v == "insufficient"]
    style = (
        "terse, heavy abbreviations, facts scattered mid-note"
        if f.difficulty == "buried"
        else "clear and well organized"
    )
    user = (
        f"Note type: {title}\nDate: {when:%m/%d/%Y}\nAuthor: {author}\n"
        f"Patient (synthetic): {f.patient.name}, {when.year - f.patient.birth_date.year}-year-old "
        f"{f.patient.sex}\nStyle: {style}\n\n"
        "Sentences that MUST appear verbatim (copy each exactly, character for character):\n"
        + "\n".join(f"- {s}" for s in req)
        + "\n\nDo NOT mention any of these topics anywhere in the note:\n"
        + ("\n".join(f"- {a}" for a in avoid) or "- (none)")
    )
    msgs = [
        {"role": "system", "content": prompts.load("notes_v1")},
        {"role": "user", "content": user},
    ]
    for _ in range(3):
        out: _NoteText = await llm("fast", msgs, _NoteText)
        if all(s in out.text for s in req):
            return Note(
                slot=slot, date=when, title=title, author=author, text=out.text, source="llm"
            )
    # shortcut: falls back to the template after 3 misses so a build never stalls; the note's
    # `source` records it, and the eval report counts template notes per split.
    return template_note(f, slot, rng)


def check_notes(f: EsiFacts, notes: list[Note]) -> list[str]:
    """Every fact sentence must be present verbatim in its own slot's note."""
    by_slot = {n.slot: n.text for n in notes}
    return [
        f"{s.leaf}: missing from {s.slot} note"
        for s in f.statements
        if s.text not in by_slot.get(s.slot, "")
    ]

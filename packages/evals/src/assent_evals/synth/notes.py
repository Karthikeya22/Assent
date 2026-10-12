"""Clinical notes for a fact sheet: LLM-written (benchmark) or templated (tests, no-key dev).

Either way every non-stale and stale fact sentence must appear verbatim, or the note is rejected.
"""

import random
from datetime import date
from typing import Literal

from pydantic import BaseModel

from assent_agents import prompts
from assent_agents.llm import StructuredLLM
from assent_evals.synth import hgns, pva
from assent_evals.synth.case import Facts
from assent_evals.synth.phrases import AVOID

TITLES: dict[str, tuple[str, str]] = {
    "pcp": ("Primary Care Progress Note", "Primary care physician"),
    "pt": ("Physical Therapy Discharge Summary", "Physical therapist"),
    "radiology": ("Radiology Report", "Radiologist"),
    "consult": ("Pain Management Consultation", "Pain medicine physician"),
}
FILLER: dict[str, list[str]] = {
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
    slot: str
    date: date
    title: str
    author: str
    text: str
    source: Literal["template", "llm"]


class _NoteText(BaseModel):
    text: str


# family -> (note slots oldest-first, titles, filler, topics to avoid per insufficient leaf)
SPECS: dict[
    str, tuple[list[str], dict[str, tuple[str, str]], dict[str, list[str]], dict[str, str]]
] = {
    "esi": (["pcp", "pt", "radiology", "consult"], TITLES, FILLER, AVOID),
    "hgns": (hgns.SLOTS, hgns.TITLES, hgns.FILLER, hgns.AVOID),
    "pva": (pva.SLOTS, pva.TITLES, pva.FILLER, pva.AVOID),
}


def slots_for(f: Facts) -> list[str]:
    used = {s.slot for s in f.statements}
    return [s for s in SPECS[f.family][0] if s in used or s in ("pcp", "consult", "ent")]


def _required(f: Facts, slot: str) -> list[str]:
    req = [s.text for s in f.statements if s.slot == slot]
    if f.injection and slot == "pcp":
        req.append(f.injection)
    return req


def template_note(f: Facts, slot: str, rng: random.Random) -> Note:
    _, titles, filler, _ = SPECS[f.family]
    title, author = titles[slot]
    when = f.slot_dates()[slot]
    req = _required(f, slot)
    body = filler[slot][:]
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


async def llm_note(f: Facts, slot: str, rng: random.Random, llm: StructuredLLM) -> Note:
    _, titles, _, avoid_topics = SPECS[f.family]
    title, author = titles[slot]
    when = f.slot_dates()[slot]
    req = _required(f, slot)
    avoid = [avoid_topics[k] for k, v in f.gold.items() if v == "insufficient"]
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
        missing = [s for s in req if s not in out.text]
        if not missing:
            return Note(
                slot=slot, date=when, title=title, author=author, text=out.text, source="llm"
            )
        # Retry with the exact misses: report-style notes (PSG, radiology) tend to tabulate them.
        msgs = [
            *msgs[:2],
            {"role": "assistant", "content": out.model_dump_json()},
            {
                "role": "user",
                "content": "These sentences were missing or altered. Rewrite the whole note in "
                "prose and include each one exactly, as its own sentence:\n"
                + "\n".join(f"- {s}" for s in missing),
            },
        ]
    # shortcut: falls back to the template after 3 misses so a build never stalls; the note's
    # `source` records it, and the eval report counts template notes per split.
    return template_note(f, slot, rng)


def check_notes(f: Facts, notes: list[Note]) -> list[str]:
    """Every fact sentence must be present verbatim in its own slot's note."""
    by_slot = {n.slot: n.text for n in notes}
    return [
        f"{s.leaf}: missing from {s.slot} note"
        for s in f.statements
        if s.text not in by_slot.get(s.slot, "")
    ]

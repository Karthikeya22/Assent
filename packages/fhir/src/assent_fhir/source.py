"""Where patient data comes from. File-backed for now; HAPI FHIR `$everything` later (Phase 6)."""

import json
from pathlib import Path
from typing import Any, Protocol


class FhirSource(Protocol):
    def everything(self, ref: str) -> list[dict[str, Any]]: ...


class FileFhirSource:
    """Reads `<root>/<ref>.bundle.json` (a transaction bundle) and returns its resources."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def everything(self, ref: str) -> list[dict[str, Any]]:
        bundle = json.loads((self.root / f"{ref}.bundle.json").read_text("utf-8"))
        return [e["resource"] for e in bundle.get("entry", [])]

"""Pull LCDs from the CMS Coverage API into versioned snapshots under data/policies/.

Run: `uv run python -m assent_agents.policy.ingest L39240 L39015 L36920`
"""

import hashlib
import json
import sys
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from assent_agents.policy.html_text import html_to_text

API = "https://api.coverage.cms.gov"
REPO_ROOT = Path(__file__).resolve().parents[5]
POLICY_DIR = REPO_ROOT / "data" / "policies"


@dataclass(frozen=True)
class LcdSnapshot:
    source_id: str  # "L39240"
    lcd_id: int
    version: int
    title: str
    contractor: str
    rev_eff_date: str
    source_url: str
    retrieved_at: str
    raw_text: str
    content_hash: str


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _get(path: str, token: str | None = None) -> Any:
    req = urllib.request.Request(API + path, headers={"Accept": "application/json"})  # noqa: S310
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (fixed https host)
        return json.load(r)


def _license_token() -> str:
    # The LCD body includes AMA CPT content; the API issues a token on accepting its license.
    return str(_get("/v1/metadata/license-agreement/")["data"][0]["Token"])


def _report_row(lcd_id: int) -> dict[str, Any]:
    rows = _get("/v1/reports/local-coverage-final-lcds/?state=all&contractor=all")["data"]
    for row in rows:
        if int(row["document_id"]) == lcd_id:
            return dict(row)
    raise LookupError(f"L{lcd_id} not found among final LCDs")


def fetch_lcd(lcd_id: int, version: int | None = None) -> LcdSnapshot:
    row = _report_row(lcd_id)
    ver = version or int(row["document_version"])
    d = _get(f"/v1/data/lcd/?lcdid={lcd_id}&ver={ver}", _license_token())["data"][0]
    text = html_to_text(d["indication"])
    return LcdSnapshot(
        source_id=f"L{lcd_id}",
        lcd_id=lcd_id,
        version=ver,
        title=d["title"],
        contractor=str(row.get("contractor_name_type", "")).split("\n")[0].strip(),
        rev_eff_date=str(d.get("rev_eff_date") or ""),
        source_url=f"https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid={lcd_id}&ver={ver}",
        retrieved_at=datetime.now(UTC).isoformat(timespec="seconds"),
        raw_text=text,
        content_hash=sha256(text),
    )


def snapshot_path(source_id: str, version: int, root: Path = POLICY_DIR) -> Path:
    return root / f"{source_id}-v{version}.json"


def save_snapshot(s: LcdSnapshot, root: Path = POLICY_DIR) -> Path:
    p = snapshot_path(s.source_id, s.version, root)
    if p.exists():
        old = json.loads(p.read_text("utf-8"))
        if old["content_hash"] != s.content_hash:
            # A version number is immutable upstream; a different body means our parser or the
            # source changed. Never overwrite silently: gold trees quote this exact text.
            raise ValueError(f"{p.name}: content changed upstream for the same version")
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(s), indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n")
    return p


def load_snapshot(source_id: str, version: int, root: Path = POLICY_DIR) -> LcdSnapshot:
    return LcdSnapshot(**json.loads(snapshot_path(source_id, version, root).read_text("utf-8")))


def main(ids: list[str]) -> None:
    for sid in ids:
        s = fetch_lcd(int(sid.lstrip("Ll")))
        print(f"{save_snapshot(s).name}  {len(s.raw_text):>6} chars  {s.title}")


if __name__ == "__main__":
    main(sys.argv[1:])

import json
from pathlib import Path

import pytest

from assent_agents.policy.html_text import html_to_text
from assent_agents.policy.ingest import LcdSnapshot, save_snapshot, sha256

# Shape of the CMS API payload: the HTML itself arrives entity-encoded.
ENCODED = (
    "&lt;p&gt;&lt;strong&gt;Covered Indications &lt;/strong&gt;&lt;/p&gt;"
    "&lt;p&gt;1. ESI is necessary when:&lt;/p&gt;"
    "&lt;ul&gt;&lt;li&gt;Radiculopathy due to disc herniation&lt;sup&gt;5&lt;/sup&gt;; "
    "&lt;strong&gt;OR&lt;/strong&gt;&lt;/li&gt;"
    "&lt;li&gt;Post-laminectomy syndrome&lt;sup&gt;6-8&lt;/sup&gt;&lt;/li&gt;&lt;/ul&gt;"
    "&lt;p&gt;Pain duration of at least four (4)&amp;#160;weeks &amp;#8805; 4&lt;/p&gt;"
)


def test_encoded_html_becomes_structured_text() -> None:
    assert html_to_text(ENCODED) == (
        "Covered Indications\n\n"
        "1. ESI is necessary when:\n\n"
        "- Radiculopathy due to disc herniation; OR\n"
        "- Post-laminectomy syndrome\n\n"
        "Pain duration of at least four (4) weeks ≥ 4"
    )


def test_nested_lists_indent() -> None:
    html = "<ul><li>outer<ul><li>inner</li></ul></li></ul>"
    assert html_to_text(html) == "- outer\n  - inner"


def _snap(text: str) -> LcdSnapshot:
    return LcdSnapshot(
        source_id="L1",
        lcd_id=1,
        version=2,
        title="t",
        contractor="c",
        rev_eff_date="2026-01-01",
        source_url="u",
        retrieved_at="2026-10-09T00:00:00Z",
        raw_text=text,
        content_hash=sha256(text),
    )


def test_save_is_idempotent_and_refuses_silent_overwrite(tmp_path: Path) -> None:
    p = save_snapshot(_snap("abc"), root=tmp_path)
    assert p.name == "L1-v2.json"
    assert json.loads(p.read_text("utf-8"))["raw_text"] == "abc"
    save_snapshot(_snap("abc"), root=tmp_path)  # same content: fine
    with pytest.raises(ValueError, match="changed upstream"):
        save_snapshot(_snap("abd"), root=tmp_path)

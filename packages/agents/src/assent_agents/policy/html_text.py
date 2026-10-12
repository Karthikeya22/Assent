"""LCD HTML → plain text keeping paragraph and list structure, so criteria can quote it verbatim."""

import html
import re
from html.parser import HTMLParser

_BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table"}
_LIST = {"ul", "ol"}


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.depth = 0  # list nesting
        self.skip = 0  # inside <sup>: footnote markers would pollute verbatim quotes

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "sup":
            self.skip += 1
        elif tag in _LIST:
            self.depth += 1
        elif tag == "li":
            self.out.append("\n" + "  " * max(self.depth - 1, 0) + "- ")
        elif tag == "br":
            self.out.append("\n")
        elif tag in _BLOCK:
            self.out.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "sup":
            self.skip = max(self.skip - 1, 0)
        elif tag in _LIST:
            self.depth = max(self.depth - 1, 0)
            if self.depth == 0:
                self.out.append("\n\n")
        elif tag in _BLOCK:
            self.out.append("\n\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.out.append(data)


def html_to_text(s: str) -> str:
    # The CMS API double-encodes: the HTML itself arrives as &lt;p&gt;... so unescape first.
    if "&lt;" in s:
        s = html.unescape(s)
    p = _Text()
    p.feed(s)
    p.close()
    text = "".join(p.out).replace("\xa0", " ")
    lines = [
        re.sub(r"[ \t]+", " ", ln).strip() if not ln.lstrip().startswith("- ") else _indent(ln)
        for ln in text.split("\n")
    ]
    # Bullets with nothing after them come from wrapper <li>s around nested lists.
    lines = [ln for ln in lines if ln.strip() != "-"]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _indent(line: str) -> str:
    lead = len(line) - len(line.lstrip(" "))
    return " " * lead + re.sub(r"[ \t]+", " ", line.strip())

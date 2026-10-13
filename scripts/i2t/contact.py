"""usage: contact.py <dir> <out.jpg> [cols] : tile the chapter screenshots in story order."""

import sys
from pathlib import Path

from PIL import Image

IDS = [
    "hero",
    "problem",
    "policy",
    "chart",
    "prove",
    "verify",
    "argue",
    "packet",
    "use",
    "proof",
    "close",
]
d, out = Path(sys.argv[1]), sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 3
w, h = 640, 400
ims = [
    Image.open(d / f"{i}.jpg").convert("RGB").resize((w, h))
    for i in IDS
    if (d / f"{i}.jpg").exists()
]
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (w * cols, h * rows), "white")
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * w, (k // cols) * h))
sheet.save(out, quality=78)

"""usage: sheet.py <dir> <pass> : ref + front render side by side, then a 4-view turntable strip."""

import sys

from PIL import Image

d, p = sys.argv[1], sys.argv[2]
ref = Image.open(f"{d}/ref.png").convert("RGB").resize((420, 420))
views = [
    Image.open(f"{d}/shots/{p}-{n}.png").convert("RGB").resize((420, 420))
    for n in ["front", "right", "rear", "left"]
]
s = Image.new("RGB", (420 * 5, 420), "white")
s.paste(ref, (0, 0))
for i, v in enumerate(views):
    s.paste(v, (420 * (i + 1), 0))
s.save(f"{d}/shots/review-{p}.jpg", quality=82)

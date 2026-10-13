"""Generate porcelain-style reference images for the landing's 3D objects (img2threejs input).

Usage: uv run python scripts/gen_reference_images.py [--n 2] [--only folder,scales]
Writes .data/refs/<object>-<i>.png. Reads OPENAI_API_KEY from .env.
"""

import argparse
import base64
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".data" / "refs"

# One style for every object so the world reads as one set (DESIGN.md: porcelain and evidence).
STYLE = (
    "Studio product render of a single object made of matte white porcelain with a subtle"
    " soft sheen, softly rounded bevels, simplified stylized forms, small deep teal-green"
    " (#0f6e5c) accent details. Isolated on a plain pale grey-green background (#f3f5f4)."
    " Soft diffuse key light from the upper left, gentle rim light, soft contact shadow "
    "below. Three-quarter view, centered, the whole object visible with margin around it."
    " No text, no letters, no logos, no people."
)

OBJECTS = {
    "folder": (
        "A medical patient chart folder lying slightly open, a few loose paper pages fanning "
        "out of it, a small clip at the top edge."
    ),
    "magnifier": (
        "A magnifying glass with a thick round clear glass lens in a porcelain rim and a "
        "short rounded handle."
    ),
    "scales": (
        "Classical balance scales: a slim central pillar, a horizontal beam, two shallow "
        "round pans hanging on thin chains, beam level."
    ),
    "stamp": (
        "A desk seal stamp with a rounded porcelain handle and a circular base, standing "
        "beside a round deep teal-green wax seal disc embossed with a simple check mark."
    ),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2, help="variants per object")
    ap.add_argument("--only", default="", help="comma-separated object names")
    ap.add_argument("--model", default="gpt-image-1")
    ap.add_argument("--quality", default="medium")
    args = ap.parse_args()

    load_dotenv()  # walks up from this script, so worktrees find the main checkout .env
    client = OpenAI()
    OUT.mkdir(parents=True, exist_ok=True)
    names = [n for n in args.only.split(",") if n] or list(OBJECTS)
    for name in names:
        res = client.images.generate(
            model=args.model,
            prompt=f"{OBJECTS[name]} {STYLE}",
            size="1024x1024",
            quality=args.quality,
            n=args.n,
        )
        for i, img in enumerate(res.data):
            assert img.b64_json, "expected base64 image data"
            path = OUT / f"{name}-{i}.png"
            path.write_bytes(base64.b64decode(img.b64_json))
            print(path)


if __name__ == "__main__":
    main()

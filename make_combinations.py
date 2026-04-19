"""
Combine each montage with an image of its metadata.

For every metadata text file in <dataset>/metadata/, the "Metadata:"
section (everything up to the blank line before "Metadata Information:")
is rendered into a PNG. That metadata PNG is then stacked vertically
below the matching montage in <dataset>/montages/, with both images
scaled to a common width. The result is written to
<dataset>/combination/<ZTFID>.png.

Supported datasets: expert_examples, human_baseline.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent

DATASETS = {
    "expert_examples": "Metadata",
    "human_baseline": "Metadata",
}

TARGET_WIDTH = 900
PAD = 20
LINE_SPACING = 8
TITLE_SIZE = 26
BODY_SIZE = 20
BG = (255, 255, 255)
FG = (20, 20, 20)
TITLE_FG = (0, 0, 0)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def parse_metadata(path: Path) -> list[str]:
    """Return lines belonging to the 'Metadata:' block only."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    in_meta = False
    for ln in lines:
        stripped = ln.strip()
        if stripped.lower().startswith("metadata information"):
            break
        if stripped.lower().startswith("metadata:"):
            in_meta = True
            continue
        if in_meta:
            if stripped == "":
                continue
            out.append(stripped)
    return out


def render_metadata_image(title: str, items: list[str], width: int) -> Image.Image:
    title_font = load_font(TITLE_SIZE)
    body_font = load_font(BODY_SIZE)

    dummy = Image.new("RGB", (10, 10), BG)
    d = ImageDraw.Draw(dummy)

    def text_h(font: ImageFont.FreeTypeFont, s: str = "Ag") -> int:
        bbox = d.textbbox((0, 0), s, font=font)
        return bbox[3] - bbox[1]

    title_h = text_h(title_font)
    body_h = text_h(body_font)

    height = PAD + title_h + PAD // 2 + len(items) * (body_h + LINE_SPACING) + PAD
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    draw.text((PAD, PAD), title, fill=TITLE_FG, font=title_font)

    y = PAD + title_h + PAD // 2
    for line in items:
        draw.text((PAD, y), line, fill=FG, font=body_font)
        y += body_h + LINE_SPACING

    return img


def resize_to_width(img: Image.Image, width: int) -> Image.Image:
    if img.width == width:
        return img
    ratio = width / img.width
    new_h = max(1, int(round(img.height * ratio)))
    return img.resize((width, new_h), Image.LANCZOS)


def ztfid_from_meta(path: Path) -> str:
    m = re.search(r"(ZTF[0-9A-Za-z]+)", path.stem)
    if not m:
        raise ValueError(f"Cannot extract ZTF id from {path.name}")
    return m.group(1)


def process_dataset(dataset: str) -> None:
    meta_dir = ROOT / dataset / "metadata"
    mont_dir = ROOT / dataset / "montages"
    out_dir = ROOT / dataset / "combination"

    if not meta_dir.is_dir() or not mont_dir.is_dir():
        print(f"[skip] {dataset}: metadata/ or montages/ folder missing")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    meta_files = sorted(meta_dir.glob("*.txt"))
    if not meta_files:
        print(f"[skip] {dataset}: no metadata files in {meta_dir}")
        return

    print(f"\n=== {dataset} ===")
    made, missing = 0, []
    for meta_path in meta_files:
        ztfid = ztfid_from_meta(meta_path)
        montage_path = mont_dir / f"{ztfid}.png"
        if not montage_path.exists():
            missing.append(ztfid)
            continue

        items = parse_metadata(meta_path)
        meta_img = render_metadata_image(f"Metadata ({ztfid})", items, TARGET_WIDTH)

        montage = Image.open(montage_path).convert("RGB")
        montage = resize_to_width(montage, TARGET_WIDTH)

        combined = Image.new(
            "RGB",
            (TARGET_WIDTH, montage.height + meta_img.height),
            BG,
        )
        combined.paste(montage, (0, 0))
        combined.paste(meta_img, (0, montage.height))

        out_path = out_dir / f"{ztfid}.png"
        combined.save(out_path)
        made += 1
        print(f"wrote {out_path.relative_to(ROOT)}")

    print(f"Done. {made} combined images written to {out_dir}.")
    if missing:
        print(f"Missing montages for: {', '.join(missing)}")


def main() -> None:
    targets = sys.argv[1:] or list(DATASETS.keys())
    for dataset in targets:
        process_dataset(dataset)


if __name__ == "__main__":
    main()

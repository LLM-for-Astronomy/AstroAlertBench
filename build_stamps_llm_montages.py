"""
Build one PNG montage per object: Science | Reference | Difference (labels on top).
Reads existing FITS under stamps/; writes to --out dir (default: stamps_llm).
Does not modify stamps/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
STAMPS = ROOT / "stamps"
OUT = ROOT / "stamps_llm"

LABELS = ("Science", "Reference", "Difference")
FITS_NAMES = ("science.fits", "template.fits", "difference.fits")

# Layout
PANEL = 63
LABEL_H = 26
GAP_X = 10
PAD_Y = 6
MARGIN = 8
BG = (32, 32, 36)
LABEL_COLOR = (220, 220, 225)


def _stretch_u8(data: np.ndarray) -> np.ndarray:
    x = np.asarray(data, dtype=np.float64)
    x = np.nan_to_num(x, nan=np.nanmedian(x) if np.any(np.isfinite(x)) else 0.0)
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        return np.zeros_like(x, dtype=np.uint8)
    lo, hi = np.percentile(finite, (1.0, 99.0))
    if hi <= lo + 1e-12:
        return np.zeros_like(x, dtype=np.uint8)
    y = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return (y * 255.0).astype(np.uint8)


def _load_stamp(path: Path) -> np.ndarray:
    with fits.open(path, memmap=False) as hdul:
        data = hdul[0].data
        if data is None and len(hdul) > 1:
            data = hdul[1].data
    if data is None:
        raise ValueError(f"no image data in {path}")
    if data.ndim > 2:
        data = np.squeeze(data)
    if data.ndim != 2:
        raise ValueError(f"expected 2D array in {path}, got shape {data.shape}")
    return _stretch_u8(data)


def _font(size: int = 14) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in candidates:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def build_montage(paths: list[Path], font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> Image.Image:
    panels = [_load_stamp(p) for p in paths]
    h_img = panels[0].shape[0]
    w_img = panels[0].shape[1]
    for p in panels[1:]:
        if p.shape != (h_img, w_img):
            raise ValueError("stamp shapes differ; expected matching cutouts")

    col_w = w_img
    total_w = MARGIN * 2 + 3 * col_w + 2 * GAP_X
    total_h = MARGIN * 2 + LABEL_H + PAD_Y + h_img

    out = Image.new("RGB", (total_w, total_h), BG)
    draw = ImageDraw.Draw(out)

    y0 = MARGIN + LABEL_H + PAD_Y
    x = MARGIN
    for i, (label, arr) in enumerate(zip(LABELS, panels, strict=True)):
        cx = x + col_w // 2
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, MARGIN + 2), label, fill=LABEL_COLOR, font=font)
        rgb = np.stack([arr, arr, arr], axis=-1)
        im = Image.fromarray(rgb, mode="RGB")
        if im.size != (w_img, h_img):
            im = im.resize((w_img, h_img), Image.Resampling.NEAREST)
        out.paste(im, (x, y0))
        x += col_w + GAP_X

    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="FITS stamps -> labeled PNG montages")
    ap.add_argument("--force", action="store_true", help="Overwrite existing montage.png")
    ap.add_argument("--out", type=str, default=None, help="Output directory (default: stamps_llm)")
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else OUT

    if not STAMPS.is_dir():
        print(f"Missing stamps dir: {STAMPS}", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    font = _font()

    n_ok = 0
    n_skip = 0
    n_fail = 0

    for class_dir in sorted(STAMPS.iterdir()):
        if not class_dir.is_dir():
            continue
        cname = class_dir.name
        for oid_dir in sorted(class_dir.iterdir()):
            if not oid_dir.is_dir():
                continue
            oid = oid_dir.name
            fits_paths = [oid_dir / fn for fn in FITS_NAMES]
            if not all(p.is_file() for p in fits_paths):
                n_fail += 1
                print(f"skip incomplete FITS {cname}/{oid}", file=sys.stderr)
                continue

            dest_dir = out_dir / cname / oid
            dest = dest_dir / "montage.png"
            if dest.is_file() and not args.force:
                n_skip += 1
                continue

            try:
                img = build_montage(fits_paths, font)
                dest_dir.mkdir(parents=True, exist_ok=True)
                img.save(dest, format="PNG", optimize=True)
                n_ok += 1
            except Exception as e:
                n_fail += 1
                print(f"FAIL {cname}/{oid}: {e}", file=sys.stderr)

    print(f"montage.png written: {n_ok}, skipped (exists): {n_skip}, failed/incomplete: {n_fail}")
    print(f"Output root: {out_dir}")


if __name__ == "__main__":
    main()

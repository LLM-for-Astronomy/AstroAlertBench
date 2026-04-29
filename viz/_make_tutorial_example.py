"""Generate human_samples/tutorial_example/{combination,metadata,montages}/ for
one manually-chosen datapoint.

Selection criteria (already verified): oid must be in manifest_benchmark_final.csv,
not overlap expert_examples or human_baselines, and both Kimi-K2.5 and
Qwen3.5-397B-A17B (thinking) must have classified it correctly. ZTF23abbaqzy
(target_class=SN, ALERCE p=0.941) was picked — a textbook SN on a host galaxy
that both models get right with clean reasoning.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prompts import STAMPS_LLM_DIRNAME

OID = "ZTF23abbaqzy"
TARGET_CLASS = "SN"

SRC_MONTAGE = PROJECT_ROOT / STAMPS_LLM_DIRNAME / TARGET_CLASS / OID / "montage.png"
MANIFEST = PROJECT_ROOT / "data" / "manifest_benchmark_final.csv"

OUT_ROOT = PROJECT_ROOT / "human_samples" / "tutorial_example"
OUT_MONTAGE = OUT_ROOT / "montages" / f"{OID}.png"
OUT_METADATA = OUT_ROOT / "metadata" / f"tutorialexamplemetadata-{OID}.txt"
OUT_COMBO = OUT_ROOT / "combination" / f"{OID}.png"


# 19 fields, in the same order and with the same display names as the existing
# human_baselines and expert_examples metadata files.
FIELDS: list[tuple[str, str, str]] = [
    ("Observation Time (MJD)", "firstmjd", "{:.4f}"),
    ("Filter Band", "fid_band", "{}"),
    ("PSF Magnitude", "magpsf", "{:.4f}"),
    ("Magnitude Uncertainty", "sigmapsf", "{:.4f}"),
    ("Flux Change Direction", "isdiffpos", "{}"),
    ("FWHM", "fwhm", "{:.4f}"),
    ("Nearest-source Star/Galaxy Score", "sgscore1", "{:.4f}"),
    ("Distance to Nearest Reference Source", "distpsnr1", "{:.4f}"),
    ("Star-classifier Score", "classtar", "{:.4f}"),
    ("Reference-source Chi", "chinr", "{:.4f}"),
    ("Reference-source Sharpness", "sharpnr", "{:.4f}"),
    ("Historical Detections", "ndethist", "{:d}"),        # alert-level
    ("Historical Coverages", "ncovhist", "{:d}"),         # alert-level
    ("Detection Time Span in days", "deltajd", "{:.4f}"),
    ("PS1 g-band Magnitude", "sgmag1", "{:.4f}"),
    ("PS1 r-band Magnitude", "srmag1", "{:.4f}"),
    ("PS1 i-band Magnitude", "simag1", "{:.4f}"),
    ("PS1 z-band Magnitude", "szmag1", "{:.4f}"),
    ("PS1 Match Count", "nmtchps", "{:d}"),
]

DEFINITIONS: dict[str, str] = {
    "firstmjd": "Modified Julian Date of the first detection",
    "fid_band": "Observing filter (g, r, or i)",
    "magpsf": "Brightness from PSF-fit photometry; lower = brighter",
    "sigmapsf": "1-sigma uncertainty on the PSF magnitude",
    "isdiffpos": "Whether the source is brighter (positive) or fainter (negative) than reference",
    "fwhm": "Full width at half maximum of the detected source (seeing proxy)",
    "sgscore1": "Star/galaxy score for nearest PS1 source; ~1 = star-like, ~0 = galaxy-like",
    "distpsnr1": "Angular distance (arcsec) to the nearest reference catalog source",
    "classtar": "SExtractor morphology classifier; ~1 = point source, ~0 = extended",
    "chinr": "Chi-squared of PSF fit to the nearest reference source; ~1 = well-fit point source",
    "sharpnr": "Sharpness of nearest reference source; ~0 = point source, large positive = extended/blended",
    "ndethist": "Number of prior detections associated with this source",
    "ncovhist": "Number of prior images covering this sky position",
    "deltajd": "Elapsed days between first and last detection; 0 = single detection",
    "sgmag1": "Pan-STARRS1 g-band magnitude of nearest cross-matched source",
    "srmag1": "Pan-STARRS1 r-band magnitude of nearest cross-matched source",
    "simag1": "Pan-STARRS1 i-band magnitude of nearest cross-matched source",
    "szmag1": "Pan-STARRS1 z-band magnitude of nearest cross-matched source",
    "nmtchps": "Number of PS1 catalog sources within matching radius; 0/N/A = no counterpart",
}


def _col(row: pd.Series, name: str):
    """Prefer alert_* variants to match how prompts.manifest_row_to_metadata resolves
    `ndethist` / `ncovhist` (see prompts.py)."""
    if name == "ndethist":
        return row["alert_ndethist"] if pd.notna(row.get("alert_ndethist")) else row["ndethist"]
    if name == "ncovhist":
        return row["alert_ncovhist"] if pd.notna(row.get("alert_ncovhist")) else row["ncovhist"]
    return row[name]


def _fmt(name: str, fmt: str, raw) -> str:
    if pd.isna(raw):
        return "N/A"
    if name == "isdiffpos":
        v = str(raw).strip().lower()
        if v in ("t", "1", "positive", "+"):
            return "positive"
        if v in ("f", "0", "negative", "-"):
            return "negative"
        return str(raw)
    if fmt == "{:d}":
        return fmt.format(int(raw))
    if fmt == "{}":
        return str(raw)
    return fmt.format(float(raw))


def build_metadata_lines(row: pd.Series) -> list[str]:
    lines: list[str] = ["Metadata:"]
    for i, (label, col, fmt) in enumerate(FIELDS, 1):
        val = _fmt(col, fmt, _col(row, col))
        lines.append(f"{i}. {label} ({col}): {val}")
    lines.append("")
    lines.append("Metadata Information:")
    for i, (label, col, _) in enumerate(FIELDS, 1):
        lines.append(f"{i}. {label} ({col}): {DEFINITIONS[col]}")
    return lines


def write_metadata_txt(row: pd.Series) -> None:
    OUT_METADATA.parent.mkdir(parents=True, exist_ok=True)
    OUT_METADATA.write_text("\n".join(build_metadata_lines(row)) + "\n", encoding="utf-8")
    print(f"wrote {OUT_METADATA}")


def write_relabeled_montage() -> None:
    """Produce a 225x111 PNG that looks like human_baselines/montages/*.png:
    same stamp strip as the source montage, but with the top header relabeled
    from 'Science / Template / Image' to 'Science / Reference / Difference'."""
    OUT_MONTAGE.parent.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC_MONTAGE).convert("RGB")
    W, H = src.size  # (225, 111)
    stamp_strip = src.crop((0, 37, W, 103))  # rows measured empirically

    out = Image.new("RGB", (W, H), (30, 30, 30))
    # Paste stamp strip in the same vertical position as the source montage.
    out.paste(stamp_strip, (0, 37))

    # Draw the new header labels centered above each of the 3 stamps.
    draw = ImageDraw.Draw(out)
    # Small label font sized to fit 225-px-wide strip.
    for size in (12, 11, 10, 9, 8):
        font = _load_mono_font(size)
        widths = [draw.textbbox((0, 0), lbl, font=font)[2] for lbl in ("Science", "Reference", "Difference")]
        if max(widths) <= (W // 3) - 4:
            break
    third = W // 3
    for i, label in enumerate(("Science", "Reference", "Difference")):
        bbox = draw.textbbox((0, 0), label, font=font)
        tx = i * third + (third - (bbox[2] - bbox[0])) // 2
        ty = (37 - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((tx, ty), label, fill=(230, 230, 230), font=font)

    out.save(OUT_MONTAGE)
    print(f"wrote {OUT_MONTAGE}  size={out.size}")


# Retained for backwards compatibility — unused now.
def copy_montage() -> None:
    OUT_MONTAGE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_MONTAGE, OUT_MONTAGE)
    print(f"wrote {OUT_MONTAGE}")


def _load_mono_font(size: int) -> ImageFont.ImageFont:
    """Try a couple of common monospace fonts on Windows before falling back."""
    for candidate in ("consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_combination_image(row: pd.Series) -> None:
    """Stack the upscaled montage (top, dark) above the short-form metadata (bottom,
    white). Layout matches human_baselines/combination/*.png stylistically."""
    OUT_COMBO.parent.mkdir(parents=True, exist_ok=True)

    CANVAS_W = 900

    # ---- Top: montage panel (dark) ---------------------------------------
    # The raw ZTF montage PNG has its own baked-in headers ("Science / Template /
    # Image"). For consistency with human_baselines/combination/*, we crop the
    # header band off and redraw fresh "Science / Reference / Difference" labels
    # over the stamp strip. The empirically-measured header region for 225x111
    # montages is y in [0, 37); stamps occupy y in [37, 103).
    mont_full = Image.open(SRC_MONTAGE).convert("RGB")
    mont_strip = mont_full.crop((0, 37, mont_full.size[0], 103))
    scale = (CANVAS_W - 40) / mont_strip.size[0]
    stamps_w = int(mont_strip.size[0] * scale)
    stamps_h = int(mont_strip.size[1] * scale)
    mont_big = mont_strip.resize((stamps_w, stamps_h), Image.NEAREST)

    header_font = _load_mono_font(42)
    header_h = 100  # tall header row to fit "Science / Reference / Difference"
    top_pad = 30
    top_panel_h = top_pad + header_h + stamps_h + top_pad
    top_panel = Image.new("RGB", (CANVAS_W, top_panel_h), (30, 30, 30))
    draw = ImageDraw.Draw(top_panel)

    # Center each header over its third of the stamps strip.
    third_w = stamps_w // 3
    x_left_strip = (CANVAS_W - stamps_w) // 2
    for i, label in enumerate(("Science", "Reference", "Difference")):
        bbox = draw.textbbox((0, 0), label, font=header_font)
        tx = x_left_strip + i * third_w + (third_w - (bbox[2] - bbox[0])) // 2
        ty = top_pad + (header_h - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((tx, ty), label, fill=(230, 230, 230), font=header_font)
    top_panel.paste(mont_big, (x_left_strip, top_pad + header_h))

    # ---- Bottom: metadata panel (white, short form only) -----------------
    title_font = _load_mono_font(28)
    text_font = _load_mono_font(22)
    short_lines: list[str] = [f"Metadata ({OID})"]
    for i, (label, col, fmt) in enumerate(FIELDS, 1):
        val = _fmt(col, fmt, _col(row, col))
        short_lines.append(f"{i}. {label} ({col}): {val}")

    # Measure needed height.
    line_h = 30
    title_h = 46
    pad_y = 20
    pad_x = 30
    body_h = pad_y + title_h + len(short_lines[1:]) * line_h + pad_y

    bottom_panel = Image.new("RGB", (CANVAS_W, body_h), (255, 255, 255))
    bdraw = ImageDraw.Draw(bottom_panel)
    bdraw.text((pad_x, pad_y), short_lines[0], fill=(0, 0, 0), font=title_font)
    y = pad_y + title_h
    for ln in short_lines[1:]:
        bdraw.text((pad_x, y), ln, fill=(0, 0, 0), font=text_font)
        y += line_h

    # ---- Stack -----------------------------------------------------------
    out = Image.new("RGB", (CANVAS_W, top_panel_h + body_h), (255, 255, 255))
    out.paste(top_panel, (0, 0))
    out.paste(bottom_panel, (0, top_panel_h))
    out.save(OUT_COMBO)
    print(f"wrote {OUT_COMBO}  size={out.size}")


def main() -> None:
    if not SRC_MONTAGE.is_file():
        print(f"Missing montage: {SRC_MONTAGE}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(MANIFEST)
    hit = df[df["oid"] == OID]
    if hit.empty:
        print(f"{OID} not in {MANIFEST}", file=sys.stderr)
        sys.exit(1)
    row = hit.iloc[0]

    write_metadata_txt(row)
    write_relabeled_montage()
    build_combination_image(row)


if __name__ == "__main__":
    main()

"""Generate 5 additional human_samples/human_baselines/{combination,metadata,montages}/
entries (one per class) from data/manifest_fewshot.csv.

Picks (distinct from the 30 existing baselines+expert examples, highest ALERCE
probability per class from manifest_fewshot.csv):

    SN        ZTF18abjjgwy  p=0.9412
    AGN       ZTF20abodaqn  p=0.8833
    VS        ZTF23abntiay  p=0.9625
    asteroid  ZTF26aargnnv  p=1.0000
    bogus     ZTF22abiaehs  p=0.9689

Layout, metadata field set, and image style match
viz/_make_tutorial_example.py (headers relabeled to Science / Reference /
Difference, metadata prefix humanbaselinemetadata-<OID>.txt).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prompts import STAMPS_LLM_DIRNAME

MANIFEST = PROJECT_ROOT / "data" / "manifest_fewshot.csv"
OUT_ROOT = PROJECT_ROOT / "human_samples" / "human_baselines"

PICKS: list[tuple[str, str]] = [
    ("ZTF18abjjgwy", "SN"),
    ("ZTF20abodaqn", "AGN"),
    ("ZTF23abntiay", "VS"),
    ("ZTF26aargnnv", "asteroid"),
    ("ZTF22abiaehs", "bogus"),
]


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
    ("Historical Detections", "ndethist", "{:d}"),
    ("Historical Coverages", "ncovhist", "{:d}"),
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
    if name == "ndethist":
        if "alert_ndethist" in row and pd.notna(row.get("alert_ndethist")):
            return row["alert_ndethist"]
        return row["ndethist"]
    if name == "ncovhist":
        if "alert_ncovhist" in row and pd.notna(row.get("alert_ncovhist")):
            return row["alert_ncovhist"]
        return row["ncovhist"]
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


def _load_mono_font(size: int) -> ImageFont.ImageFont:
    for candidate in ("consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


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


def write_metadata_txt(oid: str, row: pd.Series) -> Path:
    out = OUT_ROOT / "metadata" / f"humanbaselinemetadata-{oid}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(build_metadata_lines(row)) + "\n", encoding="utf-8")
    return out


def write_relabeled_montage(oid: str, src_montage: Path) -> Path:
    """225x111 montage with Science / Reference / Difference labels (matches
    the style used for tutorial_example and existing human_baselines)."""
    out = OUT_ROOT / "montages" / f"{oid}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    src = Image.open(src_montage).convert("RGB")
    W, H = src.size
    stamp_strip = src.crop((0, 37, W, 103))

    canvas = Image.new("RGB", (W, H), (30, 30, 30))
    canvas.paste(stamp_strip, (0, 37))

    draw = ImageDraw.Draw(canvas)
    for size in (12, 11, 10, 9, 8):
        font = _load_mono_font(size)
        widths = [
            draw.textbbox((0, 0), lbl, font=font)[2]
            for lbl in ("Science", "Reference", "Difference")
        ]
        if max(widths) <= (W // 3) - 4:
            break
    third = W // 3
    for i, label in enumerate(("Science", "Reference", "Difference")):
        bbox = draw.textbbox((0, 0), label, font=font)
        tx = i * third + (third - (bbox[2] - bbox[0])) // 2
        ty = (37 - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((tx, ty), label, fill=(230, 230, 230), font=font)

    canvas.save(out)
    return out


def build_combination_image(oid: str, row: pd.Series, src_montage: Path) -> Path:
    """Montage (dark, top) + short-form metadata (white, bottom)."""
    out = OUT_ROOT / "combination" / f"{oid}.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    CANVAS_W = 900

    mont_full = Image.open(src_montage).convert("RGB")
    mont_strip = mont_full.crop((0, 37, mont_full.size[0], 103))
    scale = (CANVAS_W - 40) / mont_strip.size[0]
    stamps_w = int(mont_strip.size[0] * scale)
    stamps_h = int(mont_strip.size[1] * scale)
    mont_big = mont_strip.resize((stamps_w, stamps_h), Image.NEAREST)

    header_font = _load_mono_font(42)
    header_h = 100
    top_pad = 30
    top_panel_h = top_pad + header_h + stamps_h + top_pad
    top_panel = Image.new("RGB", (CANVAS_W, top_panel_h), (30, 30, 30))
    draw = ImageDraw.Draw(top_panel)

    third_w = stamps_w // 3
    x_left_strip = (CANVAS_W - stamps_w) // 2
    for i, label in enumerate(("Science", "Reference", "Difference")):
        bbox = draw.textbbox((0, 0), label, font=header_font)
        tx = x_left_strip + i * third_w + (third_w - (bbox[2] - bbox[0])) // 2
        ty = top_pad + (header_h - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((tx, ty), label, fill=(230, 230, 230), font=header_font)
    top_panel.paste(mont_big, (x_left_strip, top_pad + header_h))

    title_font = _load_mono_font(28)
    text_font = _load_mono_font(22)
    short_lines: list[str] = [f"Metadata ({oid})"]
    for i, (label, col, fmt) in enumerate(FIELDS, 1):
        val = _fmt(col, fmt, _col(row, col))
        short_lines.append(f"{i}. {label} ({col}): {val}")

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

    canvas = Image.new("RGB", (CANVAS_W, top_panel_h + body_h), (255, 255, 255))
    canvas.paste(top_panel, (0, 0))
    canvas.paste(bottom_panel, (0, top_panel_h))
    canvas.save(out)
    return out


def main() -> None:
    df = pd.read_csv(MANIFEST)
    df_by_oid = {str(r["oid"]): r for _, r in df.iterrows()}

    for oid, target_class in PICKS:
        if oid not in df_by_oid:
            print(f"[SKIP] {oid}: not in {MANIFEST}", file=sys.stderr)
            continue
        row = df_by_oid[oid]
        src_montage = PROJECT_ROOT / STAMPS_LLM_DIRNAME / target_class / oid / "montage.png"
        if not src_montage.is_file():
            print(f"[SKIP] {oid}: missing {src_montage}", file=sys.stderr)
            continue

        m = write_metadata_txt(oid, row)
        mn = write_relabeled_montage(oid, src_montage)
        cb = build_combination_image(oid, row, src_montage)
        print(f"[OK] {oid} ({target_class})")
        print(f"     metadata    -> {m.relative_to(PROJECT_ROOT)}")
        print(f"     montage     -> {mn.relative_to(PROJECT_ROOT)}")
        print(f"     combination -> {cb.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

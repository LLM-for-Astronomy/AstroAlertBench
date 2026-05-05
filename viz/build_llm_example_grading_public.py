"""Build human_samples/llm_example_grading_public/ for 20 benchmark OIDs (4 per class).

Layout::

    separate/<target_class>/<oid>/<OID> - <model_slug>.png   # 13 stacked images per OID
    total/<same basename>   # flat copy; names are globally unique (oid × model)

Each PNG stacks (top) the montage + metadata panel (same as human_baselines /
llm_example_grading_zooniverse) and (bottom) Part B leading + alternative text plus
predicted vs gold class — matching the public grading figure style.

``examples/`` holds a single illustrative stacked PNG for one OID **not** in the 20-row
public grid (same layout; one model). Regenerate with::

    python -m viz.build_llm_example_grading_public examples

Selection (from data/manifest_benchmark_final.csv, n=1500):

- Gold class one of SN / AGN / VS / asteroid / bogus; exactly 4 OIDs per class.
- Every OID must have a **parseable 5-class Part C** in **all 13** benchmark run.jsonl
  files (see RUN_SPECS in viz.build_llm_example_grading).
- Part B **leading_interpretation_and_support** and **alternative_analysis** must be
  non-empty strings after strip().
- Metadata must pass the same \"usable combination\" filter as
  viz.build_llm_example_grading_zooniverse (core fields not NaN / not -999 sentinel;
  at least one PS1 band present).

Run from repo root::

    python -m viz.build_llm_example_grading_public

Requires benchmark ``runs/.../run.jsonl`` and ``stamps_llm_updated/<class>/<oid>/montage.png``.
"""
from __future__ import annotations

import shutil
import sys
import textwrap
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prompts import STAMPS_LLM_DIRNAME

import viz._make_human_baselines_batch as hb
from viz.build_llm_example_grading import (
    MANIFEST,
    RUN_SPECS,
    _final_class_from_parsed,
    _load_jsonl_index,
    _part_b_texts,
)
from viz.build_llm_example_grading_zooniverse import (
    _grading_text_lines,
    _flatten_wrapped,
    _parsed_dict,
    _pred_from_rec,
    _manifest_usable_for_combination,
)

# Bottom text panel only (public pack): full width to match combination montage (900px),
# tight insets (smaller on the right so copy uses more width), larger type than zooniverse.
GRADING_PANEL_W = 900
GRADING_TEXT_MARGIN_L = 8
GRADING_TEXT_MARGIN_R = 4
GRADING_WRAP_CHARS = 94
# Body paragraphs; section labels use body + GRADING_HEADER_EXTRA_PT so titles stand out.
GRADING_BODY_FONT_SIZES = (17, 16, 15, 14)
GRADING_HEADER_EXTRA_PT = 2
GRADING_LINE_GAP = 6
# Section labels only: nudge slightly right (body paragraphs unchanged).
GRADING_HEADER_MARGIN_L_EXTRA = 3

_GRADING_HEADER_EXACT = frozenset(
    ("Leading Interpretation and Support:", "Alternative Analysis:")
)


def _grading_line_uses_header_font(ln: str) -> bool:
    if ln in _GRADING_HEADER_EXACT:
        return True
    return ln.startswith("LLM's Classification:") or ln.startswith("Correct Class:")

# Metadata strip (combination PNG): slightly smaller type + less horizontal padding than defaults.
PUBLIC_METADATA_TITLE_PT = 24
PUBLIC_METADATA_BODY_PT = 18
PUBLIC_METADATA_PAD_X = 18

BASE_OUT = PROJECT_ROOT / "human_samples" / "llm_example_grading_public"
SEPARATE = BASE_OUT / "separate"
TOTAL = BASE_OUT / "total"
EXAMPLES_DIR = BASE_OUT / "examples"

# One stacked figure in examples/: benchmark run used for Part B / Part C text.
EXAMPLE_RUN_FOLDER = "gemini25_flash_none"

CLASSES_5 = ("SN", "AGN", "VS", "asteroid", "bogus")
PER_CLASS = 4


def _render_grading_image(body_lines: list[str]) -> Image.Image:
    """White grading panel: same width as montage+metadata (900); asymmetric L/R inset."""
    draw_tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    max_w_body = GRADING_PANEL_W - GRADING_TEXT_MARGIN_L - GRADING_TEXT_MARGIN_R
    max_w_header = (
        GRADING_PANEL_W
        - GRADING_TEXT_MARGIN_L
        - GRADING_HEADER_MARGIN_L_EXTRA
        - GRADING_TEXT_MARGIN_R
    )
    flat: list[str] = []
    body_font = hb._load_mono_font(GRADING_BODY_FONT_SIZES[0])
    header_font = body_font

    for body_pt in GRADING_BODY_FONT_SIZES:
        body_font = hb._load_mono_font(body_pt)
        header_font = hb._load_mono_font(body_pt + GRADING_HEADER_EXTRA_PT)
        flat = _flatten_wrapped(body_lines, GRADING_WRAP_CHARS)
        if not flat:
            break
        fits = True
        for ln in flat:
            if not ln:
                continue
            is_h = _grading_line_uses_header_font(ln)
            f = header_font if is_h else body_font
            limit = max_w_header if is_h else max_w_body
            bbox = draw_tmp.textbbox((0, 0), ln, font=f)
            if bbox[2] - bbox[0] > limit:
                fits = False
                break
        if fits:
            break

    y = GRADING_TEXT_MARGIN_L
    positions: list[tuple[str, int, ImageFont.ImageFont]] = []
    for ln in flat:
        f = header_font if ln and _grading_line_uses_header_font(ln) else body_font
        bbox = draw_tmp.textbbox((0, 0), ln or " ", font=f)
        h = bbox[3] - bbox[1]
        positions.append((ln, y, f))
        y += h + GRADING_LINE_GAP

    canvas_w = GRADING_PANEL_W
    vm = max(GRADING_TEXT_MARGIN_L, GRADING_TEXT_MARGIN_R)
    canvas_h = max(vm * 2 + 40, y + GRADING_TEXT_MARGIN_R)
    img = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for ln, y0, f in positions:
        is_h = bool(ln) and _grading_line_uses_header_font(ln)
        x0 = GRADING_TEXT_MARGIN_L + (GRADING_HEADER_MARGIN_L_EXTRA if is_h else 0)
        draw.text((x0, y0), ln, fill=(0, 0, 0), font=f)
    return img


def _vstack_centered(top: Image.Image, bottom: Image.Image) -> Image.Image:
    w = max(top.width, bottom.width)
    h = top.height + bottom.height
    out = Image.new("RGB", (w, h), (255, 255, 255))
    out.paste(top, ((w - top.width) // 2, 0))
    out.paste(bottom, ((w - bottom.width) // 2, top.height))
    return out


def _oid_passes(
    oid: str,
    gold: str,
    row: pd.Series,
    store_by_folder: dict[str, dict[str, dict]],
) -> bool:
    if not _manifest_usable_for_combination(row):
        return False
    montage = PROJECT_ROOT / STAMPS_LLM_DIRNAME / gold / oid / "montage.png"
    if not montage.is_file():
        return False
    for _slug, _jp, folder in RUN_SPECS:
        store = store_by_folder.get(folder)
        if not store:
            continue
        rec = store.get(oid)
        pred = _pred_from_rec(rec)
        if pred is None:
            return False
        parsed = _parsed_dict(rec)
        lead, alt = _part_b_texts(parsed)
        if not lead or not alt:
            return False
    return True


def _pick_oids_for_class(
    gold: str,
    df: pd.DataFrame,
    store_by_folder: dict[str, dict[str, dict]],
) -> list[str]:
    sub = df[df["target_class"].astype(str) == gold].copy()
    oids: list[str] = []
    for oid in sorted(sub["oid"].astype(str).unique()):
        if len(oids) >= PER_CLASS:
            break
        row = sub[sub["oid"].astype(str) == oid].iloc[0]
        if _oid_passes(str(oid), gold, row, store_by_folder):
            oids.append(str(oid))
    return oids


def _public_oid_set(df: pd.DataFrame, store_by_folder: dict[str, dict[str, dict]]) -> set[str]:
    """OIDs used in separate/ and total/ (4 per class)."""
    out: set[str] = set()
    for cls in CLASSES_5:
        for oid in _pick_oids_for_class(cls, df, store_by_folder):
            out.add(oid)
    return out


def build_examples_figure() -> Path:
    """Write ``examples/<OID> - <run>_example.png`` for one OID outside the public 20."""
    df = pd.read_csv(MANIFEST, low_memory=False)
    store_by_folder: dict[str, dict[str, dict]] = {}
    for slug, jpath, folder in RUN_SPECS:
        if not jpath.is_file():
            print(f"[WARN] missing {jpath} — cannot build examples/", file=sys.stderr)
            continue
        store_by_folder[folder] = _load_jsonl_index(jpath)

    if len(store_by_folder) != 13:
        print(
            f"[FATAL] need all 13 benchmark run.jsonl files; loaded {len(store_by_folder)}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if EXAMPLE_RUN_FOLDER not in store_by_folder:
        print(f"[FATAL] unknown EXAMPLE_RUN_FOLDER={EXAMPLE_RUN_FOLDER!r}", file=sys.stderr)
        sys.exit(1)

    public_oids = _public_oid_set(df, store_by_folder)
    df_oid = {str(r["oid"]): r for _, r in df.iterrows()}

    chosen: tuple[str, str] | None = None
    for oid in sorted(df["oid"].astype(str).unique()):
        if oid in public_oids:
            continue
        row = df_oid.get(oid)
        if row is None:
            continue
        gold = str(row["target_class"])
        if gold not in CLASSES_5:
            continue
        if _oid_passes(oid, gold, row, store_by_folder):
            chosen = (oid, gold)
            break

    if chosen is None:
        print("[FATAL] no manifest OID outside public 20 passes the same filters.", file=sys.stderr)
        sys.exit(1)

    oid, gold = chosen
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for p in EXAMPLES_DIR.glob("*.png"):
        p.unlink()

    tmp_root = EXAMPLES_DIR / "_tmp_build"
    shutil.rmtree(tmp_root, ignore_errors=True)
    tmp_root.mkdir(parents=True)
    hb.OUT_ROOT = tmp_root

    row = df_oid[oid]
    src_montage = PROJECT_ROOT / STAMPS_LLM_DIRNAME / gold / oid / "montage.png"
    comb_path = hb.build_combination_image(
        oid,
        row,
        src_montage,
        metadata_title_pt=PUBLIC_METADATA_TITLE_PT,
        metadata_body_pt=PUBLIC_METADATA_BODY_PT,
        metadata_pad_x=PUBLIC_METADATA_PAD_X,
    )
    comb_img = Image.open(comb_path).convert("RGB")

    rec = store_by_folder[EXAMPLE_RUN_FOLDER].get(oid)
    parsed = _parsed_dict(rec) if rec else {}
    lead, alt = _part_b_texts(parsed)
    pred = _pred_from_rec(rec) if rec else None
    lines = _grading_text_lines(lead, alt, pred, gold)
    text_img = _render_grading_image(lines)
    stacked = _vstack_centered(comb_img, text_img)

    out_path = EXAMPLES_DIR / f"{oid} - {EXAMPLE_RUN_FOLDER}_example.png"
    stacked.save(out_path)

    shutil.rmtree(tmp_root, ignore_errors=True)
    rel = out_path.relative_to(PROJECT_ROOT)
    print(f"[OK] examples (OID not in public 20): {oid} ({gold}) -> {rel}")
    return out_path


def main() -> None:
    df = pd.read_csv(MANIFEST, low_memory=False)
    store_by_folder: dict[str, dict[str, dict]] = {}
    for slug, jpath, folder in RUN_SPECS:
        if not jpath.is_file():
            print(f"[WARN] missing {jpath} — cannot validate or build for {folder}", file=sys.stderr)
            continue
        store_by_folder[folder] = _load_jsonl_index(jpath)

    if len(store_by_folder) != 13:
        print(
            f"[FATAL] need all 13 benchmark run.jsonl files; loaded {len(store_by_folder)}.",
            file=sys.stderr,
        )
        sys.exit(1)

    picks: dict[str, list[str]] = {}
    for cls in CLASSES_5:
        picks[cls] = _pick_oids_for_class(cls, df, store_by_folder)
        if len(picks[cls]) < PER_CLASS:
            print(
                f"[FATAL] class {cls}: only found {len(picks[cls])}/{PER_CLASS} OIDs "
                "matching metadata + 13× parseable Part C + non-empty Part B texts.",
                file=sys.stderr,
            )
            print(f"        candidates tried (sorted): first few ...", file=sys.stderr)
            sys.exit(1)

    SEPARATE.mkdir(parents=True, exist_ok=True)
    TOTAL.mkdir(parents=True, exist_ok=True)
    for p in TOTAL.glob("*.png"):
        p.unlink()

    df_oid = {str(r["oid"]): r for _, r in df.iterrows()}

    for cls in CLASSES_5:
        for oid in picks[cls]:
            row = df_oid[oid]
            oid_dir = SEPARATE / cls / oid
            if oid_dir.is_file():
                oid_dir.unlink()
            shutil.rmtree(oid_dir, ignore_errors=True)
            oid_dir.mkdir(parents=True, exist_ok=True)

            hb.OUT_ROOT = oid_dir
            src_montage = PROJECT_ROOT / STAMPS_LLM_DIRNAME / cls / oid / "montage.png"
            comb_path = hb.build_combination_image(
                oid,
                row,
                src_montage,
                metadata_title_pt=PUBLIC_METADATA_TITLE_PT,
                metadata_body_pt=PUBLIC_METADATA_BODY_PT,
                metadata_pad_x=PUBLIC_METADATA_PAD_X,
            )
            comb_img = Image.open(comb_path).convert("RGB")
            # Drop intermediate combination/ to keep only final 13 PNGs in oid_dir
            comb_dir = oid_dir / "combination"
            if comb_dir.is_dir():
                shutil.rmtree(comb_dir)

            for _slug, _jpath, folder in RUN_SPECS:
                rec = store_by_folder[folder].get(oid)
                parsed = _parsed_dict(rec) if rec else {}
                lead, alt = _part_b_texts(parsed)
                pred = _pred_from_rec(rec) if rec else None
                lines = _grading_text_lines(lead, alt, pred, cls)
                text_img = _render_grading_image(lines)
                stacked = _vstack_centered(comb_img, text_img)
                fname = f"{oid} - {folder}.png"
                out_local = oid_dir / fname
                stacked.save(out_local)

                shutil.copy2(out_local, TOTAL / fname)

            print(f"[OK] {cls} / {oid} -> 13 images")

    print(f"Done.\n  {SEPARATE.relative_to(PROJECT_ROOT)}\n  {TOTAL.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "examples":
        build_examples_figure()
    else:
        main()

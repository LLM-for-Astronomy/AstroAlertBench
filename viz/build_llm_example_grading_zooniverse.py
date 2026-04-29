"""Build human_samples/llm_example_grading_zooniverse/ — five gold OIDs (one per class).

Layout per OID matches ``llm_example_grading``: ``combination/<OID>.png`` plus 13 files
``N_<model_slug>_grading.png`` (UTF-8 grading text rendered as images; no ``.txt``).

``ZOONIVERSE_PICKS`` are chosen from ``manifest_benchmark_final.csv`` so each OID has
a **parseable 5-class Part C** in **all 13** ``RUN_SPECS`` run.jsonl files,
**mixed** correctness (at least one model right and at least one wrong), and
**usable stamp metadata** (core numeric fields not NaN and not the ``-999`` sentinel,
so the combination image is not mostly ``N/A``).

Run from repo root::

    python -m viz.build_llm_example_grading_zooniverse
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

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

# One per class in CLASSES_5; validated in main() when all 13 run.jsonl are present.
ZOONIVERSE_PICKS: list[tuple[str, str]] = [
    ("ZTF19abkdsaw", "AGN"),
    ("ZTF25aaxmsns", "SN"),
    ("ZTF19aayhwvd", "VS"),
    ("ZTF25aahvsli", "bogus"),
    ("ZTF26aargnnp", "asteroid"),
]

BASE_OUT = PROJECT_ROOT / "human_samples" / "llm_example_grading_zooniverse"

# Max width used when choosing font size and text wrapping; output image is trimmed to content.
MAX_CANVAS_W = 900
MIN_CANVAS_W = 280
TEXT_MARGIN = 22
WRAP_WIDTH_CHARS = 100
FONT_SIZE_CANDIDATES = (13, 12, 11)


def _parsed_dict(rec: dict | None) -> dict:
    if not rec:
        return {}
    parsed = rec.get("parsed")
    if not isinstance(parsed, dict) and rec.get("raw_text"):
        from evaluate import extract_json_object

        parsed = extract_json_object(rec.get("raw_text") or "")
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _pred_from_rec(rec: dict | None) -> str | None:
    p = _parsed_dict(rec)
    if not p:
        return None
    return _final_class_from_parsed(p)


def _is_bad_sentinel(val: object) -> bool:
    if pd.isna(val):
        return True
    try:
        if float(val) <= -998.5:
            return True
    except (TypeError, ValueError):
        return False
    return False


def _manifest_usable_for_combination(row: pd.Series) -> bool:
    """Require real numeric metadata for the combination panel (not mostly -999 / NaN)."""
    for col in (
        "magpsf",
        "sigmapsf",
        "fwhm",
        "sgscore1",
        "distpsnr1",
        "classtar",
        "chinr",
        "sharpnr",
    ):
        if _is_bad_sentinel(hb._col(row, col)):
            return False
    ps1_ok = sum(
        1
        for col in ("sgmag1", "srmag1", "simag1", "szmag1")
        if not _is_bad_sentinel(hb._col(row, col))
    )
    return ps1_ok >= 1


def _validate_zooniverse_pick(
    oid: str,
    gold: str,
    store_by_folder: dict[str, dict[str, dict]],
    row: pd.Series | None = None,
) -> None:
    if len(store_by_folder) != 13:
        return
    missing: list[str] = []
    preds: list[str] = []
    for _slug, _jpath, folder in RUN_SPECS:
        store = store_by_folder.get(folder) or {}
        rec = store.get(oid)
        pred = _pred_from_rec(rec)
        if pred is None:
            missing.append(folder)
        else:
            preds.append(pred)
    if missing:
        raise SystemExit(
            f"[FATAL] {oid} ({gold}): no parseable 5-class Part C for: {', '.join(missing)}"
        )
    n_ok = sum(1 for p in preds if p == gold)
    n = len(preds)
    if n_ok == 0:
        raise SystemExit(
            f"[FATAL] {oid} ({gold}): all {n} models wrong — need mixed correctness"
        )
    if n_ok == n:
        raise SystemExit(
            f"[FATAL] {oid} ({gold}): all {n} models correct — need mixed correctness"
        )
    if row is not None and not _manifest_usable_for_combination(row):
        raise SystemExit(
            f"[FATAL] {oid} ({gold}): manifest missing or -999 metadata "
            "(combination panel would be unusable)"
        )


def _grading_text_lines(
    leading: str,
    alt: str,
    pred: str | None,
    correct_class: str,
) -> list[str]:
    return [
        "Leading Interpretation and Support:",
        leading,
        "",
        "Alternative Analysis:",
        alt,
        "",
        f"LLM's Classification: {pred if pred is not None else '(no parseable Part C / pipeline)'}",
        f"Correct Class: {correct_class}",
    ]


def _flatten_wrapped(body: list[str], width: int) -> list[str]:
    out: list[str] = []
    for block in body:
        if block == "":
            out.append("")
            continue
        chunks = textwrap.wrap(
            block,
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
        )
        out.extend(chunks if chunks else [""])
    return out


def _write_grading_png(path: Path, body_lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    draw_tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    font = hb._load_mono_font(FONT_SIZE_CANDIDATES[0])
    flat: list[str] = []
    max_w = MAX_CANVAS_W - 2 * TEXT_MARGIN
    for size in FONT_SIZE_CANDIDATES:
        font = hb._load_mono_font(size)
        flat = _flatten_wrapped(body_lines, WRAP_WIDTH_CHARS)
        if not flat:
            break
        widest = 0
        for ln in flat:
            if not ln:
                continue
            bbox = draw_tmp.textbbox((0, 0), ln, font=font)
            widest = max(widest, bbox[2] - bbox[0])
        if widest <= max_w:
            break

    line_gap = 5
    y = TEXT_MARGIN
    positions: list[tuple[str, int]] = []
    for ln in flat:
        bbox = draw_tmp.textbbox((0, 0), ln or " ", font=font)
        h = bbox[3] - bbox[1]
        positions.append((ln, y))
        y += h + line_gap

    max_line_w = 0
    for ln in flat:
        if ln:
            bbox = draw_tmp.textbbox((0, 0), ln, font=font)
            max_line_w = max(max_line_w, bbox[2] - bbox[0])

    canvas_w = max(MIN_CANVAS_W, min(MAX_CANVAS_W, max_line_w + 2 * TEXT_MARGIN))

    canvas_h = max(TEXT_MARGIN * 2 + 60, y + TEXT_MARGIN)
    img = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for ln, y0 in positions:
        draw.text((TEXT_MARGIN, y0), ln, fill=(0, 0, 0), font=font)

    img.save(path)


def main() -> None:
    df = pd.read_csv(MANIFEST)
    df_oid = {str(r["oid"]): r for _, r in df.iterrows()}
    store_by_folder: dict[str, dict[str, dict]] = {}
    for slug, jpath, folder in RUN_SPECS:
        if not jpath.is_file():
            print(f"[WARN] missing {jpath}, skip model {folder}", file=sys.stderr)
            continue
        store_by_folder[folder] = _load_jsonl_index(jpath)
    if len(store_by_folder) != 13:
        print(
            f"[WARN] only {len(store_by_folder)}/13 run files loaded",
            file=sys.stderr,
        )
    else:
        for oid, tc in ZOONIVERSE_PICKS:
            if oid not in df_oid:
                raise SystemExit(f"[FATAL] {oid}: not in manifest")
            _validate_zooniverse_pick(oid, tc, store_by_folder, df_oid[oid])
        print("[OK] ZOONIVERSE_PICKS validated (13/13 parseable, mixed correctness)", file=sys.stderr)

    BASE_OUT.mkdir(parents=True, exist_ok=True)

    for oid, tc in ZOONIVERSE_PICKS:
        if oid not in df_oid:
            print(f"[SKIP] {oid} not in manifest", file=sys.stderr)
            continue
        row = df_oid[oid]
        if str(row["target_class"]) != tc:
            print(
                f"[SKIP] {oid}: manifest target_class {row['target_class']} != {tc}",
                file=sys.stderr,
            )
            continue

        root = BASE_OUT / oid
        root.mkdir(parents=True, exist_ok=True)

        src_montage = PROJECT_ROOT / STAMPS_LLM_DIRNAME / tc / oid / "montage.png"
        if not src_montage.is_file():
            print(f"[SKIP] missing montage {src_montage}", file=sys.stderr)
            continue

        hb.OUT_ROOT = root
        comb_path = hb.build_combination_image(oid, row, src_montage)
        print(f"[OK] {oid} ({tc}) combination -> {comb_path.relative_to(PROJECT_ROOT)}")

        for i, (_slug, _jpath, folder) in enumerate(RUN_SPECS, start=1):
            store = store_by_folder.get(folder) or {}
            rec = store.get(oid)
            out_png = root / f"{i}_{folder}_grading.png"
            if not rec:
                lines = _grading_text_lines("", "", None, tc)
                _write_grading_png(out_png, lines)
                continue
            parsed = _parsed_dict(rec)
            lead, alt = _part_b_texts(parsed)
            pred = _pred_from_rec(rec)
            lines = _grading_text_lines(lead, alt, pred, tc)
            _write_grading_png(out_png, lines)

    print(f"Done. Output under {BASE_OUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

"""Build human_samples/llm_example_grading/<OID>/ for three benchmark datapoints.

For each OID: combination PNG (montage + metadata, same layout as human_baselines)
and 13 files named ``N_<model_slug>_grading.txt`` (N=1..13) filled from that model's
run.jsonl (Part B leading/alternative + 5-class prediction).

Selected from data/manifest_benchmark_final.csv with ~mixed correctness across
13 models and high Part B self-scores (see human_samples/llm_example_grading/README.md).

Run from repo root::

    python -m viz.build_llm_example_grading
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import viz._make_human_baselines_batch as hb
from evaluate import (
    normalize_stage1,
    normalize_stage2,
    normalize_stage3_label,
    stages_to_final_class,
)

# Must match full-benchmark run.jsonl locations (13 runs). Order 1..13 is the human
# example grading layout: Gemini Pro, Gemini Flash, GPT high/none, Opus think/nothink,
# Kimi, then Qwen 4B / 35B / 397B (think then nothink within each size).
RUN_SPECS: list[tuple[str, Path, str]] = [
    ("gemini25_pro_high", PROJECT_ROOT / "runs/20260424-1809-gemini25-pro-high-benchmark-full/run.jsonl", "gemini25_pro_high"),
    ("gemini25_flash_none", PROJECT_ROOT / "runs/20260423-2110-gemini25-flash-none-benchmark-full/run.jsonl", "gemini25_flash_none"),
    ("gpt54_high", PROJECT_ROOT / "runs/20260421-2024-gpt-5.4-high-benchmark-full/run.jsonl", "gpt54_high"),
    ("gpt54_none", PROJECT_ROOT / "runs/20260421-2032-gpt-5.4-none-benchmark-full/run.jsonl", "gpt54_none"),
    ("opus47_think", PROJECT_ROOT / "runs/20260423-0942-opus47-think-benchmark-full/run.jsonl", "opus47_think"),
    ("opus47_nothink", PROJECT_ROOT / "runs/20260424-2324-opus47-nothink-benchmark-full/run.jsonl", "opus47_nothink"),
    ("kimi_k25", PROJECT_ROOT / "runs/20260420-1226-kimi-k25-benchmark-full/run.jsonl", "kimi_k25"),
    ("qwen35_4b_think", PROJECT_ROOT / "runs/20260420-1920-qwen35-4b-benchmark-full/run.jsonl", "qwen35_4b_think"),
    ("qwen35_4b_nothink", PROJECT_ROOT / "runs/20260421-0002-qwen35-4b-nothink-benchmark-full/run.jsonl", "qwen35_4b_nothink"),
    ("qwen35_35b_think", PROJECT_ROOT / "runs/20260420-2054-qwen35-35b-a3b-benchmark-full/run.jsonl", "qwen35_35b_think"),
    ("qwen35_35b_nothink", PROJECT_ROOT / "runs/20260421-0019-qwen35-35b-a3b-nothink-benchmark-full/run.jsonl", "qwen35_35b_nothink"),
    ("qwen35_397b_think", PROJECT_ROOT / "runs/20260420-1554-qwen35-397b-a17b-benchmark-full/run.jsonl", "qwen35_397b_think"),
    ("qwen35_397b_nothink", PROJECT_ROOT / "runs/20260421-0025-qwen35-397b-a17b-nothink-benchmark-full/run.jsonl", "qwen35_397b_nothink"),
]

# Chosen for: in manifest_benchmark_final; mixed correct/wrong across 13 models; high self-scores.
PICKS: list[tuple[str, str]] = [
    ("ZTF19abfqvbg", "AGN"),
    ("ZTF25abxlcvf", "SN"),
    ("ZTF26aargnnp", "asteroid"),
]

BASE_OUT = PROJECT_ROOT / "human_samples" / "llm_example_grading"
MANIFEST = PROJECT_ROOT / "data" / "manifest_benchmark_final.csv"


def _load_jsonl_index(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            oid = o.get("oid")
            if oid:
                out[str(oid)] = o
    return out


def _final_class_from_parsed(parsed: dict) -> str | None:
    if not isinstance(parsed, dict):
        return None
    pc = parsed.get("Part C") or parsed.get("part_c")
    if not isinstance(pc, dict):
        return None
    s1 = normalize_stage1(pc.get("stage1"))
    s2 = normalize_stage2(pc.get("stage2"))
    s3 = normalize_stage3_label(pc.get("stage3"))
    if s1 is None or s2 is None or s3 is None:
        return None
    return stages_to_final_class(s1, s2, s3)


def _part_b_texts(parsed: dict) -> tuple[str, str]:
    if not isinstance(parsed, dict):
        return "", ""
    pb = parsed.get("Part B") or parsed.get("part_b")
    if not isinstance(pb, dict):
        return "", ""
    lead = pb.get("leading_interpretation_and_support") or ""
    alt = pb.get("alternative_analysis") or ""
    if not isinstance(lead, str):
        lead = str(lead)
    if not isinstance(alt, str):
        alt = str(alt)
    return lead.strip(), alt.strip()


def _write_grading_txt(
    path: Path,
    leading: str,
    alt: str,
    pred: str | None,
    correct_class: str,
) -> None:
    def q(s: str) -> str:
        return json.dumps(s, ensure_ascii=False)

    lines = [
        f'"leading_interpretation_and_support": {q(leading)}',
        f'"alternative_analysis": {q(alt)}',
        f"LLM's Classification: {pred if pred is not None else '(no parseable Part C / pipeline)'}",
        f"Correct Class: {correct_class}",
        "Your Grading: ",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


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

    BASE_OUT.mkdir(parents=True, exist_ok=True)

    for oid, tc in PICKS:
        if oid not in df_oid:
            print(f"[SKIP] {oid} not in manifest", file=sys.stderr)
            continue
        row = df_oid[oid]
        assert str(row["target_class"]) == tc

        root = BASE_OUT / oid
        root.mkdir(parents=True, exist_ok=True)

        src_montage = PROJECT_ROOT / "stamps_llm" / tc / oid / "montage.png"
        if not src_montage.is_file():
            print(f"[SKIP] missing montage {src_montage}", file=sys.stderr)
            continue

        hb.OUT_ROOT = root
        comb_path = hb.build_combination_image(oid, row, src_montage)
        print(f"[OK] {oid} ({tc}) combination -> {comb_path.relative_to(PROJECT_ROOT)}")

        for i, (_slug, _jpath, folder) in enumerate(RUN_SPECS, start=1):
            store = store_by_folder.get(folder) or {}
            rec = store.get(oid)
            out = root / f"{i}_{folder}_grading.txt"
            if not rec:
                _write_grading_txt(out, "", "", None, tc)
                continue
            parsed = rec.get("parsed")
            if not isinstance(parsed, dict) and rec.get("raw_text"):
                from evaluate import extract_json_object

                parsed = extract_json_object(rec.get("raw_text") or "")
            if not isinstance(parsed, dict):
                parsed = {}
            lead, alt = _part_b_texts(parsed)
            pred = _final_class_from_parsed(parsed) if parsed else None
            _write_grading_txt(out, lead, alt, pred, tc)

    print(f"Done. Output under {BASE_OUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

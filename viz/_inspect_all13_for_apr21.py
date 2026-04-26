"""One-shot: dump compact metrics from every benchmark-full run for the
20260421 cross-run report rewrite.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RUNS = [
    ("gpt-5.4-high",        "runs/20260421-2024-gpt-5.4-high-benchmark-full",        "openai"),
    ("gpt-5.4-none",        "runs/20260421-2032-gpt-5.4-none-benchmark-full",        "openai"),
    ("opus47-think",        "runs/20260423-0942-opus47-think-benchmark-full",        "anthropic"),
    ("opus47-nothink",      "runs/20260424-2324-opus47-nothink-benchmark-full",      "anthropic"),
    ("gemini25-pro-high",   "runs/20260424-1809-gemini25-pro-high-benchmark-full",   "google"),
    ("gemini25-flash-none", "runs/20260423-2110-gemini25-flash-none-benchmark-full", "google"),
    ("kimi-k25",            "runs/20260420-1226-kimi-k25-benchmark-full",            "tinker"),
    ("qwen397-think",       "runs/20260420-1554-qwen35-397b-a17b-benchmark-full",    "tinker"),
    ("qwen35b-think",       "runs/20260420-2054-qwen35-35b-a3b-benchmark-full",      "tinker"),
    ("qwen4b-think",        "runs/20260420-1920-qwen35-4b-benchmark-full",           "tinker"),
    ("qwen397-nothink",     "runs/20260421-0025-qwen35-397b-a17b-nothink-benchmark-full", "tinker"),
    ("qwen35b-nothink",     "runs/20260421-0019-qwen35-35b-a3b-nothink-benchmark-full",   "tinker"),
    ("qwen4b-nothink",      "runs/20260421-0002-qwen35-4b-nothink-benchmark-full",        "tinker"),
]


def _mean_field(jsonl: Path, field: str) -> float | None:
    """Mean of a top-level numeric field across run.jsonl rows that have it."""
    if not jsonl.exists():
        return None
    vals: list[float] = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        v = row.get(field)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    return sum(vals) / len(vals) if vals else None


def _split_in_out_tokens(jsonl: Path) -> tuple[float | None, float | None, float | None]:
    """Mean (input_tokens, output_tokens, reasoning_tokens) across rows."""
    if not jsonl.exists():
        return None, None, None
    inp, out, rea = [], [], []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        for src in (row.get("usage") or {}, row):
            if isinstance(src, dict):
                if "input_tokens" in src:
                    inp.append(float(src["input_tokens"]))
                if "output_tokens" in src:
                    out.append(float(src["output_tokens"]))
                if "reasoning_tokens" in src:
                    rea.append(float(src["reasoning_tokens"]))
    f = lambda L: (sum(L) / len(L)) if L else None
    return f(inp), f(out), f(rea)


def main() -> None:
    out: dict[str, dict] = {}
    for slug, folder, backend in RUNS:
        run_dir = PROJECT_ROOT / folder
        m_path = run_dir / "metrics.json"
        if not m_path.exists():
            print(f"SKIP {slug}: no metrics.json", file=sys.stderr)
            continue
        m = json.loads(m_path.read_text(encoding="utf-8"))
        avg_in, avg_out, avg_rea = _split_in_out_tokens(run_dir / "run.jsonl")
        out[slug] = {
            "folder": folder,
            "backend": backend,
            "n_examples": m.get("n_examples"),
            "n_errors": m.get("n_errors"),
            "json_valid_rate": m.get("json_valid_rate"),
            "n_truncated": m.get("n_truncated"),
            "truncated_rate": m.get("truncated_rate"),
            "part_a_macro_accuracy": m.get("part_a_macro_accuracy"),
            "part_a_exact_match_rate": m.get("part_a_exact_match_rate"),
            "part_b_msrs": m.get("part_b_msrs"),
            "part_b_self_pass_rate": m.get("part_b_self_pass_rate"),
            "part_c_n_evaluable": m.get("part_c_n_evaluable"),
            "stage1": m.get("part_c_stage1_accuracy"),
            "stage2": m.get("part_c_stage2_accuracy"),
            "stage3": m.get("part_c_stage3_accuracy"),
            "stage3_cond": m.get("part_c_stage3_conditional_accuracy"),
            "five_class_on_parsed": m.get("part_c_final_5class_accuracy"),
            "stage3_macro_f1": m.get("part_c_stage3_macro_f1"),
            "per_class_acc": m.get("per_class_accuracy"),
            "per_class_total": m.get("per_class_total"),
            "per_class_correct": m.get("per_class_correct"),
            "stage3_per_class_prf": m.get("part_c_stage3_per_class_prf"),
            "stage3_confusion": m.get("part_c_stage3_confusion_matrix"),
            "output_tokens": m.get("output_tokens"),
            "answer_tokens": m.get("answer_tokens"),
            "error_breakdown_format": (m.get("error_breakdown") or {}).get("format"),
            "value_top10": (m.get("error_breakdown") or {}).get("value_top10"),
            "n_with_value_errors": (m.get("error_breakdown") or {}).get("n_with_value_errors"),
            "calibration": m.get("part_bc_confidence_accuracy"),
            "avg_input_tokens": avg_in,
            "avg_output_tokens": avg_out,
            "avg_reasoning_tokens": avg_rea,
        }

    out_path = PROJECT_ROOT / "viz" / "_inspect_all13_for_apr21.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out_path} ({len(out)} runs)")


if __name__ == "__main__":
    main()

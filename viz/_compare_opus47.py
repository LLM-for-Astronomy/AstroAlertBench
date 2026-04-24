"""Pull comparison metrics across prior benchmark-full runs vs Opus 4.7 think."""
from __future__ import annotations

import json
from pathlib import Path

RUNS = {
    "opus47-high":   "runs/20260423-0942-opus47-think-benchmark-full/metrics.json",
    "gpt-5.4-high":  "runs/20260421-2024-gpt-5.4-high-benchmark-full/metrics.json",
    "gpt-5.4-none":  "runs/20260421-2032-gpt-5.4-none-benchmark-full/metrics.json",
    "kimi-k25":      "runs/20260420-1226-kimi-k25-benchmark-full/metrics.json",
    "qwen35-397b":   "runs/20260420-1554-qwen35-397b-a17b-benchmark-full/metrics.json",
    "qwen35-35b":    "runs/20260420-2054-qwen35-35b-a3b-benchmark-full/metrics.json",
    "qwen35-4b":     "runs/20260420-1920-qwen35-4b-benchmark-full/metrics.json",
}

header = f"{'run':20s}  {'5class':>7s}  {'parse':>6s}  {'trunc':>6s}  {'msrs':>5s}  {'AGN':>6s}  {'SN':>6s}  {'VS':>6s}  {'ast':>6s}  {'bog':>6s}  {'calgap':>7s}  {'r':>6s}  {'out_mean':>8s}  {'out_p95':>7s}"
print(header)
print("-" * len(header))
for name, path in RUNS.items():
    p = Path(path)
    if not p.is_file():
        print(f"{name:20s}  (missing metrics.json at {path})")
        continue
    m = json.load(open(p, encoding="utf-8"))
    pca = m["per_class_accuracy"]
    cal = m["part_bc_confidence_accuracy"]
    ot = m["output_tokens"]
    print(
        f"{name:20s}  "
        f"{m['part_c_final_5class_accuracy']:7.4f}  "
        f"{m['json_valid_rate']:6.4f}  "
        f"{m.get('truncated_rate', 0.0):6.4f}  "
        f"{m['part_b_msrs']:5.2f}  "
        f"{pca['AGN']:6.4f}  "
        f"{pca['SN']:6.4f}  "
        f"{pca['VS']:6.4f}  "
        f"{pca['asteroid']:6.4f}  "
        f"{pca['bogus']:6.4f}  "
        f"{cal['calibration_gap']:+7.4f}  "
        f"{cal['pearson_r']:+6.3f}  "
        f"{ot['mean']:8.1f}  "
        f"{ot['p95']:7.0f}"
    )

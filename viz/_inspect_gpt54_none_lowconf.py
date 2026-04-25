"""One-shot: inspect the 36 low-confidence (self-mean < 4) predictions in the
GPT-5.4 none full-benchmark run.

For each such row report:
  - target class breakdown (gold)
  - predicted 5-class breakdown
  - confusion table (gold x pred) restricted to the low-conf bin
  - histogram of self_mean values in the low-conf bin
  - per-class accuracy on the low-conf bin
Compare to the same model's overall class distribution as a sanity check.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluate import (  # noqa: E402
    GOLD_STAGES,
    extract_json_object,
    extract_self_scores,
    normalize_stage1,
    normalize_stage2,
    normalize_stage3_label,
    stages_to_final_class,
)

RUN_FOLDER = PROJECT_ROOT / "runs" / "20260421-2032-gpt-5.4-none-benchmark-full"
JSONL = RUN_FOLDER / "run.jsonl"

CLASSES = ["bogus", "asteroid", "SN", "VS", "AGN"]


def main() -> None:
    overall_gold: Counter[str] = Counter()
    overall_pred: Counter[str] = Counter()
    low_gold: Counter[str] = Counter()
    low_pred: Counter[str] = Counter()
    low_conf_means: list[float] = []
    low_rows: list[dict] = []
    confusion: dict[str, Counter[str]] = {c: Counter() for c in CLASSES}
    per_class_low_correct: Counter[str] = Counter()
    per_class_low_total: Counter[str] = Counter()

    n_total = 0
    n_linked = 0
    n_low_linked = 0

    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            n_total += 1
            if r.get("error"):
                continue
            tc = r.get("target_class")
            if tc is None:
                continue
            parsed = r.get("parsed") or extract_json_object(r.get("answer_text") or r.get("raw_text") or "")
            if not isinstance(parsed, dict):
                continue
            part_b = parsed.get("Part B") or parsed.get("part_b")
            part_c = parsed.get("Part C") or parsed.get("part_c")
            if not isinstance(part_b, dict) or not isinstance(part_c, dict):
                continue
            scores = extract_self_scores(part_b)
            if not all(s is not None for s in scores):
                continue
            self_mean = float(np.mean(scores))
            ps1 = normalize_stage1(part_c.get("stage1"))
            ps2 = normalize_stage2(part_c.get("stage2"))
            ps3 = normalize_stage3_label(part_c.get("stage3"))
            if ps1 is None or ps2 is None or ps3 is None:
                continue
            pred_final = stages_to_final_class(ps1, ps2, ps3)
            if pred_final is None:
                continue

            n_linked += 1
            tc_str = str(tc)
            overall_gold[tc_str] += 1
            overall_pred[pred_final] += 1

            if self_mean < 4.0:
                n_low_linked += 1
                low_gold[tc_str] += 1
                low_pred[pred_final] += 1
                low_conf_means.append(self_mean)
                if tc_str in confusion:
                    confusion[tc_str][pred_final] += 1
                per_class_low_total[tc_str] += 1
                if pred_final == tc_str:
                    per_class_low_correct[tc_str] += 1
                low_rows.append({
                    "oid": r.get("oid"),
                    "gold": tc_str,
                    "pred": pred_final,
                    "self_scores": scores,
                    "self_mean": round(self_mean, 3),
                    "correct": pred_final == tc_str,
                })

    print(f"Run folder       : {RUN_FOLDER.name}")
    print(f"Total JSONL rows : {n_total}")
    print(f"Linked (parsed B+C): {n_linked}")
    print(f"Low-conf (<4)    : {n_low_linked}")
    print()

    print("=" * 70)
    print("Self-mean distribution in the low-conf bin (3 self-scores 1..5):")
    print("=" * 70)
    bin_counter = Counter(round(m, 3) for m in low_conf_means)
    for m, c in sorted(bin_counter.items()):
        print(f"  self_mean = {m:>5}   n = {c:>3}")
    print()

    print("=" * 70)
    print("Class distribution: low-conf bin vs all-linked")
    print("=" * 70)
    print(f"{'class':<14}  {'low-bin':>8}  {'low-bin %':>10}  "
          f"{'linked':>8}  {'linked %':>9}  {'low rate':>9}")
    for c in CLASSES:
        n_low = low_gold.get(c, 0)
        n_all = overall_gold.get(c, 0)
        low_pct = (100 * n_low / n_low_linked) if n_low_linked else 0.0
        all_pct = (100 * n_all / n_linked) if n_linked else 0.0
        # P(self_mean < 4 | class = c): how often does the model self-flag this class?
        low_rate = (100 * n_low / n_all) if n_all else 0.0
        print(f"{c:<14}  {n_low:>8}  {low_pct:>9.2f}%  {n_all:>8}  {all_pct:>8.2f}%  {low_rate:>8.2f}%")
    print(f"{'TOTAL':<14}  {n_low_linked:>8}  {100.0:>9.2f}%  {n_linked:>8}  {100.0:>8.2f}%")
    print()

    print("=" * 70)
    print("Per-class accuracy on the low-conf bin (gold class -> correct?):")
    print("=" * 70)
    print(f"{'class':<14}  {'n_low':>5}  {'correct':>7}  {'acc':>6}")
    for c in CLASSES:
        n_low = per_class_low_total.get(c, 0)
        cor = per_class_low_correct.get(c, 0)
        acc = (100 * cor / n_low) if n_low else float("nan")
        acc_s = f"{acc:>5.1f}%" if n_low else "  n/a"
        print(f"{c:<14}  {n_low:>5}  {cor:>7}  {acc_s:>6}")
    print()

    print("=" * 70)
    print("Confusion within the low-conf bin (rows: gold, cols: pred):")
    print("=" * 70)
    header = "gold \\ pred  " + "  ".join(f"{c[:8]:>8}" for c in CLASSES) + "    total"
    print(header)
    for g in CLASSES:
        row = confusion[g]
        cells = "  ".join(f"{row.get(p, 0):>8}" for p in CLASSES)
        total = sum(row.values())
        print(f"{g:<12}  {cells}  {total:>8}")
    print()

    print("=" * 70)
    print("All low-conf rows (gold, pred, scores, mean, correct):")
    print("=" * 70)
    print(f"{'oid':<14}  {'gold':<14}  {'pred':<14}  {'scores':<11}  {'mean':>5}  ok?")
    for row in sorted(low_rows, key=lambda r: (r["gold"], r["self_mean"])):
        scores_s = "/".join(str(s) for s in row["self_scores"])
        mark = "Y" if row["correct"] else "."
        print(f"{row['oid']:<14}  {row['gold']:<14}  {row['pred']:<14}  "
              f"{scores_s:<11}  {row['self_mean']:>5.2f}  {mark}")


if __name__ == "__main__":
    main()

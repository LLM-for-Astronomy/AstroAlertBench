"""Build a balanced n=300 subsample of manifest_benchmark_final.csv.

60 alerts per class (AGN / SN / VS / asteroid / bogus), sampled with a fixed
seed so every model in the class-probability calibration experiment sees the
same alerts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ["AGN", "SN", "VS", "asteroid", "bogus"]
DEFAULT_SEED = 20260725
DEFAULT_PER_CLASS = 60


def build(
    src: Path,
    out: Path,
    per_class: int = DEFAULT_PER_CLASS,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    df = pd.read_csv(src, low_memory=False)
    if "target_class" not in df.columns:
        raise SystemExit(f"{src} missing target_class")
    parts = []
    for cls in CLASSES:
        sub = df[df["target_class"] == cls]
        if len(sub) < per_class:
            raise SystemExit(
                f"class {cls}: only {len(sub)} rows, need {per_class}"
            )
        parts.append(sub.sample(n=per_class, random_state=seed))
    out_df = pd.concat(parts, ignore_index=True)
    # Stable order: class blocks then oid, so JSONL walk is deterministic.
    out_df = out_df.sort_values(["target_class", "oid"]).reset_index(drop=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out, index=False)

    summary = {
        "source": str(src.as_posix()),
        "out": str(out.as_posix()),
        "seed": seed,
        "n_total": int(len(out_df)),
        "per_class": per_class,
        "class_counts": out_df["target_class"].value_counts().to_dict(),
        "oids": out_df["oid"].tolist(),
    }
    summary_path = out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out}  n={len(out_df)}")
    print(out_df["target_class"].value_counts().to_string())
    print(f"Summary: {summary_path}")
    return out_df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--src",
        type=Path,
        default=ROOT / "data" / "manifest_benchmark_final.csv",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT
        / "data_class_probability_calibration"
        / "manifest_class_prob_300.csv",
    )
    ap.add_argument("--per-class", type=int, default=DEFAULT_PER_CLASS)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()
    build(args.src, args.out, per_class=args.per_class, seed=args.seed)


if __name__ == "__main__":
    main()

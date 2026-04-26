"""Build stratified n=35 low-confidence subsamples + prior JSON for each model.

Writes under ``data_second_roll_out_ablation/``:

  metadata/<slug>_n35.csv   — rows from ``data/manifest_benchmark_final.csv`` plus
                            ``ablation_prior_file`` column
  priors/<slug>/<oid>.json  — first-pass record (+ meta) for prompting
  ablation_summary.json     — pool sizes, allocations, chosen OIDs per model

Usage::

    python -m viz.build_second_rollout_ablation \\
        --manifest data/manifest_benchmark_final.csv \\
        --out-root data_second_roll_out_ablation \\
        --n 35 --random-seed 42

Requires the five full-benchmark JSONLs listed in ``MODELS`` to exist under
``results/``.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluate import (  # noqa: E402
    extract_json_object,
    extract_self_scores,
    normalize_stage1,
    normalize_stage2,
    normalize_stage3_label,
    stages_to_final_class,
)

CLASSES = ("SN", "VS", "AGN", "bogus", "asteroid")

MODELS: list[dict[str, str]] = [
    {"slug": "gpt54_high", "jsonl": "results/benchmark_gpt54_high.jsonl"},
    {"slug": "gpt54_none", "jsonl": "results/benchmark_gpt54_none.jsonl"},
    {"slug": "gemini25_flash_none", "jsonl": "results/benchmark_gemini25_flash_none.jsonl"},
    {"slug": "opus47_think", "jsonl": "results/benchmark_opus47_think.jsonl"},
    {"slug": "opus47_nothink", "jsonl": "results/benchmark_opus47_nothink.jsonl"},
]


def _load_jsonl(path: Path) -> dict[str, dict]:
    by_oid: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        oid = rec.get("oid")
        if oid:
            by_oid[str(oid)] = rec
    return by_oid


def _parsed_self_mean(parsed: dict | None) -> float | None:
    if not isinstance(parsed, dict):
        return None
    part_b = parsed.get("Part B") or parsed.get("part_b")
    if not isinstance(part_b, dict):
        return None
    scores = extract_self_scores(part_b)
    if len(scores) != 3 or any(s is None for s in scores):
        return None
    return float(sum(scores)) / 3.0


def _partc_evaluable(parsed: dict | None) -> bool:
    if not isinstance(parsed, dict):
        return False
    part_c = parsed.get("Part C") or parsed.get("part_c")
    if not isinstance(part_c, dict):
        return False
    ps1 = normalize_stage1(part_c.get("stage1"))
    ps2 = normalize_stage2(part_c.get("stage2"))
    ps3 = normalize_stage3_label(part_c.get("stage3"))
    if ps1 is None or ps2 is None or ps3 is None:
        return False
    return stages_to_final_class(ps1, ps2, ps3) is not None


def _first_pass_correct(parsed: dict | None, gold_tc: str) -> bool | None:
    if not isinstance(parsed, dict):
        return None
    part_c = parsed.get("Part C") or parsed.get("part_c")
    if not isinstance(part_c, dict):
        return None
    ps1 = normalize_stage1(part_c.get("stage1"))
    ps2 = normalize_stage2(part_c.get("stage2"))
    ps3 = normalize_stage3_label(part_c.get("stage3"))
    if ps1 is None or ps2 is None or ps3 is None:
        return None
    pred = stages_to_final_class(ps1, ps2, ps3)
    if pred is None:
        return None
    return pred == str(gold_tc)


def _allocate_stratified(class_counts: dict[str, int], n: int) -> dict[str, int]:
    """Hamilton largest-remainder: integer quotas summing to ``n``."""
    total = sum(class_counts.values())
    if total == 0:
        raise ValueError("empty pool")
    raw: list[tuple[str, int, float]] = []
    rem_sum = 0
    for c in CLASSES:
        nc = class_counts.get(c, 0)
        exact = nc * n / total
        fl = int(exact // 1)
        rem = exact - fl
        raw.append((c, fl, rem))
        rem_sum += fl
    deficit = n - rem_sum
    raw.sort(key=lambda t: t[2], reverse=True)
    quotas = {t[0]: t[1] for t in raw}
    for i in range(deficit):
        quotas[raw[i % len(raw)][0]] += 1
    return quotas


def _build_pool(by_oid: dict[str, dict], manifest: pd.DataFrame) -> list[dict]:
    pool: list[dict] = []
    for _, row in manifest.iterrows():
        oid = str(row["oid"])
        tc = str(row["target_class"])
        rec = by_oid.get(oid)
        if not rec or rec.get("error"):
            continue
        raw = rec.get("answer_text") or rec.get("raw_text") or ""
        parsed = rec.get("parsed")
        if parsed is None and raw:
            parsed = extract_json_object(raw)
        sm = _parsed_self_mean(parsed)
        if sm is None or sm >= 4.0:
            continue
        if not _partc_evaluable(parsed):
            continue
        ok = _first_pass_correct(parsed, tc)
        if ok is None:
            continue
        pool.append(
            {
                "oid": oid,
                "target_class": tc,
                "self_mean": sm,
                "first_correct": bool(ok),
                "record": rec,
                "parsed": parsed,
            }
        )
    return pool


def _pick_stratified(pool: list[dict], quotas: dict[str, int], rng: random.Random) -> list[dict]:
    by_class: dict[str, list[dict]] = defaultdict(list)
    for p in pool:
        by_class[p["target_class"]].append(p)
    for c in CLASSES:
        rng.shuffle(by_class[c])
    chosen: list[dict] = []
    for c in CLASSES:
        need = quotas.get(c, 0)
        avail = by_class[c]
        if len(avail) < need:
            raise ValueError(
                f"Not enough low-confidence rows in class {c!r}: need {need}, have {len(avail)}"
            )
        chosen.extend(avail[:need])
    rng.shuffle(chosen)
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "data" / "manifest_benchmark_final.csv")
    ap.add_argument("--out-root", type=Path, default=PROJECT_ROOT / "data_second_roll_out_ablation")
    ap.add_argument("--n", type=int, default=35, help="Subsample size per model (default 35)")
    ap.add_argument("--random-seed", type=int, default=42)
    args = ap.parse_args()

    manifest = pd.read_csv(args.manifest, low_memory=False)
    rng = random.Random(args.random_seed)

    meta_dir = args.out_root / "metadata"
    pri_root = args.out_root / "priors"
    meta_dir.mkdir(parents=True, exist_ok=True)
    pri_root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {"models": {}, "n": args.n, "random_seed": args.random_seed}

    for spec in MODELS:
        slug = spec["slug"]
        jpath = PROJECT_ROOT / spec["jsonl"]
        if not jpath.is_file():
            print(f"SKIP {slug}: missing {jpath}", file=sys.stderr)
            continue

        by_oid = _load_jsonl(jpath)
        pool = _build_pool(by_oid, manifest)
        if len(pool) < args.n:
            raise SystemExit(
                f"{slug}: low-confidence pool has only {len(pool)} rows (< {args.n}). "
                "Cannot build stratified sample."
            )

        class_counts = Counter(p["target_class"] for p in pool)
        quotas = _allocate_stratified(dict(class_counts), args.n)
        picked = _pick_stratified(pool, quotas, rng)
        oids = [p["oid"] for p in picked]

        pri_dir = pri_root / slug
        pri_dir.mkdir(parents=True, exist_ok=True)

        rel_prefix = str(args.out_root.relative_to(PROJECT_ROOT)).replace("\\", "/")

        rows_out = []
        for p in picked:
            oid = p["oid"]
            prior_path = pri_dir / f"{oid}.json"
            rel = f"{rel_prefix}/priors/{slug}/{oid}.json"
            payload = {
                "oid": oid,
                "model_slug": slug,
                "source_jsonl": spec["jsonl"],
                "first_pass": p["record"],
            }
            prior_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

            mrow = manifest[manifest["oid"] == oid].iloc[0].to_dict()
            mrow["ablation_prior_file"] = rel
            rows_out.append(mrow)

        df_out = pd.DataFrame(rows_out)
        csv_path = meta_dir / f"{slug}_n{args.n}.csv"
        df_out.to_csv(csv_path, index=False)

        summary["models"][slug] = {
            "jsonl": spec["jsonl"],
            "low_conf_pool_size": len(pool),
            "low_conf_class_counts": dict(class_counts),
            "quotas_n35": quotas,
            "chosen_oids": oids,
            "manifest_csv": str(csv_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        }
        print(f"Wrote {csv_path} ({len(df_out)} rows) + {len(oids)} priors under {pri_dir}")

    (args.out_root / "ablation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {args.out_root / 'ablation_summary.json'}")


if __name__ == "__main__":
    main()

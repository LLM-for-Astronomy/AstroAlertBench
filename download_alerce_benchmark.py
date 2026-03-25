"""
Download ALeRCE stamp_classifier benchmark: 500 objects per class (highest probability),
metadata + 3 stamp FITS (science, template, difference).

If stamp download fails for an OID (e.g. API returns JSON instead of FITS), that OID is
skipped and the next-highest-probability candidate from the same class is used, until
500 successes per class. OIDs are unique across the whole dataset (no duplicate objects).

Explorer-equivalent filters: stamp_classifier, class, probability >= MIN_PROB, sort prob DESC.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import pandas as pd
from astropy.io.fits.verify import VerifyWarning
from alerce.core import Alerce

warnings.filterwarnings("ignore", category=VerifyWarning)

# --- config ---
OUT = Path(__file__).resolve().parent
DATA = OUT / "data"
STAMPS = OUT / "stamps"

CLASSES = ["SN", "AGN", "VS", "asteroid", "bogus"]
SURVEY = "ztf"
CLASSIFIER = "stamp_classifier"
SAMPLES_PER_CLASS = 500
MIN_PROBABILITY = 0.8
PAGE_SIZE = 500
MAX_POOL_PAGES = 8  # up to 4000 ranked candidates per class for replacements
RETRIES = 8
SAVE_LOCK = None  # unused; kept for compatibility if extended


def _with_retry(fn, *args, **kwargs):
    last = None
    for attempt in range(RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last = e
            time.sleep(2.0 * (attempt + 1))
    raise last


def pick_candid_candidates(alerce: Alerce, oid: str) -> list[int]:
    d = _with_retry(alerce.query_detections, oid, survey=SURVEY, format="pandas")
    if d is None or len(d) == 0:
        return []
    d = d.sort_values("mjd", ascending=True)
    stamped = d[d["has_stamp"] == True]  # noqa: E712
    if len(stamped) == 0:
        return [int(d["candid"].iloc[0])]
    return [int(x) for x in stamped["candid"].tolist()[:8]]


def _cleanup_partial_stamps(dest: Path) -> None:
    names = ["science.fits", "template.fits", "difference.fits"]
    paths = [dest / n for n in names]
    present = [p.exists() and p.stat().st_size > 0 for p in paths]
    if any(present) and not all(present):
        for p in paths:
            if p.exists():
                p.unlink()


def stamps_complete(dest: Path) -> bool:
    return all((dest / f"{n}.fits").exists() and (dest / f"{n}.fits").stat().st_size > 0 for n in ["science", "template", "difference"])


def save_stamps(alerce: Alerce, oid: str, candids: list[int], dest_dir: Path) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    names = ["science", "template", "difference"]
    paths = [dest_dir / f"{n}.fits" for n in names]
    if all(p.exists() and p.stat().st_size > 0 for p in paths):
        return candids[0]

    last: Exception | None = None
    for candid in candids:
        _cleanup_partial_stamps(dest_dir)
        try:
            hdul = _with_retry(alerce.get_stamps, oid, candid=candid, survey=SURVEY, format="HDUList")
            for i, name in enumerate(names):
                hdul[i].writeto(paths[i], overwrite=True)
            return candid
        except Exception as e:
            last = e
            continue
    assert last is not None
    raise last


def fetch_ranked_pool(alerce: Alerce, class_name: str) -> pd.DataFrame:
    """Multiple pages of query_objects, probability DESC (same ranking as Explorer)."""
    parts: list[pd.DataFrame] = []
    for page in range(1, MAX_POOL_PAGES + 1):
        df = alerce.query_objects(
            survey=SURVEY,
            classifier=CLASSIFIER,
            class_name=class_name,
            order_by="probability",
            order_mode="DESC",
            page=page,
            page_size=PAGE_SIZE,
            probability=MIN_PROBABILITY,
            format="pandas",
        )
        if df is None or len(df) == 0:
            break
        parts.append(df)
        if len(df) < PAGE_SIZE:
            break
    if not parts:
        raise RuntimeError(f"No objects returned for class {class_name}")
    pool = pd.concat(parts, ignore_index=True)
    pool = pool.drop_duplicates(subset=["oid"], keep="first")
    pool = pool.sort_values("probability", ascending=False).reset_index(drop=True)
    return pool


def fill_class(
    alerce: Alerce,
    class_name: str,
    pool: pd.DataFrame,
    used_oids: set[str],
) -> tuple[pd.DataFrame, list[str]]:
    """
    Walk pool by descending probability. Skip OIDs already used elsewhere.
    Stop at SAMPLES_PER_CLASS successful stamp sets (reuse existing files if present).
    Returns (dataframe of accepted rows, list of skip reasons for logging).
    """
    rows: list[dict] = []
    skips: list[str] = []

    for _, row in pool.iterrows():
        oid = str(row["oid"])
        if oid in used_oids:
            continue

        dest = STAMPS / class_name / oid

        if stamps_complete(dest):
            used_oids.add(oid)
            r = row.to_dict()
            r["target_class"] = class_name
            if "candid_used" not in r:
                r["candid_used"] = pd.NA
            r["stamp_dir"] = str(dest)
            r["stamp_error"] = ""
            rows.append(r)
            print(f"  reuse {oid} p={row['probability']:.6f}")
            if len(rows) >= SAMPLES_PER_CLASS:
                break
            continue

        try:
            candids = pick_candid_candidates(alerce, oid)
            if not candids:
                skips.append(f"{oid}: no detections")
                continue
            candid = save_stamps(alerce, oid, candids, dest)
            used_oids.add(oid)
            r = row.to_dict()
            r["target_class"] = class_name
            r["candid_used"] = candid
            r["stamp_dir"] = str(dest)
            r["stamp_error"] = ""
            rows.append(r)
            print(f"  ok {oid} p={row['probability']:.6f} candid={candid}")
            time.sleep(0.06)
        except Exception as e:
            _cleanup_partial_stamps(dest)
            skips.append(f"{oid}: {e}")
            print(f"  skip {oid} p={row['probability']:.6f}: {e}", file=sys.stderr)

        if len(rows) >= SAMPLES_PER_CLASS:
            break

    return pd.DataFrame(rows), skips


def build_summary(final_df: pd.DataFrame) -> dict:
    summary: dict = {"classes": {}, "classifier": CLASSIFIER, "min_probability_floor": MIN_PROBABILITY}
    for cname in CLASSES:
        sub = final_df[final_df["target_class"] == cname]
        if len(sub) == 0:
            summary["classes"][cname] = {"count": 0}
            continue
        summary["classes"][cname] = {
            "count": len(sub),
            "min_probability_among_selected": float(sub["probability"].min()),
            "max_probability_among_selected": float(sub["probability"].max()),
        }
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--rebuild",
        action="store_true",
        help="Refetch ranked pools and rebuild manifest (recommended after stamp failures).",
    )
    args = p.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    STAMPS.mkdir(parents=True, exist_ok=True)

    manifest_path = DATA / "manifest.csv"
    summary_path = DATA / "summary.json"
    skips_path = DATA / "replacement_skips.log"

    alerce = Alerce()

    if not args.rebuild and manifest_path.exists():
        print("Manifest exists; use --rebuild to refetch pools and fill 500/class with replacements.")
        print(f"Or delete {manifest_path} first.")
        return

    print("Fetching ranked pools and filling 500 stamps per class (with replacement on failure)...")
    used_oids: set[str] = set()
    all_parts: list[pd.DataFrame] = []
    all_skips: list[str] = []

    for cname in CLASSES:
        print(f"\n=== {cname} ===")
        pool = fetch_ranked_pool(alerce, cname)
        print(f"pool size: {len(pool)} (pages up to {MAX_POOL_PAGES}, page_size {PAGE_SIZE})")
        df_c, skips = fill_class(alerce, cname, pool, used_oids)
        all_skips.extend([f"[{cname}] {s}" for s in skips])
        if len(df_c) < SAMPLES_PER_CLASS:
            print(
                f"ERROR: only {len(df_c)}/{SAMPLES_PER_CLASS} for {cname}; "
                "increase MAX_POOL_PAGES or lower MIN_PROBABILITY.",
                file=sys.stderr,
            )
        all_parts.append(df_c)

    final_df = pd.concat(all_parts, ignore_index=True)
    summary = build_summary(final_df)

    final_df.to_csv(manifest_path, index=False)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(skips_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_skips))

    print(f"\nWrote {manifest_path} ({len(final_df)} rows)")
    print(f"Wrote {summary_path}")
    print(f"Wrote {skips_path} ({len(all_skips)} skipped attempts)")


if __name__ == "__main__":
    main()

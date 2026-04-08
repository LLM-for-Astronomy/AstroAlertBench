"""
Replace manifest rows that are missing PS1 cross-match fields
(objectidps1, sgmag1, srmag1, simag1, szmag1) with new objects from ALeRCE
whose AVRO data actually contains those fields.

For each replacement:
  1. Fetch ranked candidates from ALeRCE (probability DESC), skipping OIDs
     already in the manifest.
  2. For each candidate, fetch AVRO and verify PS1 fields are present and not
     all -999 (sentinel for "no match").
  3. Download 3 FITS stamps (science, template, difference).
  4. Build montage PNG (Science | Template | Image).
  5. Enrich metadata from AVRO (same fields as enrich_manifest_alerce.py).

Writes updated manifest to --out (default: data/manifest_enriched.csv).

Example:
  python replace_missing_ps1.py --manifest data/manifest_enriched.csv
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import fastavro
import numpy as np
import pandas as pd
from alerce.core import Alerce

from download_alerce_benchmark import (
    CLASSIFIER,
    MIN_PROBABILITY,
    PAGE_SIZE,
    STAMPS,
    SURVEY,
    _with_retry,
    pick_candid_candidates,
    save_stamps,
    stamps_complete,
)
from build_stamps_llm_montages import FITS_NAMES, build_montage, _font

ROOT = Path(__file__).resolve().parent
STAMPS_LLM = ROOT / "stamps_llm"
FID_TO_BAND = {1: "g", 2: "r", 3: "i"}
PS1_REQUIRED = ["objectidps1", "sgmag1", "srmag1", "simag1", "szmag1"]
MAX_POOL_PAGES = 12


def _parse_avro_candidate(raw_bytes: bytes) -> dict | None:
    """Parse AVRO bytes into candidate dict; returns None on failure."""
    try:
        rec = next(fastavro.reader(io.BytesIO(raw_bytes)))
        return rec.get("candidate") or {}
    except Exception:
        return None


def _has_ps1(cand: dict) -> bool:
    """Check that all required PS1 fields are present and not sentinel -999."""
    for col in PS1_REQUIRED:
        val = cand.get(col)
        if val is None:
            return False
        if isinstance(val, (int, float)) and val == -999.0:
            return False
    return True


def _enrich_from_candidate(cand: dict, candid: int) -> dict:
    """Extract the same enrichment fields as enrich_manifest_alerce.py."""
    fid = cand.get("fid")
    fid_band = None
    if fid is not None and not (isinstance(fid, float) and pd.isna(fid)):
        try:
            fid_band = FID_TO_BAND.get(int(fid), str(int(fid)))
        except (TypeError, ValueError):
            fid_band = str(fid)

    return {
        "candid_used": candid,
        "fid": fid,
        "fid_band": fid_band,
        "magpsf": cand.get("magpsf"),
        "sigmapsf": cand.get("sigmapsf"),
        "sgscore1": cand.get("sgscore1"),
        "sgscore2": cand.get("sgscore2"),
        "sgscore3": cand.get("sgscore3"),
        "distpsnr1": cand.get("distpsnr1"),
        "distpsnr2": cand.get("distpsnr2"),
        "distpsnr3": cand.get("distpsnr3"),
        "classtar": cand.get("classtar"),
        "fwhm": cand.get("fwhm"),
        "isdiffpos": cand.get("isdiffpos"),
        "alert_ndethist": cand.get("ndethist"),
        "alert_ncovhist": cand.get("ncovhist"),
        "chinr": cand.get("chinr"),
        "sharpnr": cand.get("sharpnr"),
        "objectidps1": cand.get("objectidps1"),
        "sgmag1": cand.get("sgmag1"),
        "srmag1": cand.get("srmag1"),
        "simag1": cand.get("simag1"),
        "szmag1": cand.get("szmag1"),
        "nmtchps": cand.get("nmtchps"),
    }


def fetch_pool(alerce: Alerce, class_name: str, exclude_oids: set[str]) -> pd.DataFrame:
    """Fetch ranked pool for a class, excluding already-used OIDs."""
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
        return pd.DataFrame()
    pool = pd.concat(parts, ignore_index=True)
    pool = pool.drop_duplicates(subset=["oid"], keep="first")
    pool = pool[~pool["oid"].isin(exclude_oids)]
    pool = pool.sort_values("probability", ascending=False).reset_index(drop=True)
    return pool


def try_replacement(
    alerce: Alerce,
    oid_candidate: str,
    class_name: str,
    font,
) -> dict | None:
    """
    Try one candidate OID: fetch AVRO, check PS1, download stamps, build montage.
    Returns enriched row dict on success, None on failure.
    """
    try:
        candids = pick_candid_candidates(alerce, oid_candidate)
        if not candids:
            return None

        # Check AVRO for PS1 fields using the first available candid
        cand_dict = None
        used_candid = None
        for candid in candids:
            raw = _with_retry(alerce.get_avro, oid_candidate, candid=candid, survey=SURVEY)
            cand_dict = _parse_avro_candidate(raw)
            if cand_dict is not None and _has_ps1(cand_dict):
                used_candid = candid
                break
            cand_dict = None

        if cand_dict is None or used_candid is None:
            return None

        # Download FITS stamps
        dest = STAMPS / class_name / oid_candidate
        actual_candid = save_stamps(alerce, oid_candidate, [used_candid] + candids, dest)

        # Build montage
        fits_paths = [dest / fn for fn in FITS_NAMES]
        if not all(p.is_file() for p in fits_paths):
            return None
        montage = build_montage(fits_paths, font)
        montage_dir = STAMPS_LLM / class_name / oid_candidate
        montage_dir.mkdir(parents=True, exist_ok=True)
        montage.save(montage_dir / "montage.png", format="PNG", optimize=True)

        enriched = _enrich_from_candidate(cand_dict, used_candid)
        enriched["stamp_dir"] = str(dest)
        enriched["stamp_error"] = ""
        return enriched

    except Exception as e:
        print(f"    FAIL {oid_candidate}: {e}", file=sys.stderr)
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Replace manifest rows missing PS1 fields")
    ap.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifest_enriched.csv")
    ap.add_argument("--out", type=Path, default=None, help="Output path (default: overwrite --manifest)")
    ap.add_argument("--sleep", type=float, default=0.15, help="Delay between API calls")
    ap.add_argument("--dry-run", action="store_true", help="Only report what would be replaced")
    args = ap.parse_args()

    out_path = args.out or args.manifest

    df = pd.read_csv(args.manifest, low_memory=False)
    missing_mask = df[PS1_REQUIRED].isna().any(axis=1)
    n_missing = missing_mask.sum()

    print(f"Total rows: {len(df)}")
    print(f"Rows missing PS1: {n_missing}")
    if n_missing == 0:
        print("Nothing to replace.")
        return

    per_class = df[missing_mask].groupby("target_class").size()
    print("Missing per class:")
    for cls, count in per_class.items():
        print(f"  {cls}: {count}")

    if args.dry_run:
        print("(dry run — exiting)")
        return

    alerce = Alerce()
    font = _font()
    all_oids = set(df["oid"].astype(str))

    replacements_log: list[str] = []

    for cls in sorted(per_class.index):
        n_needed = int(per_class[cls])
        cls_missing_idx = df.index[missing_mask & (df["target_class"] == cls)]
        print(f"\n=== {cls}: need {n_needed} replacements ===")

        # Current min probability in the class (replacement threshold)
        cls_existing = df[df["target_class"] == cls]
        min_prob = cls_existing["probability"].min()
        print(f"  Current min probability: {min_prob:.6f}")

        pool = fetch_pool(alerce, cls, all_oids)
        print(f"  Pool size (new candidates): {len(pool)}")

        replaced = 0
        for _, pool_row in pool.iterrows():
            if replaced >= n_needed:
                break

            candidate_oid = str(pool_row["oid"])
            candidate_prob = pool_row["probability"]

            print(f"  Trying {candidate_oid} (prob={candidate_prob:.6f})...")
            result = try_replacement(alerce, candidate_oid, cls, font)

            if result is None:
                time.sleep(args.sleep)
                continue

            # Find the next missing-row index to replace
            replace_idx = cls_missing_idx[replaced]
            old_oid = df.at[replace_idx, "oid"]

            # Copy pool_row's object-level columns, then overlay enrichment
            new_row = pool_row.to_dict()
            new_row["target_class"] = cls
            new_row.update(result)

            # Overwrite the row in the dataframe
            for col, val in new_row.items():
                if col in df.columns:
                    df.at[replace_idx, col] = val
                else:
                    df[col] = np.nan
                    df.at[replace_idx, col] = val

            df.at[replace_idx, "oid"] = candidate_oid
            all_oids.add(candidate_oid)

            replaced += 1
            replacements_log.append(f"{cls}: {old_oid} -> {candidate_oid} (prob={candidate_prob:.6f})")
            print(f"    REPLACED {old_oid} -> {candidate_oid}")
            time.sleep(args.sleep)

        if replaced < n_needed:
            print(f"  WARNING: only replaced {replaced}/{n_needed} for {cls}", file=sys.stderr)

    # Verify
    still_missing = df[PS1_REQUIRED].isna().any(axis=1).sum()
    print(f"\nAfter replacement: {still_missing} rows still missing PS1 fields")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(df)} rows)")

    log_path = out_path.with_suffix(".replacements.log")
    log_path.write_text("\n".join(replacements_log), encoding="utf-8")
    print(f"Replacement log: {log_path} ({len(replacements_log)} swaps)")


if __name__ == "__main__":
    main()

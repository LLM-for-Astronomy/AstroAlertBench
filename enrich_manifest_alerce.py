"""
Download prompt-facing metadata from ALeRCE for each manifest row.

Uses:
  - query_detections(oid)  -> per-detection fid, magpsf, sigmapsf, ...
  - get_avro(oid, candid)  -> full ZTF candidate (sgscore*, distpsnr*, classtar, fwhm, ...)

Writes new columns suitable for prompts.py: fid_band, magpsf, sigmapsf, sgscore1, ...
Object-level ndethist/ncovhist in the CSV are left unchanged; candidate-level values are
stored as alert_ndethist / alert_ncovhist to avoid clobbering.
Also extracts PS1 cross-match fields: objectidps1, sgmag1, srmag1, simag1, szmag1, nmtchps.

Requires: pip install fastavro

Recommended (full manifest, five classes in parallel, then merge):
  python run_enrich_parallel.py --in data/manifest.csv --out data/manifest_enriched.csv

Single process (slower):
  python enrich_manifest_alerce.py --in data/manifest.csv --out data/manifest_enriched.csv

One class only (manual sharding or debugging):
  python enrich_manifest_alerce.py --in data/manifest.csv --out data/manifest_enriched_SN.csv --target-class SN
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import fastavro
except ImportError as e:
    raise SystemExit("pip install fastavro") from e

from alerce.core import Alerce

from download_alerce_benchmark import pick_candid_candidates

ROOT = Path(__file__).resolve().parent
SURVEY = "ztf"
FID_TO_BAND = {1: "g", 2: "r", 3: "i"}


def safe_int(x: object) -> int:
    """ZTF candid values are ~1e18 — never use float(); avoid 32-bit int overflow on Windows."""
    if pd.isna(x):
        raise ValueError("missing candid")
    if isinstance(x, (int, np.integer)):
        return int(x)
    s = str(x).strip()
    if not s or s.lower() == "nan":
        raise ValueError("empty candid")
    try:
        return int(s)
    except ValueError:
        pass
    from decimal import Decimal

    return int(Decimal(s))


def _candid_for_row(alerce: Alerce, row: pd.Series) -> int:
    raw = row.get("candid_used")
    if pd.notna(raw) and str(raw).strip() != "":
        return safe_int(raw)
    cands = pick_candid_candidates(alerce, str(row["oid"]))
    if not cands:
        raise RuntimeError(f"No detections for {row['oid']}")
    return int(cands[0])


def _parse_avro_candidate(raw_bytes: bytes) -> dict:
    rec = next(fastavro.reader(io.BytesIO(raw_bytes)))
    return rec.get("candidate") or {}


def enrich_row(alerce: Alerce, row: pd.Series) -> dict[str, object]:
    oid = str(row["oid"])
    candid = _candid_for_row(alerce, row)

    det = alerce.query_detections(oid, survey=SURVEY, format="pandas")
    if det is None or len(det) == 0:
        raise RuntimeError(f"No detections: {oid}")
    # candid must stay int64 — astype(int) can be 32-bit on Windows and overflows
    cand_col = det["candid"].to_numpy(dtype=np.int64, copy=False)
    m = det[cand_col == np.int64(candid)]
    if len(m) == 0:
        m = det.sort_values("mjd", ascending=True)
    row_det = m.iloc[0]

    raw = alerce.get_avro(oid, candid=candid, survey=SURVEY)
    cand = _parse_avro_candidate(raw)

    fid = cand.get("fid")
    if fid is None:
        fid = row_det.get("fid")
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
        "magpsf": cand.get("magpsf", row_det.get("magpsf")),
        "sigmapsf": cand.get("sigmapsf", row_det.get("sigmapsf")),
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", type=Path, default=ROOT / "data" / "manifest.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "manifest_enriched.csv")
    ap.add_argument("--sleep", type=float, default=0.12, help="Seconds between API calls")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument(
        "--target-class",
        type=str,
        default=None,
        metavar="CLASS",
        help="Only enrich rows where target_class equals this (e.g. SN, AGN, VS, asteroid, bogus).",
    )
    args = ap.parse_args()

    # Keep candid_used as string so pandas does not load ~1e18 IDs as lossy floats
    _cols = pd.read_csv(args.inp, nrows=0).columns.tolist()
    _dtype = {"candid_used": "string"} if "candid_used" in _cols else {}
    df = pd.read_csv(args.inp, dtype=_dtype, low_memory=False)
    if args.target_class is not None:
        tc = str(args.target_class).strip()
        df = df[df["target_class"].astype(str) == tc]
        if len(df) == 0:
            print(f"No rows with target_class={tc!r}", file=sys.stderr)
            sys.exit(1)
    df = df.iloc[args.start :]
    if args.limit is not None:
        df = df.head(args.limit)

    alerce = Alerce()
    rows_out: list[dict[str, object]] = []
    errors: list[str] = []

    for i, (_, row) in enumerate(df.iterrows()):
        oid = str(row["oid"])
        try:
            ex = enrich_row(alerce, row)
            merged = {**row.to_dict(), **ex}
            rows_out.append(merged)
            print(f"OK {i+1}/{len(df)} {oid}")
        except Exception as e:
            errors.append(f"{oid}: {e}")
            rows_out.append(row.to_dict())
            print(f"FAIL {oid}: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    out_df = pd.DataFrame(rows_out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False)
    print(f"Wrote {args.out} ({len(out_df)} rows)")
    if errors:
        err_path = args.out.with_suffix(".errors.txt")
        err_path.write_text("\n".join(errors), encoding="utf-8")
        print(f"Errors logged to {err_path}")


if __name__ == "__main__":
    main()

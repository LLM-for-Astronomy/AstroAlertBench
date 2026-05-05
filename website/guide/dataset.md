# Sources & splits

## Origin

Objects come from the **ALeRCE** broker API over **ZTF** alert streams. A download script:

- pulls **ranked candidate pools** per class,
- keeps a **minimum classifier probability floor** (see project `download_alerce_benchmark.py`),
- retires failed stamp URLs and takes the **next eligible object** until each class quota is met.

Outputs typically include:

- `data/manifest.csv` — one row per benchmark example,
- `data/summary.json` — run-level stats,
- `data/replacement_skips.log` — objects skipped during fill,
- `stamps_original/<class>/<oid>/` — **FITS** triplet (science, template, difference).

## Main paper-size split

For full-model comparisons we use a **balanced 1 500-row** manifest (300 per five-way class). In the repository this is usually **`manifest_benchmark_final.csv`** after you finalize class counts. Smaller **`manifest_fewshot.csv`** and enriched **`manifest_enriched.csv`** variants exist for few-shot and full-metadata prompt tests.

Always match **the same manifest** in `run_tinker_benchmark.py` and `evaluate.py` when reporting numbers.

## Enrichment

`enrich_manifest_alerce.py` can attach **AVRO / detection-level fields** (e.g. `magpsf`, `fid`-related bands, `sgscore1`, `distpsnr1`, …) needed for Part A gold and for richer prompts. Some columns are **required** by the runner (e.g. `fid`, `isdiffpos`); see repository `README` for the current list.

## What ships in git

**FITS** trees under `stamps_original/` and legacy `stamps_llm/` are usually **gitignored** because of size. **`stamps_llm_updated/`** PNG montages may be committed if you want a **self-contained clone** without rebuilding from FITS.

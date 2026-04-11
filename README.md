# LLM for astronomy — ZTF / ALeRCE stamp benchmark

Scripts to build a **stamp_classifier** benchmark from [ALeRCE](https://science.alerce.online/) (ZTF): 500 objects per class (SN, AGN, VS, asteroid, bogus), metadata, FITS stamps, and LLM-oriented PNG montages.

## Setup

```bash
pip install -r requirements.txt
```

## Download data (FITS + manifest)

Refetches ranked pools and fills **500 stamps per class** (skips failed stamp URLs and takes the next-highest-probability object).

```bash
python download_alerce_benchmark.py --rebuild
```

Outputs: `data/manifest.csv`, `data/summary.json`, `data/replacement_skips.log`, and cutouts under `stamps/<class>/<oid>/`.

## Build PNG montages for LLMs

```bash
python build_stamps_llm_montages.py
```

Writes `stamps_llm/<class>/<oid>/montage.png` (Science | Template | Image panels) from existing FITS. Original FITS are unchanged.

## Zero-shot evaluation (Tinker API)

Requires `TINKER_API_KEY` from the [Tinker console](https://tinker-console.thinkingmachines.ai/) and optional extra packages (`tinker`, `tinker-cookbook`, `transformers`, `torch`, `python-dotenv` — see `requirements.txt`). Put the key in **`.env`** as `TINKER_API_KEY=...` (file is gitignored); `api_tinker.py` loads it automatically.

Pipeline matches AstroAlertBench-style **inputs → prompt → structured JSON (Parts A–C)**; prompts live in `prompts.py` and are used by `api_tinker.py`. Alternate modules: `prompt_ablation` (fewer metadata fields), `prompt_agn_instruction` (same full metadata as `prompts.py` plus extra system text on using PS1 colors and `sgscore1`/`distpsnr1` for **AGN vs variable_star** in Part B/C).

```bash
set TINKER_API_KEY=your_key
python run_tinker_benchmark.py --manifest data/manifest_enriched.csv --limit 20 --out results/run1.jsonl
python evaluate.py --predictions results/run1.jsonl --manifest data/manifest_enriched.csv
```

- **Images:** one **montage PNG** per object (Science \| Template \| Difference) is sent with the user text (three separate cutouts can be added later).
- **Metadata:** prompts use **raw ZTF-style candidate fields** (e.g. `fid`, `isdiffpos`) plus a short field reference in the system message (see [ZTF Avro schema](https://zwickytransientfacility.github.io/ztf-avro-alert/schema.html)). Part A still asks for decoded `filter_band` (g/r/i) and `subtraction_sign` (positive/negative); evaluation gold uses `fid_band` and `isdiffpos` from the CSV. **Required columns:** `fid` and `isdiffpos` must be present — use **`manifest_enriched.csv`** after `python enrich_manifest_alerce.py` (`query_detections` + `get_avro` per object; requires `fastavro`). If they are missing, `run_tinker_benchmark.py` exits with an error at startup.

## Repository layout

| Path | Description |
|------|-------------|
| `download_alerce_benchmark.py` | ALeRCE API download + replacement logic |
| `build_stamps_llm_montages.py` | FITS → labeled PNG montages |
| `prompts.py` | System + user prompts (Parts A–C, JSON schema) |
| `prompt_agn_instruction.py` | Same as `prompts.py` user metadata + extended system guidance for AGN vs variable star |
| `api_tinker.py` | Tinker VLM sampling (Qwen3-VL + montage) |
| `run_tinker_benchmark.py` | Batch JSONL runner |
| `evaluate.py` | Parse JSON outputs; accuracy vs manifest |
| `enrich_manifest_alerce.py` | Fetch `magpsf`, `sgscore*`, `fid_band`, etc. from ALeRCE AVRO/detections |
| `data/` | Manifest and summary (tracked) |
| `stamps/`, `stamps_llm/` | Large binaries — ignored by git; regenerate locally |

## GitHub

Repository: [github.com/Cruuusade/LLM_FOR_ASTRONOMY](https://github.com/Cruuusade/LLM_FOR_ASTRONOMY)

**First-time push** (after creating the empty repo on GitHub):

```bash
cd /path/to/ZTF_Adjusted_Dataset
git remote add origin https://github.com/Cruuusade/LLM_FOR_ASTRONOMY.git   # skip if already added
git branch -M main
git push -u origin main
```

If `git push` asks for credentials, use a [Personal Access Token](https://github.com/settings/tokens) (classic: enable `repo` scope) as the password, or install [GitHub CLI](https://cli.github.com/) and run `gh auth login`.

Large FITS/PNG trees under `stamps/` and `stamps_llm/` are **not** tracked; only scripts and `data/` manifests are in git. Regenerate data locally with the commands above.

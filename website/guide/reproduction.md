# Setup & reproduction

## Environment

```bash
pip install -r requirements.txt
```

Use a virtual environment. Some backends require extra packages and API keys (`TINKER_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, …).

## Build or fetch data

1. **Download FITS + base manifest**

   ```bash
   python download_alerce_benchmark.py --rebuild
   ```

2. **Optional: enrich manifest** (full AVRO / detection fields)

   ```bash
   python enrich_manifest_alerce.py
   ```

3. **Build PNG montages**

   ```bash
   python build_stamps_llm_montages.py
   ```

   Ensure montages land under **`stamps_llm_updated/`** for default runners.

## Run evaluation (example)

Tinker-hosted model:

```bash
python run_tinker_benchmark.py \
  --manifest data/manifest_enriched.csv \
  --limit 20 \
  --out results/run1.jsonl
python evaluate.py --predictions results/run1.jsonl --manifest data/manifest_enriched.csv
```

Adjust `--backend`, `--model`, and reasoning flags for other providers (see `run_tinker_benchmark.py` header examples).

## This documentation site

From `website/`:

```bash
npm install
npm run dev
```

Build static files for hosting:

```bash
npm run build
```

Artifacts go to `website/.vitepress/dist/` (suitable for Netlify, GitHub Pages, or any static host).

# Second-rollout ablation (low-confidence re-trial)

This folder holds **per-model** stratified samples (n = 35) of alerts where that
model’s **first-pass mean Part B self-score** was **&lt; 4**, plus frozen
**first-pass JSON** for prompting a blind second trial.

## Layout

| Path | Purpose |
|------|---------|
| `METRICS_SPEC.md` | Final metric definitions (correction flow, calibration, McNemar, etc.). |
| `metadata/<slug>_n35.csv` | Subset of `data/manifest_benchmark_final.csv` rows + `ablation_prior_file`. |
| `priors/<slug>/<oid>.json` | First-pass record from the model’s benchmark JSONL. |
| `ablation_summary.json` | Pool sizes, per-class quotas, chosen OIDs. |

Regenerate manifests after editing the pool logic or benchmark JSONLs:

```bash
python -m viz.build_second_rollout_ablation
```

## Run second pass (one command per model)

Uses `prompts_second_roll_out_ablation.py` (project root). Pick `--concurrency`
to match your rate limits (Anthropic: 2 is typical).

| Model | Example command |
|-------|-----------------|
| GPT-5.4 high | `python run_second_rollout_benchmark.py --manifest data_second_roll_out_ablation/metadata/gpt54_high_n35.csv --backend openai --model gpt-5.4 --reasoning-effort high --out results/second_rollout_gpt54_high_n35.jsonl --concurrency 8` |
| GPT-5.4 none | `python run_second_rollout_benchmark.py --manifest data_second_roll_out_ablation/metadata/gpt54_none_n35.csv --backend openai --model gpt-5.4 --reasoning-effort none --out results/second_rollout_gpt54_none_n35.jsonl --concurrency 8` |
| Gemini 2.5 Flash none | `python run_second_rollout_benchmark.py --manifest data_second_roll_out_ablation/metadata/gemini25_flash_none_n35.csv --backend google --model gemini-2.5-flash --reasoning-effort none --out results/second_rollout_gemini25_flash_none_n35.jsonl --concurrency 8` |
| Claude Opus 4.7 think | `python run_second_rollout_benchmark.py --manifest data_second_roll_out_ablation/metadata/opus47_think_n35.csv --backend anthropic --model claude-opus-4-7 --reasoning-effort high --out results/second_rollout_opus47_think_n35.jsonl --concurrency 2` |
| Claude Opus 4.7 nothink | `python run_second_rollout_benchmark.py --manifest data_second_roll_out_ablation/metadata/opus47_nothink_n35.csv --backend anthropic --model claude-opus-4-7 --reasoning-effort none --out results/second_rollout_opus47_nothink_n35.jsonl --concurrency 2` |

## Evaluate paired outcomes

```bash
python evaluate_second_rollout.py \
  --second-jsonl results/second_rollout_gpt54_high_n35.jsonl \
  --manifest data_second_roll_out_ablation/metadata/gpt54_high_n35.csv \
  --out-json results/second_rollout_gpt54_high_n35.metrics.json
```

Add `--include-qualitative` to embed truncated Part B text for manual contradiction coding.

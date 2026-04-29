# `manifest_human_baselines_15.csv`

**15 rows** — one per **human baseline** cutout under `human_samples/human_baselines/` (metadata files `humanbaselinemetadata-<OID>.txt`).

**Row source:** `data/manifest_enriched.csv` (same column schema as `manifest_benchmark_final.csv`). These OIDs are **not** all present in `manifest_benchmark_final.csv` (only 3/15 overlap the 1500-row benchmark draw); enriched manifest is the join source so all Part B / ALERCE fields match `prompts.py`.

**Sort order:** `oid` ascending.

**Gold `target_class` distribution:** AGN 5, VS 3, SN 2, bogus 3, asteroid 3 (15 total).

**Montages for `run_tinker_benchmark` / `api_*`:** `stamps_llm_updated/<target_class>/<oid>/montage.png` (default; see `prompts.STAMPS_LLM_DIRNAME` / `ZTF_STAMPS_LLM_DIR`) — verified present for all 15 rows.

---

## Full-benchmark model grid (13 runs)

Use `--manifest data/manifest_human_baselines_15.csv` and point `--out` per run, e.g. under `results/human_baselines_15_<slug>.jsonl`. Slugs match `results_comparison/report/20260421_report_benchmark_full_all_runs.md`:

| Backend | Model / config | Example `--model` / flags |
|--------|------------------|---------------------------|
| anthropic | Opus 4.7 think | `claude-opus-4-7` `--reasoning-effort high` |
| anthropic | Opus 4.7 nothink | `claude-opus-4-7` `--reasoning-effort none` |
| openai | GPT-5.4 high | `gpt-5.4` `--reasoning-effort high` |
| openai | GPT-5.4 none | `gpt-5.4` `--reasoning-effort none` |
| google | Gemini 2.5 Pro | `gemini-2.5-pro` `--reasoning-effort high` |
| google | Gemini 2.5 Flash | `gemini-2.5-flash` `--reasoning-effort none` |
| tinker | Kimi K2.5 | `moonshotai/Kimi-K2.5` |
| tinker | Qwen3.5-397B think | `Qwen/Qwen3.5-397B-A17B` |
| tinker | Qwen3.5-397B nothink | `Qwen/Qwen3.5-397B-A17B` `--thinking disabled` |
| tinker | Qwen3.5-35B think | `Qwen/Qwen3.5-35B-A3B` |
| tinker | Qwen3.5-35B nothink | `Qwen/Qwen3.5-35B-A3B` `--thinking disabled` |
| tinker | Qwen3.5-4B think | `Qwen/Qwen3.5-4B` |
| tinker | Qwen3.5-4B nothink | `Qwen/Qwen3.5-4B` `--thinking disabled` |

Evaluate with `evaluate.py --predictions <jsonl> --manifest data/manifest_human_baselines_15.csv`.

**Full run folders** (same layout as `runs/20260421-2024-gpt-5.4-high-benchmark-full/` — `run.jsonl`, `metrics.json`, `runmeta.json` when available, `report.md`, `plots/`, `viz/`): from repo root run `python -m viz._build_human_baselines_15_run_folders` after all `results/human_baselines_15_*.jsonl` files exist. That creates `runs/<timestamp>-<slug>-human-baselines-15/` for each of the 13 model configs and refreshes `runs/index.md` / `runs/index.jsonl`.

---

*Created 2026-04-18.*

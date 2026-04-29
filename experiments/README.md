# Experiments

**This directory no longer stores per-run logs.** All VLM benchmark artifacts live under **`runs/<timestamp>-<slug>/`** (`run.jsonl`, `metrics.json`, `report.md`, `plots/`, `viz/`, optional `runmeta.json`), produced by **`viz.build_run_folder`** (see `.cursor/skills/log-experiment/SKILL.md`).

Use **`runs/index.md`** for a table of every run.

---

## Retired `EXP-*.md` files (removed 2026-04)

The former `EXP-20260419-*.md` notes duplicated **`runs/`** folders that were already created on 2026-04-19. Reference those run folders instead:

| Old experiment note | Canonical run folder |
|---|---|
| `EXP-20260419-qwen35-baseline-newparser` | [`runs/20260419-2047-qwen35-35b-a3b-baseline`](../runs/20260419-2047-qwen35-35b-a3b-baseline/report.md) |
| `EXP-20260419-qwen35-tokenlimit` | [`runs/20260419-2047-qwen35-35b-a3b-tokenlimit`](../runs/20260419-2047-qwen35-35b-a3b-tokenlimit/report.md) |
| `EXP-20260419-kimi-k25-think` | [`runs/20260419-2230-kimi-k25-think`](../runs/20260419-2230-kimi-k25-think/report.md) |
| `EXP-20260419-qwen35-397b` | [`runs/20260419-2230-qwen35-397b-a17b`](../runs/20260419-2230-qwen35-397b-a17b/report.md) |
| `EXP-20260419-qwen35-4b` | [`runs/20260419-2230-qwen35-4b`](../runs/20260419-2230-qwen35-4b/report.md) |
| `EXP-20260419-gpt54-high` | [`runs/20260419-2230-gpt-5.4-high`](../runs/20260419-2230-gpt-5.4-high/report.md) |
| `EXP-20260419-gpt54-none` | [`runs/20260419-2230-gpt-5.4-none`](../runs/20260419-2230-gpt-5.4-none/report.md) |

---

## If you need a new run folder

From repo root, after `run_tinker_benchmark.py` has written `results/<name>.jsonl`:

```bash
python -m viz.build_run_folder --jsonl results/<name>.jsonl --manifest data/<manifest>.csv --model <model_id> --slug <kebab-slug> [--backend tinker|openai] ...
```

Batch helper for human-baselines-15: `python -m viz._build_human_baselines_15_run_folders`.

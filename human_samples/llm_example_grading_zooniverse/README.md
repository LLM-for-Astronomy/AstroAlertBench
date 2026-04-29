# LLM example grading — Zooniverse layout (5 × 13)

Five **gold-labelled** cutouts from `data/manifest_benchmark_final.csv`, **one per 5-class label** (`SN`, `AGN`, `VS`, `asteroid`, `bogus`), with the same **13** full-benchmark model runs as `human_samples/llm_example_grading/`.

| OID | `target_class` | Note |
|-----|----------------|------|
| `ZTF19abkdsaw` | AGN | 13/13 parseable; mixed correct/incorrect models |
| `ZTF25aaxmsns` | SN | same |
| `ZTF19aayhwvd` | VS | same |
| `ZTF25aahvsli` | bogus | same |
| `ZTF26aargnnp` | asteroid | same; also in `llm_example_grading` |

**Per OID:**

- `combination/<OID>.png` — same spec as `llm_example_grading` / `human_baselines` (Science / Reference / Difference + metadata block).
- **13 PNGs** — `N_<model_slug>_grading.png` for `N = 1 … 13` and `RUN_SPECS` order in `viz/build_llm_example_grading.py` (Gemini → GPT → Opus → Kimi → Qwen). Each image uses section titles **Leading Interpretation and Support:** and **Alternative Analysis:** (own lines; body follows without JSON quoting), then LLM prediction and correct class. Width is trimmed to the rendered text (up to 900 px).

Selection rule: each OID must have a mappable 5-class label from Part C in **all 13** benchmark `run.jsonl` files, at least one model correct and one wrong versus manifest `target_class`, and **stamp metadata** usable for the combination figure (no reliance on `-999` / empty fields for core photometry and PS1 cross-match columns). The builder checks this when all 13 runs are present (otherwise it warns and skips validation).

**Regenerate:**

```text
python -m viz.build_llm_example_grading_zooniverse
```

Requires the same `runs/.../run.jsonl` files and `stamps_llm/<class>/<OID>/montage.png` inputs as `viz/build_llm_example_grading.py`.

*Built by `viz/build_llm_example_grading_zooniverse.py`.*

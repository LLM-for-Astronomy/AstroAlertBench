# LLM example grading (3 × 13)

Three **gold-labelled** cutouts from `data/manifest_benchmark_final.csv` (the 1 500-row benchmark), chosen so that across the **13** completed full-benchmark model runs:

- each model had **parseable** Part C for that OID on **≥10** runs, with **neither** all-correct **nor** all-wrong 5-class outcomes (mixed agreement), and  
- Part B self-scores (where present) are **confident** on average (median of per-model means ≥ **4.0**; per-row minimum of those means ≥ **3.0** in the scan that picked these OIDs).

| OID | `target_class` | Role / note |
|-----|----------------|-------------|
| `ZTF19abfqvbg` | AGN | ≈7 vs ≈6 models correct (among parsed); strong self-score spread still ≥4 for most runs. |
| `ZTF25abxlcvf` | SN (supernova) | Same “mixed + confident” pattern. |
| `ZTF26aargnnp` | asteroid | Same pattern. |

**Layout (each OID folder):**

- `combination/<OID>.png` — **Science / Reference / Difference** strip + metadata block, same spec as `human_samples/human_baselines/combination/` (e.g. `ZTF17aacriru.png` reference in repo history).
- **13 text files** (one per model) at the OID root — `N_<model_slug>_grading.txt` with `N` in 1…13, in the same order as `RUN_SPECS` in `viz/build_llm_example_grading.py` (1–2: Gemini; 3–4: GPT; 5–6: Opus; 7: Kimi; 8–13: Qwen by size, think before nothink; e.g. `1_gemini25_pro_high_grading.txt`, `8_qwen35_4b_think_grading.txt`, `13_qwen35_397b_nothink_grading.txt`). Each file contains:
  - `leading_interpretation_and_support` and `alternative_analysis` copied from that model’s `runs/.../run.jsonl` **parsed** JSON;
  - `LLM's Classification` = mapped 5-class label from Part C (or a note if unparseable);
  - `Correct Class` = gold `target_class` for that OID from the benchmark manifest;
  - `Your Grading` **left blank** for human use.

**Regenerate** (e.g. after re-running a benchmark and updating `run.jsonl`):

```text
python -m viz.build_llm_example_grading
```

If you still have the older layout (one subfolder per model with `grading.txt` inside, or a wrong leading index on the filename), run `python -m viz.fix_llm_grading_folder_names` to flatten to `N_<slug>_grading.txt` and renumber to match current `RUN_SPECS`.

---

*Created by `viz/build_llm_example_grading.py`.*

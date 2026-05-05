---
title: Visualizations
---

# Visualizations

This page shows the **kinds of assets** the benchmark site is meant to carry: **example stamps**, **summary graphs**, a **per-class heatmap**, **code** to regenerate plots, and **Markdown** patterns (fenced blocks, callouts, collapsible sections).

---

## Example stamp image (RGB montage)

Each model conditions on **one PNG** per alert: Science, reference (template), and difference panels in a single file (`oid` **ZTF26aargnnp**, class **asteroid** in the example below).

![Example ZTF stamp montage: Science, reference, and difference panels for ZTF26aargnnp](/figures/example_montage_ztf26aargnnp.png)

---

## Headline benchmark graph (absolute 5-class accuracy)

Bar chart: **13** full-benchmark runs on **n = 1500**, ranked by **absolute** five-way accuracy (parse rate × accuracy on valid JSON). Error bars are **1σ** binomial.

![Ranked absolute 5-class accuracy with error bars](/figures/01_absolute_5class_ranked.png)

---

## Per-class heatmap

Rows are runs (same ranking); columns are **SN, AGN, VS, asteroid, bogus**. Cell color encodes per-class accuracy.

![Per-class accuracy heatmap, 13 runs by 5 classes](/figures/02_per_class_heatmap.png)

---

## Code: regenerate these figures

From the repository root (with the thirteen `metrics.json` / run folders in place):

```bash
python -m viz._make_charts_benchmark_full_apr21
```

Evaluate a JSONL and write metrics (input to the chart module):

```bash
python evaluate.py --predictions results/your_run.jsonl --manifest data/manifest_benchmark_final.csv
```

---

## Markdown & layout blocks

VitePress extends Markdown with **admonitions** and **collapsible** sections—useful for long JSON or policy notes.

::: tip Example callout
This is a **tip** container (`::: tip`). Use it for short “how to read” notes beside figures.
:::

::: warning Truncated or partial runs
Some small open runs hit the **output cap**; their heatmap rows reflect **fewer than 300** usable predictions per class. Check parse rate on the [Leaderboard](/guide/leaderboard) before comparing to closed models.
:::

::: details Example: skeleton of model output (click to expand)
The model returns **one JSON object** per row. The evaluator expects keys that line up with [Parts A–C](/guide/task-format), for example:

```json
{
  "part_a": { "filter_band": "g", "subtraction_sign": "positive" },
  "part_b": { "scores": { "key_evidence": 4, "leading_interpretation": 5, "alternative_analysis": 4 } },
  "part_c": {
    "stage1": "real_object",
    "stage2": "astrophysical",
    "stage3": "asteroid"
  }
}
```

:::

### Fenced “markdown” snippet (shown as code)

How to cite a figure in your own README:

```md
![Heatmap](charts/benchmark_full_apr21/02_per_class_heatmap.png)
*Caption: per-class accuracy, 13 runs × 5 classes.*
```

### Inline links

Figures above live under site static path **`/figures/`** after build; in the repo they are mirrored from `results_comparison/report/charts/benchmark_full_apr21/` and `stamps_llm_updated/` for deployment.

See [External links](/guide/resources) for **GitHub**, **Hugging Face**, and **Zooniverse** pointers.

---
layout: doc
---

# ZTF / ALeRCE stamp benchmark

This site documents a **vision–language benchmark** built from [ALeRCE](https://science.alerce.online/) (Zwicky Transient Facility alerts), aimed at structured prediction on real astronomical “stamps”: **science**, **template**, and **difference** imaging plus broker-style metadata.

Models receive a **single RGB montage PNG** per alert and return **JSON** with AstroAlertBench-style **Parts A–C** (metadata extraction, self-reported reasoning quality, and a three-stage → five-way classification cascade).

See example **figures, heatmaps, and code blocks** on the [Visualizations](/guide/visualizations) page; **GitHub / Hugging Face / Zooniverse** links are on [Resources](/guide/resources).

::: tip Quick links
- [Figures & heatmap](/guide/visualizations)
- [External links (GitHub, HF, Zooniverse)](/guide/resources)
- [Leaderboard (full benchmark)](/guide/leaderboard)
- [Dataset sources & splits](/guide/dataset)
- [JSON task format](/guide/task-format)
- [Metrics & `evaluate.py`](/guide/evaluation)
- [GitHub repository](https://github.com/Cruuusade/LLM_FOR_ASTRONOMY)
:::

## Why it exists

Classifying variable and transient events from survey alerts is a core step in time-domain astronomy. This benchmark fixes a **per-class pool** of high-confidence examples, **PNG montages** suited to VLMs, and a **deterministic scorer** so different models are comparable on the same inputs and gold labels.

## What you need locally

Large assets (**FITS** cutouts, optional PNG trees) are **not** always shipped with the git repository. The [reproduction](/guide/reproduction) page lists how to download, build montages, run inference, and score JSONL outputs.

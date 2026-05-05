---
title: Resources & links
---

# Resources & links

| Resource | URL | Notes |
|----------|-----|--------|
| **Source code** | [github.com/Cruuusade/LLM_FOR_ASTRONOMY](https://github.com/Cruuusade/LLM_FOR_ASTRONOMY) | Clone this repo for `evaluate.py`, `run_tinker_benchmark.py`, prompts, and viz scripts. |
| **Dataset (Hugging Face)** | *[Update when public]* `https://huggingface.co/datasets/<ORG>/<DATASET_NAME>` | **Placeholder.** Replace with your real dataset or model card; nothing in-tree points here yet. |
| **Zooniverse** | [zooniverse.org](https://www.zooniverse.org/) | Human grading of model explanations uses Zooniverse-style workflows (e.g. “LLM Response Grading” in our studies). **Add your project URL** on this line when the project is public. |
| **Broker / archive context** | [ALeRCE](https://science.alerce.online/) | Where ZTF/ALeRCE metadata and stamp URLs for the build pipeline come from. |

::: tip For maintainers
When the HF dataset or Zooniverse project goes live, edit **`website/guide/resources.md`** (this file) and replace the placeholder cells so reviewers land on the right pages.
:::

## Related material in the repo

These paths exist for authors with the repository checked out (not all are shipped on the static site):

- Human-facing grading bundles: `human_samples/llm_example_grading_zooniverse/`
- Reports that reference Zooniverse exports: `results_comparison/report/20260503_report_zooniverse_llm_grading.md`

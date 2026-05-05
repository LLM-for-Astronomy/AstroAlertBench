# Images & montages

## Pipeline

1. Science-grade **FITS** cutouts live under `stamps_original/<class>/<oid>/`.
2. `build_stamps_llm_montages.py` renders **RGB PNG montages** for VLMs.
3. Runners read montages from **`stamps_llm_updated/`** by default (`prompts.STAMPS_LLM_DIRNAME`). Override with environment variable `ZTF_STAMPS_LLM_DIR` if you point at another tree.

## Layout

Each alert uses **one PNG** shown to the model. Panels are labeled (in order):

**Science | Template | Image**

where **Image** is the **difference (DIA)** image, **not** a duplicate science frame.

::: warning Common confusion
Brokers often say “difference” or “subtraction image”; our on-montage label **Image** means that differenced product. Part A may still ask for `subtraction_sign` etc.; gold comes from manifest fields such as `isdiffpos` / `fid_band`.
:::

## Example on the doc site

A downsampled **example montage** (asteroid alert **ZTF26aargnnp**) is shown on the [Visualizations](/guide/visualizations) page together with summary plots.

## Resolution & fidelity

Montage generation parameters (scaling, WCS alignment assumptions, bit depth) are defined in `build_stamps_llm_montages.py`. If you regenerate from FITS, keep the script version **pinned** when comparing published scores.

# LLM for astronomy — ZTF / ALeRCE stamp benchmark

Scripts to build a **stamp_classifier** benchmark from [ALeRCE](https://science.alerce.online/) (ZTF): 500 objects per class (SN, AGN, VS, asteroid, bogus), metadata, FITS stamps, and LLM-oriented PNG montages.

## Setup

```bash
pip install -r requirements.txt
```

## Download data (FITS + manifest)

Refetches ranked pools and fills **500 stamps per class** (skips failed stamp URLs and takes the next-highest-probability object).

```bash
python download_alerce_benchmark.py --rebuild
```

Outputs: `data/manifest.csv`, `data/summary.json`, `data/replacement_skips.log`, and cutouts under `stamps/<class>/<oid>/`.

## Build PNG montages for LLMs

```bash
python build_stamps_llm_montages.py
```

Writes `stamps_llm/<class>/<oid>/montage.png` (Science | Template | Image panels) from existing FITS. Original FITS are unchanged.

## Repository layout

| Path | Description |
|------|-------------|
| `download_alerce_benchmark.py` | ALeRCE API download + replacement logic |
| `build_stamps_llm_montages.py` | FITS → labeled PNG montages |
| `data/` | Manifest and summary (tracked) |
| `stamps/`, `stamps_llm/` | Large binaries — ignored by git; regenerate locally |

## Remote

[https://github.com/Cruuusade/LLM_FOR_ASTRONOMY](https://github.com/Cruuusade/LLM_FOR_ASTRONOMY)

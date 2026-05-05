# Overview

The benchmark connects three layers:

1. **Data** — ALeRCE-ranked ZTF objects per class, FITS stamps, and LLM-facing PNG montages keyed by `oid` (object id).
2. **Task** — A fixed prompt contract asking for **structured JSON**: Part A (numeric / categorical fields), Part B (self-assessment of reasoning), Part C (staged labels feeding a five-way science class).
3. **Evaluation** — `evaluate.py` parses model JSON, aligns predictions to **manifest-derived gold**, and emits accuracy, calibration, and per-class breakdowns.

It follows the same **Parts A–C philosophy** as AstroAlertBench-style alert understanding: models must both **read photometry/context** and **justify** (Part B) before the **cascade** (Part C) is scored.

## Classes

Five top-level science categories appear in the released pools:

| Class     | Meaning (short) |
|-----------|-----------------|
| SN        | Supernova / explosive transient candidates |
| AGN       | Active galactic nucleus variability |
| VS        | Galactic variable stars |
| asteroid  | Solar-system movers / streak artifacts treated as a class |
| bogus     | Instrumental / subtraction artifacts and unphysical candidates |

Pools are filled to **500 objects per class** when building the main download manifest (see [Dataset](/guide/dataset)); ablations may use smaller curated CSVs.

## Backends

The reference runners support multiple inference APIs (e.g. Tinker-hosted open weights, OpenAI, Google Gemini, Anthropic Claude). All share the **same prompt module** and **image path resolution**; only the transport and decoding knobs differ.

## Scope

- **In scope:** zero-shot (or few-shot if you swap manifests) VLM inference on static montages + metadata text; automated scoring vs manifest.
- **Out of scope for this site:** training VLMs, real-time broker operations, and human/Zooniverse adjudication (those may appear as separate study notes in the repository).

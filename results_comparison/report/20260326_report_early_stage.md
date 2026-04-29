# ZTF / ALeRCE Stamp Benchmark for LLM Astronomy (Early-Stage Report)

**Status:** dataset construction and asset packaging are complete; **zero-shot prompts** (§3) are **fixed** for initial runs; quantitative evaluation and metrics are still to be filled in. This document follows the *shape* of technical reports such as *Instructing LLMs to Negotiate using Reinforcement Learning with Verifiable Rewards* (problem → setup → metrics) and the *AstroAlertBench* / *LLM for Astronomy* framing (multimodal ZTF alert triage, ALeRCE stamp classifier, five-class taxonomy), while staying brief outside the dataset section.

**Repository:** [https://github.com/Cruuusade/LLM_FOR_ASTRONOMY](https://github.com/Cruuusade/LLM_FOR_ASTRONOMY)

---

## Abstract

We are building a **balanced multimodal benchmark** for vision–language evaluation on **Zwicky Transient Facility (ZTF)** alert cutouts brokered by **ALeRCE**, using the operational **stamp classifier** taxonomy: supernova (SN), active galactic nucleus (AGN), variable star (VS), asteroid, and bogus. For each class we retain **500** objects selected by **descending ALeRCE stamp-classifier probability** (with a minimum probability floor and **replacement** from the ranked pool when stamp retrieval fails). Each example includes **tabular metadata** from the object query and **three FITS stamps** (science, template, difference), plus **PNG montages** for LLM/VLM consumption. This report records what has been implemented, the **standardized multimodal prompt** (Parts A–C + JSON) for zero-shot evaluation, and **reserved slots** for **metrics** aligned with multimodal astronomy benchmarks (e.g. AstroAlertBench-style grounding and classification).

---

## 1 Introduction and Problem Formulation

Operational ZTF pipelines issue large numbers of **first-detection** alerts that must be triaged into scientifically useful categories. ALeRCE’s **stamp classifier** maps first-alert image triplets to five high-level classes, providing a **scalable weak label** suitable for benchmarking general models against a broker that astronomers already use ([ALeRCE](https://science.alerce.online/)). Our goal is not to reproduce the neural stamp network, but to **standardize inputs** (images + metadata) and **labels** (stamp-classifier class + probability statistics) so that **LLMs / VLMs** can be compared on the same evidence used in broker-style triage—consistent with the problem setup described in *AstroAlertBench: Evaluating Vision Language Models for Multimodal Astronomical Alert Triage* (ZTF cutouts, ALeRCE taxonomy, metadata serialization).

At this **early stage** we prioritize: (i) **reproducible data collection**, (ii) **class balance** (500 per class), (iii) **high-confidence sampling** with documented floors and **replacement** when APIs return errors instead of FITS.

---

## 2 Dataset Construction (Primary Section)

### 2.1 Source and Labels


| Item           | Description                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Survey**     | ZTF (via ALeRCE API)                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Classifier** | ALeRCE `stamp_classifier` (broker real-time stamp classifier setting)                                                                                                                                                                                                                                                                                                                                                                                   |
| **Classes**    | `SN`, `AGN`, `VS`, `asteroid`, `bogus` (five-way classification)                                                                                                                                                                                                                                                                                                                                                                                        |
| **Selection**  | Per class: query objects with `order_by=probability`, `order_mode=DESC`, minimum probability **≥ 0.8** (Explorer-equivalent filter). Take the top candidates until **500 successful stamp downloads** per class; if an object’s stamps cannot be retrieved (e.g. HTTP returns JSON instead of FITS), **skip** and use the **next** object in the ranked list. **Object IDs are unique** across the whole benchmark (no duplicate `oid` across classes). |


### 2.2 Modalities per Example

1. **Metadata (tabular):** Fields returned by ALeRCE `query_objects` for each `oid` (e.g. coordinates, detection counts, times, `probability`, `classifier`, etc.), consolidated in `data/manifest.csv`.
2. **Images (FITS):** For each accepted detection, three cutouts under `stamps_original/<class>/<oid>/`: `science.fits`, `template.fits`, `difference.fits` (63×63 ZTF-style stamps).
3. **Images (LLM-facing PNG):** One **montage** per object under `stamps_llm_updated/<class>/<oid>/montage.png` by default (`prompts.STAMPS_LLM_DIRNAME`; legacy trees may use `stamps_llm/`): three panels labeled **Science**, **Template**, **Image** (the third panel is the **difference** cutout; label text follows the montage script). Stretched to 8-bit with a percentile-based normalization for display.

### 2.3 Summary Statistics (Current `data/summary.json`)

Selection used **500** objects per class. Reported **min / max** stamp-classifier **probability** among the **selected** set (per class):


| Class    | Count | Min probability (selected) | Max probability (selected) |
| -------- | ----- | -------------------------- | -------------------------- |
| SN       | 500   | 0.896107                   | 0.953128                   |
| AGN      | 500   | 0.856078                   | 0.898750                   |
| VS       | 500   | 0.942687                   | 0.968923                   |
| asteroid | 500   | 1.000000                   | 1.000000                   |
| bogus    | 500   | 0.951082                   | 0.977276                   |


**Note:** The minimum probability **within each class’s 500** is the **lowest** score among that high-confidence slice (useful for reporting dataset difficulty). The global selection floor remains **0.8** (`min_probability_floor`).

### 2.4 Artifacts and Reproducibility


| Path                           | Role                                                                                                                              |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `download_alerce_benchmark.py` | Fetch ranked pools; fill 500/class with replacement; write `data/manifest.csv`, `data/summary.json`, `data/replacement_skips.log` |
| `build_stamps_llm_montages.py` | FITS → PNG montages (place updated outputs under `stamps_llm_updated/` for current runs)                                                                                              |
| `data/manifest.csv`            | One row per benchmark example (oid, class, probabilities, candid, paths, …)                                                       |
| `stamps_original/`, `stamps_llm/` | Large binaries; **not** tracked in git (FITS + optional legacy montages)                                                                        |
| `stamps_llm_updated/` | PNG montages for VLMs; **may** be tracked in git for reproducible clones                                                                        |


### 2.5 What We Still Need (Dataset)

- **Prompt-facing metadata subset:** Full broker metadata exists in principle; we still need a **fixed, documented** text serialization (which columns go into the model prompt vs. held out for scoring only)—as in AstroAlertBench’s distinction between *stored* vs *prompt-facing* metadata.
- **Optional upgrade:** Align even more tightly with AstroAlertBench by attaching **AVRO-level** candidate fields for each chosen `candid` if we want parity with “first-detection packet” wording (current pipeline centers on object query + stamps + chosen candid).
- **Hosting:** Large FITS trees (`stamps_original/`) often need **separate release** (e.g. Zenodo, Hugging Face datasets, or Git LFS); PNG montages in `stamps_llm_updated/` may be committed to GitHub if repo size is acceptable.

---

## 3 Prompt Design (Zero-Shot)

**Goal.** We construct a standardized multimodal prompt that combines image triplets (Science, Template, Difference) with selected metadata fields, and requires the model to produce a **structured, machine-parseable response** divided into **Part A (metadata grounding)**, **Part B (scientific interpretation)**, and **Part C (staged classification)**. This follows the evaluation protocol used in multimodal astronomy benchmarks such as AstroAlertBench.

### 3.1 Prompt Structure

Each example is serialized into a consistent format consisting of:

- **Image inputs:** Science, Template, and Difference cutouts  
- **Metadata:** Selected prompt-facing fields (e.g. band, magnitude, sgscore)  
- **Instructions:** Task definition, class definitions, and output schema  

### 3.2 System Prompt

> You are an experienced astrophysicist. Your task is to classify astronomical transient candidates using three image cutouts (Science, Template, Difference) and associated metadata.
>
> You must analyze the images and metadata carefully and produce a structured response divided into three parts:
>
> **Part A: Metadata Grounding**  
> Extract and restate the key metadata fields and relevant observable properties.
>
> **Part B: Scientific Interpretation**  
> Provide a concise scientific interpretation of the candidate based on the images and metadata.
>
> **Part C: Staged Classification**  
> Make a step-by-step classification decision:
> - **Stage 1:** Determine whether the detection is a real astrophysical object or bogus  
> - **Stage 2:** Determine whether it is astrophysical or non-astrophysical  
> - **Stage 3:** Assign one of the five classes: SN, AGN, VS, asteroid, or bogus  
>
> Your final answer must follow the required JSON format exactly.

### 3.3 User Prompt Template

Fill placeholders `{oid}`, `{fid / band}`, `{magpsf}`, `{sgscore1}` (and any additional fields) from the manifest / AVRO for each alert.

**Alert ID:** `{oid}`

**Images:**

- Science image: recent observation  
- Template image: reference observation  
- Difference image: Science − Template  

**Metadata:**

- Band: `{fid / band}`  
- Magnitude (magpsf): `{magpsf}`  
- sgscore1: `{sgscore1}`  
- Detection statistics and additional fields as provided  

**Task:** Analyze the image triplet and metadata, then complete Parts A–C.

**Class Definitions:**

- **SN (Supernova):** Transient event not present in template, often point-like and located near a host galaxy  
- **AGN:** Persistent or variably bright source associated with a galaxy nucleus  
- **VS (Variable Star):** Stellar variability, typically present in both Science and Template images  
- **Asteroid:** Moving object; may show positional shift or streak-like morphology  
- **Bogus:** Artifacts such as noise, cosmic rays, subtraction errors, or misalignment  

**Instructions:**

1. Focus on the central object in the images  
2. Compare Science, Template, and Difference images  
3. Use metadata to support your reasoning  
4. Follow the staged classification process  

**Output Format (strict JSON):**

```json
{
  "Part A": {
    "band": "...",
    "magnitude": "...",
    "sgscore": "...",
    "key_features": "..."
  },
  "Part B": {
    "interpretation": "..."
  },
  "Part C": {
    "stage1": "real_object | bogus",
    "stage2": "astrophysical | non_astrophysical",
    "stage3": "SN | AGN | VS | asteroid | bogus",
    "confidence": 0.0
  }
}
```

### 3.4 Design Rationale

This structured prompt design enables:

- **Grounding evaluation:** Part A measures whether the model correctly uses metadata  
- **Interpretability:** Part B separates reasoning from final prediction  
- **Fine-grained evaluation:** Part C enables staged error analysis  
- **Robust parsing:** JSON output ensures machine-readable results  

### 3.5 Future Extensions

We plan to explore:

- Few-shot prompting with representative examples  
- Ablations with and without metadata  
- Alternative reasoning formats (e.g. chain-of-thought vs concise rationale)  

**Inference:** Zero-shot runs will use the **Tinker** API to test models.

### 3.6 Reference: MeerLICHT Real/Bogus (Prior Work — Binary Task)

The following is **not** our ZTF five-class prompt; it is a **reference template** from the MeerLICHT / [SpaceHack](https://github.com/turanbulmus/spacehack) line (binary Real vs Bogus). Our benchmark uses ZTF/ALeRCE naming and five classes.

**Persona (excerpt):** You are an experienced astrophysicist tasked with classifying transients into **Real** or **Bogus** from three images…

**Instructions (excerpt):** New / Reference / Difference cutouts; criteria for shape, flux, artifacts; JSON output with interest score — see SpaceHack materials for full text.

---

## 4 Evaluation Metrics *(Reserved — to be finalized)*

Following the *separation of concerns* in the negotiation RL paper (clear **metric definitions** before results) and AstroAlertBench’s **Part A / B / C** style, we reserve the following **slots**. Actual numbers will be filled after running models.

### 4.1 Classification Quality


| Metric                         | Definition / notes                                                         |
| ------------------------------ | -------------------------------------------------------------------------- |
| **Accuracy**                   | Fraction of correct top-1 class predictions vs. ALeRCE stamp label         |
| **Macro-F1**                   | Unweighted mean of per-class F1 (important for balanced 500/ class)        |
| **Per-class precision/recall** | Confusion matrix SN, AGN, VS, asteroid, bogus                              |
| **Calibration**                | Reliability vs. model-reported confidence (if JSON includes probabilities) |


### 4.2 Format & Grounding *(optional, AstroAlertBench-inspired)*


| Metric                         | Definition / notes                                                           |
| ------------------------------ | ---------------------------------------------------------------------------- |
| **JSON validity rate**         | Parsable structured output rate (cf. “Valid Rate” in negotiation benchmarks) |
| **Metadata grounding**         | When metadata is provided, score whether rationale cites correct fields      |
| **Human / judge model review** | Subset scored for scientific plausibility of rationale                       |


### 4.3 Efficiency & Cost


| Metric                       | Definition / notes  |
| ---------------------------- | ------------------- |
| **Tokens / USD per example** | For API-hosted VLMs |
| **Latency**                  | Wall time per batch |


---

## 5 Current Limitations

- Labels are **broker stamp-classifier** outputs, not independent human truth; errors in ALeRCE propagate as label noise.  
- **Asteroid** class in the current summary shows **probability 1.0** across the selected range—reporting and modeling should treat that **ceiling effect** explicitly.  
- PNG montages use a **display stretch**; models should be evaluated with a **fixed preprocessing** policy declared in the final benchmark card.

---

## 6 References *(selected)*

- ALeRCE: [https://science.alerce.online/](https://science.alerce.online/)  
- ZTF public data releases: [https://www.ztf.caltech.edu/ztf-public-releases.html](https://www.ztf.caltech.edu/ztf-public-releases.html)  
- Carrasco-Davis et al.; ALeRCE stamp classifier (see ALeRCE publications).  
- *AstroAlertBench* manuscript (Claire Chen, Caltech) — multimodal ZTF/ALeRCE alert triage benchmark framing.  
- *Instructing LLMs to Negotiate using Reinforcement Learning with Verifiable Rewards* (Claire Chen) — example of abstract + numbered sections + explicit metric tables.  
- MeerLICHT / SpaceHack prompting lineage: [https://github.com/turanbulmus/spacehack](https://github.com/turanbulmus/spacehack)

---

*Document version: early stage — dataset and §3 zero-shot prompt are authoritative; §4 metrics are placeholders until experiments complete.*
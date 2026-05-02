"""Build `visualization/outputs/` and `visualization/prompts/` HTML pages.

- **outputs/** — one self-contained page per full-benchmark model (13 runs) for OID
  ``ZTF26aargnnp``, same layout as ``runs/.../viz/<class>/<oid>.html`` via
  ``viz.html_report.render_datapoint_html``.
- **prompts/** — ``general_prompt.html`` (``prompts.py`` + benchmark manifest row for
  that OID) and ``second_rollout_ablation.html`` (``prompts_second_roll_out_ablation.py``;
  example OID with bundled prior JSON, documented in-page).

  python -m viz.build_visualization_bundle
"""
from __future__ import annotations

import html as html_module
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz.build_run_folder import _load_jsonl, _reconstruct_prompts  # noqa: E402
from viz.html_report import render_datapoint_html  # noqa: E402

OUT_ROOT = PROJECT_ROOT / "visualization"
OUT_OUTPUTS = OUT_ROOT / "outputs"
OUT_PROMPTS = OUT_ROOT / "prompts"

# Same 13 full-benchmark folders as results_comparison / calibration charts.
RUNS: list[tuple[str, str]] = [
    ("GPT-5.4 high", "runs/20260421-2024-gpt-5.4-high-benchmark-full"),
    ("GPT-5.4 none", "runs/20260421-2032-gpt-5.4-none-benchmark-full"),
    ("Claude Opus 4.7 think", "runs/20260423-0942-opus47-think-benchmark-full"),
    ("Claude Opus 4.7 nothink", "runs/20260424-2324-opus47-nothink-benchmark-full"),
    ("Gemini 2.5 Pro high", "runs/20260424-1809-gemini25-pro-high-benchmark-full"),
    ("Gemini 2.5 Flash none", "runs/20260423-2110-gemini25-flash-none-benchmark-full"),
    ("Kimi K2.5 think", "runs/20260420-1226-kimi-k25-benchmark-full"),
    ("Qwen3.5-397B think", "runs/20260420-1554-qwen35-397b-a17b-benchmark-full"),
    ("Qwen3.5-397B nothink", "runs/20260421-0025-qwen35-397b-a17b-nothink-benchmark-full"),
    ("Qwen3.5-35B think", "runs/20260420-2054-qwen35-35b-a3b-benchmark-full"),
    ("Qwen3.5-35B nothink", "runs/20260421-0019-qwen35-35b-a3b-nothink-benchmark-full"),
    ("Qwen3.5-4B think", "runs/20260420-1920-qwen35-4b-benchmark-full"),
    ("Qwen3.5-4B nothink", "runs/20260421-0002-qwen35-4b-nothink-benchmark-full"),
]

MANIFEST_PATH = PROJECT_ROOT / "data" / "manifest_benchmark_final.csv"
OID_TARGET = "ZTF26aargnnp"

# Logtree / per-datapoint HTML uses this stylesheet (matches reference viz pages).
LT_VIZ_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.45;
    max-width: 1200px;
    margin: 0 auto;
    padding: 14px;
    background: var(--lt-bg, #f5f5f5);
    color: var(--lt-text, #333);
}

.lt-root {
    background: var(--lt-card, white);
    padding: 1.2rem 1.4rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.lt-title {
    margin: 0 0 0.5rem 0;
    color: var(--lt-accent, #2563eb);
    border-bottom: 2px solid var(--lt-border, #e5e7eb);
    padding-bottom: 0.5rem;
}

.lt-subtitle {
    color: var(--lt-sub, #666);
    font-size: 0.875rem;
    margin-bottom: 1.2rem;
}

.lt-section {
    margin: 0.95rem 0;
    padding-left: 0.75rem;
    border-left: 2px solid var(--lt-border, #e5e7eb);
}

.lt-section-body {
    margin-top: 0.12rem;
}

.lt-section h2, .lt-section h3, .lt-section h4, .lt-section h5, .lt-section h6 {
    margin: 0.2rem 0;
    line-height: 1.3;
    color: var(--lt-accent, #2563eb);
}

.lt-h2 { font-size: 1.15rem; }
.lt-h3 { font-size: 1.05rem; }

.lt-details {
    margin: 0.35rem 0;
    border: 1px solid var(--lt-border, #e5e7eb);
    border-radius: 4px;
    padding: 0.35rem 0.45rem;
}

.lt-details summary {
    cursor: pointer;
    font-weight: 600;
    user-select: none;
}

.lt-details-body {
    margin-top: 0.25rem;
    padding: 0.35rem 0.45rem;
    background: var(--lt-bg, #f5f5f5);
    border-radius: 4px;
    overflow-x: auto;
}

.lt-details-body pre {
    margin: 0;
    font-family: var(--lt-mono, "Courier New", monospace);
    font-size: 0.875rem;
    white-space: pre-wrap;
}
"""


def _slug_label(label: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", label.strip()).strip("-").lower()
    return s or "model"


def _write_prompt_only_html(
    out_path: Path,
    *,
    page_title: str,
    subtitle: str,
    system_prompt: str,
    user_prompt: str,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_out = f"""<!doctype html>
<html lang="en">
<head>
<title>{html_module.escape(page_title)}</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>{LT_VIZ_CSS}
</style></head>
<body class="lt-root">
  <h1 class="lt-title">{html_module.escape(page_title)}</h1>
  <div class="lt-subtitle">{html_module.escape(subtitle)} · Generated {ts}</div>
  <section class="lt-section">
    <h2 class="lt-h2">Prompt</h2>
    <div class="lt-section-body">
      <section class="lt-section">
        <h3 class="lt-h3">System prompt</h3>
        <div class="lt-details">
          <details open>
            <summary>System prompt (full)</summary>
            <div class="lt-details-body"><pre>{html_module.escape(system_prompt)}</pre></div>
          </details>
        </div>
      </section>
      <section class="lt-section">
        <h3 class="lt-h3">User prompt</h3>
        <div class="lt-details-body"><pre>{html_module.escape(user_prompt)}</pre></div>
      </section>
    </div>
  </section>
</body>
</html>
"""
    out_path.write_text(html_out, encoding="utf-8")


def build_outputs(manifest: pd.DataFrame) -> int:
    manifest_by_oid = manifest.set_index("oid")
    if OID_TARGET not in manifest_by_oid.index:
        raise SystemExit(f"OID {OID_TARGET} not in {MANIFEST_PATH}")
    mrow = manifest_by_oid.loc[OID_TARGET]
    n_ok = 0
    for i, (label, rel_run) in enumerate(RUNS):
        run_dir = PROJECT_ROOT / rel_run
        jsonl = run_dir / "run.jsonl"
        slug = _slug_label(label)
        out_path = OUT_OUTPUTS / f"{i + 1:02d}_{slug}_{OID_TARGET}.html"
        if not jsonl.is_file():
            print(f"[skip] missing {jsonl}")
            continue
        rows = _load_jsonl(jsonl)
        row = next((r for r in rows if r.get("oid") == OID_TARGET), None)
        if row is None:
            print(f"[skip] no row for {OID_TARGET} in {run_dir.name}")
            continue
        try:
            sys_p, usr_p = _reconstruct_prompts(mrow, OID_TARGET, "prompts")
        except Exception as e:
            sys_p, usr_p = f"(prompt reconstruction failed: {e})", ""
        try:
            render_datapoint_html(row, mrow, sys_p, usr_p, out_path)
            print(f"  wrote {out_path.relative_to(PROJECT_ROOT)}")
            n_ok += 1
        except Exception as e:
            print(f"[fail] {out_path.name}: {e}")
    return n_ok


def build_prompt_pages(manifest: pd.DataFrame) -> None:
    manifest_by_oid = manifest.set_index("oid")
    m_target = manifest_by_oid.loc[OID_TARGET]
    sys_g, usr_g = _reconstruct_prompts(m_target, OID_TARGET, "prompts")
    _write_prompt_only_html(
        OUT_PROMPTS / "general_prompt.html",
        page_title=f"Benchmark general prompt — {OID_TARGET}",
        subtitle="Module `prompts.py`; user message built from `manifest_benchmark_final.csv` row",
        system_prompt=sys_g,
        user_prompt=usr_g,
    )
    print(f"  wrote {OUT_PROMPTS / 'general_prompt.html'}")

    ab_path = (
        PROJECT_ROOT
        / "data_second_roll_out_ablation"
        / "metadata"
        / "gpt54_high_n35.csv"
    )
    if not ab_path.is_file():
        print(f"[skip] second_rollout_ablation.html — missing {ab_path}")
        return
    ab = pd.read_csv(ab_path, low_memory=False)
    ex_oid = "ZTF26aargnnc"
    if ex_oid not in set(ab["oid"].astype(str)):
        ex_oid = str(ab["oid"].iloc[0])
    row_ab = ab[ab["oid"] == ex_oid].iloc[0]
    import importlib

    mod = importlib.import_module("prompts_second_roll_out_ablation")
    sys_s = mod.SYSTEM_PROMPT
    meta = mod.manifest_row_to_metadata(row_ab)
    usr_s = mod.build_user_prompt(ex_oid, meta)
    note = (
        f"Module `prompts_second_roll_out_ablation.py`. Example OID `{ex_oid}` from "
        "`data_second_roll_out_ablation/metadata/gpt54_high_n35.csv` (first-pass JSON "
        "bundled under `ablation_prior_file`). No prior JSON is checked in for "
        f"`{OID_TARGET}`; prompt structure and addendum are the same for every OID "
        "in the ablation run when priors exist."
    )
    _write_prompt_only_html(
        OUT_PROMPTS / "second_rollout_ablation.html",
        page_title="Second-rollout ablation — full prompt",
        subtitle=note,
        system_prompt=sys_s,
        user_prompt=usr_s,
    )
    print(f"  wrote {OUT_PROMPTS / 'second_rollout_ablation.html'}")


def main() -> None:
    OUT_OUTPUTS.mkdir(parents=True, exist_ok=True)
    OUT_PROMPTS.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(MANIFEST_PATH, low_memory=False)
    print(f"Writing visualization bundle under {OUT_ROOT.relative_to(PROJECT_ROOT)} …")
    n = build_outputs(manifest)
    print(f"  outputs: {n} HTML file(s) for {OID_TARGET}")
    build_prompt_pages(manifest)
    print("done.")


if __name__ == "__main__":
    main()

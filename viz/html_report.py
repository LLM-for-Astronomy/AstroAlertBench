"""Render one self-contained HTML per datapoint via tinker_cookbook.utils.logtree.

HTML layout (nested <section> headers):

  H1  <oid> — <target_class>
    H2  Verdict
        - predicted vs gold label, correctness at each stage
    H2  Input
        H3  Montage image (inline base64 PNG)
        H3  Metadata exposed to model
    H2  Prompt
        H3  System prompt
        H3  User prompt
    H2  Model output
        H3  Raw response (collapsed <details> when very long)
        H3  Parsed JSON
    H2  Scoring
        H3  Part A per-field correctness
        H3  Part C stage-by-stage
        H3  Error categories (format + value codes)
    H2  Tokens & run info

The generator degrades gracefully when fields are missing (e.g. `parsed` is None,
`raw_text` is truncated, `n_reasoning_tokens` is absent for tinker runs).
"""
from __future__ import annotations

import base64
import html as _html
import json
import sys
from pathlib import Path
from typing import Any

from tinker_cookbook.utils import logtree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluate import GOLD_STAGES, PART_A_QUESTIONS, check_part_a_question  # noqa: E402
from evaluate import get_gold_part_a, normalize_stage1, normalize_stage2, normalize_stage3_label  # noqa: E402


def _encode_png_b64(img_path: Path) -> str | None:
    try:
        data = Path(img_path).read_bytes()
    except (FileNotFoundError, OSError):
        return None
    return base64.b64encode(data).decode("ascii")


def _truncate(text: str, limit: int = 40000) -> tuple[str, bool]:
    """Return (possibly-truncated-text, was_truncated). Keeps HTML small."""
    if len(text) <= limit:
        return text, False
    return text[:limit] + f"\n\n... [truncated {len(text) - limit} chars] ...", True


def _verdict_table(row: dict[str, Any], gold_label: str | None) -> dict[str, Any]:
    parsed = row.get("parsed") or {}
    part_c = parsed.get("Part C") or parsed.get("part_c") or {}
    s1 = normalize_stage1(part_c.get("stage1"))
    s2 = normalize_stage2(part_c.get("stage2"))
    s3 = normalize_stage3_label(part_c.get("stage3"))

    pred_5class = _to_5class(s1, s2, s3)
    correct_overall = (pred_5class == gold_label) if gold_label else None

    g1 = g2 = g3 = None
    if gold_label in GOLD_STAGES:
        g1, g2, g3 = GOLD_STAGES[gold_label]

    return {
        "Gold (5-class)": gold_label or "?",
        "Predicted (5-class)": pred_5class or "?",
        "Correct?": _mark(correct_overall),
        "Stage 1 (real/artifact)": f"{s1 or '—'}   (gold: {g1 or '—'}){_mark(s1 == g1) if g1 else ''}",
        "Stage 2 (astro/solar)": f"{s2 or '—'}   (gold: {g2 or '—'}){_mark(s2 == g2) if g2 else ''}",
        "Stage 3 (subclass)":    f"{s3 or '—'}   (gold: {g3 or '—'}){_mark(s3 == g3) if g3 else ''}",
    }


def _to_5class(s1: str | None, s2: str | None, s3: str | None) -> str | None:
    if s1 == "artifact":
        return "bogus"
    if s1 == "real_object":
        if s2 == "solar_system":
            return "asteroid"
        if s2 == "astrophysical":
            if s3 == "supernova":
                return "SN"
            if s3 == "AGN":
                return "AGN"
            if s3 == "variable_star":
                return "VS"
    return None


def _mark(ok: bool | None) -> str:
    if ok is None:
        return ""
    return "  [correct]" if ok else "  [wrong]"


def _part_a_row_table(row: dict, manifest_row: Any) -> dict[str, str] | None:
    parsed = row.get("parsed") or {}
    pa = parsed.get("Part A") or parsed.get("part_a")
    if not isinstance(pa, dict):
        return None
    gold_a = get_gold_part_a(manifest_row)
    out: dict[str, str] = {}
    for q in PART_A_QUESTIONS:
        pred = pa.get(q)
        gold = gold_a.get(q) if gold_a else None
        if gold is None:
            out[q] = f"pred={pred!r}  gold=—"
        else:
            ok = check_part_a_question(q, pred, gold)
            out[q] = f"pred={pred!r}   gold={gold!r}   {'[correct]' if ok else '[wrong]'}"
    return out


def _token_table(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in ("n_prompt_tokens", "n_output_tokens", "n_answer_tokens", "n_reasoning_tokens"):
        if k in row and row[k] is not None:
            out[k] = row[k]
    if "max_tokens" in row:
        out["max_tokens"] = row["max_tokens"]
    if "truncated" in row:
        out["truncated"] = bool(row["truncated"])
    if "finish_reason" in row:
        out["finish_reason"] = row["finish_reason"]
    if "reasoning_effort" in row:
        out["reasoning_effort"] = row["reasoning_effort"]
    if "model" in row:
        out["model"] = row["model"]
    return out


def render_datapoint_html(
    row: dict[str, Any],
    manifest_row: Any,
    system_prompt: str,
    user_prompt: str,
    out_path: Path,
) -> None:
    """Write one HTML file to `out_path` summarizing the prediction for one oid.

    Parameters
    ----------
    row : dict
        A record from the predictions JSONL (with parsed already populated).
    manifest_row : pd.Series
        The corresponding manifest row (used to derive gold Part A + 5-class label).
    system_prompt, user_prompt : str
        The prompts that were sent to the model for this row. These are
        regenerated from `prompts.py` by the orchestrator and passed in.
    out_path : Path
        Destination .html file.
    """
    oid = row.get("oid", "?")
    tc = row.get("target_class") or manifest_row.get("target_class", "?")
    title = f"{oid} — {tc}"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with logtree.init_trace(title, path=str(out_path)):
        # -------- Verdict --------
        with logtree.scope_header("Verdict"):
            logtree.table_from_dict(_verdict_table(row, tc), caption="Prediction vs gold")

        # -------- Input --------
        with logtree.scope_header("Input"):
            with logtree.scope_header("Montage image (Science | Reference | Difference)"):
                b64 = _encode_png_b64(row.get("montage_path", ""))
                if b64:
                    logtree.log_html(
                        f'<img src="data:image/png;base64,{b64}" '
                        f'style="max-width:100%;height:auto;border:1px solid #888;" '
                        f'alt="{_html.escape(oid)} montage">'
                    )
                else:
                    logtree.log_text(f"(montage not found on disk: {row.get('montage_path', '?')})")

            with logtree.scope_header("Metadata exposed to model"):
                from prompts import manifest_row_to_metadata  # lazy import
                meta = manifest_row_to_metadata(manifest_row)
                logtree.table_from_dict({k: str(v) for k, v in meta.items()}, caption="Metadata fields")

        # -------- Prompt --------
        with logtree.scope_header("Prompt"):
            with logtree.scope_details("System prompt (click to expand)"):
                logtree.log_html(f"<pre>{_html.escape(system_prompt)}</pre>")
            with logtree.scope_header("User prompt"):
                logtree.log_html(f"<pre>{_html.escape(user_prompt)}</pre>")

        # -------- Model output --------
        with logtree.scope_header("Model output"):
            raw_text = row.get("raw_text", "") or ""
            with logtree.scope_header("Raw text (full model output incl. thinking, verbatim from jsonl)"):
                body, was_trunc = _truncate(raw_text, limit=40000)
                logtree.log_html(f"<pre>{_html.escape(body)}</pre>")
                if was_trunc:
                    logtree.log_text("(raw text truncated for HTML size)")

            parsed = row.get("parsed")
            with logtree.scope_header("Parsed JSON (extracted by evaluate.extract_json_object)"):
                if parsed is None:
                    logtree.log_text("(parsed=None — format error; see Scoring section)")
                else:
                    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                    logtree.log_html(f"<pre>{_html.escape(pretty)}</pre>")

        # -------- Scoring --------
        with logtree.scope_header("Scoring"):
            pa_tbl = _part_a_row_table(row, manifest_row)
            if pa_tbl is not None:
                with logtree.scope_header("Part A — metadata-reading per field"):
                    logtree.table_from_dict(pa_tbl, caption="Part A correctness")
            else:
                logtree.log_text("Part A: (no parsed Part A to score)")

            with logtree.scope_header("Part C — stage-by-stage"):
                logtree.table_from_dict(_verdict_table(row, tc), caption="Stage outcomes")

            with logtree.scope_header("Error categories"):
                err_tbl: dict[str, Any] = {
                    "error_category (format)": row.get("error_category", "—"),
                    "value_errors":            ", ".join(row.get("value_errors") or []) or "(none)",
                }
                logtree.table_from_dict(err_tbl, caption="Parser + value errors")

        # -------- Tokens --------
        with logtree.scope_header("Tokens & run info"):
            logtree.table_from_dict(_token_table(row), caption="Token counts")

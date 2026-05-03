"""Generate a single self-contained `benchmark_visualization.tex` for Overleaf.

Embodies each prompt and raw model output inline inside ``lstlisting`` blocks (no
external ``.txt``). If text accidentally contains the substring ``\\end{lstlisting}``,
it is split across chained listings so LaTeX still compiles.

For the **second-rollout** prompt, the shared ``prompts.py`` system text is not
repeated: it is shown as ``\{general\_prompt\_block\}`` with a footnote pointing
to the general prompt listing. Only the second-trial addendum and user message
(including embedded JSON) appear in the listing body.

Literal two-character sequences ``\\n`` / ``\\r`` in that listing are still
unescaped to real newlines before writing the TeX.

``rawouttxt`` listings use ``escapeinside={«}{»}`` so Part B reasoning fields match expert
\texttt{.docx} highlight segments (\texttt{FF0000}, \texttt{FFFF00}, \texttt{00FF00}; black for unshaded).

  python -m viz.generate_benchmark_visualization_tex

Writes ``temporary_files/benchmark_visualization.tex`` (gitignored dir).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import prompts as prompts_mod  # noqa: E402

from viz._analyze_llm_grading_docx_highlights import (  # noqa: E402
    per_model_reasoning_color_segments_in_doc_order,
)
from viz.build_run_folder import _load_jsonl, _reconstruct_prompts  # noqa: E402
from viz.build_visualization_bundle import MANIFEST_PATH, OID_TARGET, RUNS  # noqa: E402

TEX_PATH = PROJECT_ROOT / "temporary_files" / "benchmark_visualization.tex"

LST_END = r"\end{lstlisting}"


def _slug_label(label: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", label.strip()).strip("-").lower()
    return s or "model"


def _unescape_literal_newlines(s: str) -> str:
    """Turn literal ``\\n`` / ``\\r`` (two-char escapes) into real newlines."""
    if not s:
        return s
    return s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")


def _replace_unicode_dashes(s: str) -> str:
    """ASCII-safe dashes for listings/pdflatex: unicode dashes and LaTeX ``0--5`` pairs."""
    if not s:
        return s
    s = s.replace("\u2014", " - ")
    for ch in (
        "\u2013",
        "\u2212",
        "\u2010",
        "\u2011",
        "\u2012",
        "\u2015",
    ):
        s = s.replace(ch, "-")
    # Prompt source uses LaTeX-style en-dash as two hyphens (e.g. rubric "0--5").
    s = re.sub(r"(\d)--(\d)", r"\1-\2", s)
    while "  -  " in s:
        s = s.replace("  -  ", " - ")
    return s


def _normalize_second_rollout_for_tex(s: str) -> str:
    """Listing-friendly second-rollout text: ASCII dashes; unescape embedded JSON quotes/paths."""
    if not s:
        return s
    s = _replace_unicode_dashes(s)
    s = s.replace('\\"', '"')
    pair = "\\\\"
    while pair in s:
        s = s.replace(pair, "\\")
    return s


def _embed_lstlisting(text: str, style: str = "prompttxt") -> str:
    """Wrap UTF-8 text in lstlisting; chain environments if `text` contains LST_END."""
    parts = text.split(LST_END)
    inner: list[str] = []
    for i, part in enumerate(parts):
        inner.append(part)
        if i < len(parts) - 1:
            inner.append(LST_END + f"\n\\begin{{lstlisting}}[style={style}]")
    body = "".join(inner)
    return f"\\begin{{lstlisting}}[style={style}]\n{body}\n{LST_END}"


_PL_LEAD = "<<<VIZDOCX_PL_LEAD>>>"
_PL_ALT = "<<<VIZDOCX_PL_ALT>>>"

_TEX_CAT = {
    "red": "hlred",
    "yellow": "hlyellow",
    "green": "hlgreen",
    "unhighlighted": "black",
}


def _tex_escape_listings_escape(s: str) -> str:
    """Escape TeX specials inside lstlisting ``escapeinside`` regions."""
    out: list[str] = []
    for ch in s:
        if ch == "\\":
            out.append("\\textbackslash{}")
        elif ch == "{":
            out.append("\\{")
        elif ch == "}":
            out.append("\\}")
        elif ch == "%":
            out.append("\\%")
        elif ch == "#":
            out.append("\\#")
        elif ch == "$":
            out.append("\\$")
        elif ch == "^":
            out.append("\\textasciicircum{}")
        elif ch == "_":
            out.append("\\_")
        elif ch == "&":
            out.append("\\&")
        elif ch == "~":
            out.append("\\textasciitilde{}")
        else:
            out.append(ch)
    return "".join(out)


def _segments_to_colored_tex(segments: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for text, cat in segments:
        norm = text.replace("\r\n", "\n").replace("\r", "\n")
        esc = _tex_escape_listings_escape(norm)
        esc = esc.replace("\n", "\\newline\n")
        col = _TEX_CAT.get(cat, "black")
        parts.append(f"\\textcolor{{{col}}}{{{esc}}}")
    return "".join(parts)


def _brace_match_end(s: str, start: int) -> int | None:
    """Matching ``}`` for JSON object starting at ``start`` (respects quoted strings)."""
    if start >= len(s) or s[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    j = start
    while j < len(s):
        c = s[j]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return j
        j += 1
    return None


def _find_json_object_span(body: str) -> tuple[int, int] | None:
    """Locate the benchmark JSON object (contains ``\"Part A\"``) anywhere in CoT / fenced text."""
    for m in re.finditer(r'\{\s*"Part A"\s*:', body):
        start = m.start()
        end = _brace_match_end(body, start)
        if end is None:
            continue
        try:
            json.loads(body[start : end + 1])
            return start, end
        except json.JSONDecodeError:
            continue
    return None


def _dump_obj_with_part_b_highlights(obj: dict, seg: dict) -> str:
    """Pretty-print JSON with Part B reasoning placeholders replaced by colored TeX."""
    obj = json.loads(json.dumps(obj))
    pb = obj.get("Part B")
    if not isinstance(pb, dict):
        return json.dumps(obj, indent=2, ensure_ascii=False)
    if (
        "leading_interpretation_and_support" not in pb
        or "alternative_analysis" not in pb
    ):
        return json.dumps(obj, indent=2, ensure_ascii=False)
    lead_tex = _segments_to_colored_tex(seg.get("leading_interpretation_and_support") or [])
    alt_tex = _segments_to_colored_tex(seg.get("alternative_analysis") or [])
    pb["leading_interpretation_and_support"] = _PL_LEAD
    pb["alternative_analysis"] = _PL_ALT
    dumped = json.dumps(obj, indent=2, ensure_ascii=False)
    dumped = dumped.replace(json.dumps(_PL_LEAD), "«" + lead_tex + "»")
    dumped = dumped.replace(json.dumps(_PL_ALT), "«" + alt_tex + "»")
    return dumped


def _inject_reasoning_into_raw_body(body: str, seg: dict | None) -> str:
    """Inject expert-colored Part B strings; supports bare JSON, ```json fences, and leading CoT."""
    if not seg:
        return body
    span = _find_json_object_span(body)
    if span:
        s, e = span
        chunk = body[s : e + 1]
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            return body
        return body[:s] + _dump_obj_with_part_b_highlights(obj, seg) + body[e + 1 :]
    try:
        obj = json.loads(body.strip())
    except json.JSONDecodeError:
        return body
    return _dump_obj_with_part_b_highlights(obj, seg)


def _split_meta_body(combined: str) -> tuple[str, str]:
    sep = "\n\n"
    idx = combined.find(sep)
    if idx != -1 and combined.startswith("(model="):
        return combined[: idx + len(sep)], combined[idx + len(sep) :]
    return "", combined


def main() -> None:
    manifest = pd.read_csv(MANIFEST_PATH, low_memory=False)
    mby = manifest.set_index("oid")
    if OID_TARGET not in mby.index:
        raise SystemExit(f"missing {OID_TARGET} in manifest")
    mrow = mby.loc[OID_TARGET]

    sys_g, usr_g = _reconstruct_prompts(mrow, OID_TARGET, "prompts")
    prompt_general = _replace_unicode_dashes(
        "=== SYSTEM (prompts.py) ===\n\n"
        + sys_g
        + "\n\n=== USER ===\n\n"
        + usr_g
    )

    import importlib

    ab_path = (
        PROJECT_ROOT
        / "data_second_roll_out_ablation"
        / "metadata"
        / "gpt54_high_n35.csv"
    )
    second_rollout_tex_body: str
    second_rollout_footnotetext: str = ""
    if ab_path.is_file():
        ab = pd.read_csv(ab_path, low_memory=False)
        ex_oid = "ZTF26aargnnc"
        if ex_oid not in set(ab["oid"].astype(str)):
            ex_oid = str(ab["oid"].iloc[0])
        row_ab = ab[ab["oid"] == ex_oid].iloc[0]
        mod = importlib.import_module("prompts_second_roll_out_ablation")
        sys_s = mod.SYSTEM_PROMPT
        meta = mod.manifest_row_to_metadata(row_ab)
        usr_s = mod.build_user_prompt(ex_oid, meta)
        base_sys = prompts_mod.SYSTEM_PROMPT.strip()
        use_placeholder = (
            sys_s.startswith(base_sys)
            and sys_s[len(base_sys) :] == mod.SECOND_ROLL_ADDENDUM
        )
        if use_placeholder:
            listing_only = (
                mod.SECOND_ROLL_ADDENDUM + "\n\n=== USER ===\n\n" + usr_s
            )
        else:
            listing_only = (
                "=== SYSTEM ===\n\n"
                + sys_s
                + "\n\n=== USER ===\n\n"
                + usr_s
            )
        prompt_second = _normalize_second_rollout_for_tex(
            _unescape_literal_newlines(listing_only)
        )
        if use_placeholder:
            second_rollout_tex_body = (
                r"\noindent\texttt{\{general\_prompt\_block\}}\footnotemark"
                r"\vspace{0.6em}"
                "\n"
                + _embed_lstlisting(prompt_second, "prompttxt")
            )
            second_rollout_footnotetext = (
                r"\footnotetext{Same text as the \texttt{prompts.py} \textbf{system} message in the "
                r"\textit{General benchmark prompt} listing above (omitted here).}"
            )
        else:
            second_rollout_tex_body = _embed_lstlisting(prompt_second, "prompttxt")
    else:
        prompt_second = (
            f"[missing {ab_path.relative_to(PROJECT_ROOT)} - regenerate second-rollout metadata]"
        )
        second_rollout_tex_body = _embed_lstlisting(prompt_second, "prompttxt")

    raw_by_prefix: dict[str, str] = {}
    for i, (label, rel_run) in enumerate(RUNS):
        slug = _slug_label(label)
        prefix = f"{i + 1:02d}_{slug}"
        jsonl = PROJECT_ROOT / rel_run / "run.jsonl"
        if not jsonl.is_file():
            raw_by_prefix[prefix] = f"[missing run.jsonl: {rel_run}]"
            continue
        rows = _load_jsonl(jsonl)
        row = next((r for r in rows if r.get("oid") == OID_TARGET), None)
        if row is None:
            raw_by_prefix[prefix] = f"[no row for {OID_TARGET} in {rel_run}]"
            continue
        raw = row.get("raw_text") or ""
        meta_line = (
            f"(model={row.get('model', '?')}, "
            f"n_prompt_tokens={row.get('n_prompt_tokens', '?')}, "
            f"n_answer_tokens={row.get('n_answer_tokens', '?')})\n\n"
        )
        raw_by_prefix[prefix] = _replace_unicode_dashes(meta_line + raw)

    grading_docx = (
        PROJECT_ROOT / "temporary_files" / "LLM Answer Grading ZTF26aargnnp.docx"
    )
    if not grading_docx.is_file():
        grading_docx = PROJECT_ROOT / "LLM Answer Grading ZTF26aargnnp.docx"

    reasoning_segments: list[dict[str, list[tuple[str, str]]] | None] = [
        None
    ] * len(RUNS)
    if grading_docx.is_file():
        try:
            seg_blocks = per_model_reasoning_color_segments_in_doc_order(grading_docx)
            for i in range(len(RUNS)):
                reasoning_segments[i] = seg_blocks[i] if i < len(seg_blocks) else None
        except (OSError, ValueError, KeyError, RuntimeError):
            reasoning_segments = [None] * len(RUNS)

    lines: list[str] = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[a4paper,margin=0.85in]{geometry}",
        r"\usepackage{graphicx}",
        r"\usepackage{xcolor}",
        r"\definecolor{hlred}{HTML}{FF0000}",
        r"\definecolor{hlyellow}{HTML}{DAA520}",
        r"\definecolor{hlgreen}{HTML}{00FF00}",
        r"\usepackage{listings}",
        r"\usepackage{titlesec}",
        r"\titleformat{\section}{\normalfont\Large\bfseries\color{teal!70!black}}{\thesection}{0.6em}{}",
        r"\titleformat{\subsection}{\normalfont\large\bfseries\color{blue!60!black}}{\thesubsection}{0.5em}{}",
        r"\usepackage{footnote}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\usepackage[most]{tcolorbox}",
        r"\tcbuselibrary{breakable,listings}",
        "",
        r"\lstdefinestyle{prompttxt}{",
        r"  basicstyle=\ttfamily\footnotesize,",
        r"  breaklines=true,",
        r"  breakatwhitespace=false,",
        r"  columns=fullflexible,",
        r"  keepspaces=true,",
        r"  frame=none,",
        r"}",
        "",
        r"\lstdefinestyle{rawouttxt}{",
        r"  basicstyle=\ttfamily\footnotesize,",
        r"  breaklines=true,",
        r"  breakatwhitespace=false,",
        r"  columns=fullflexible,",
        r"  keepspaces=true,",
        r"  frame=none,",
        r"  escapeinside={«}{»},",
        r"}",
        "",
        r"\tcbset{",
        r"  chatturn/.style={",
        r"    boxrule=0.4pt,",
        r"    arc=2pt,",
        r"    left=6pt,",
        r"    right=6pt,",
        r"    top=2pt,",
        r"    bottom=4pt,",
        r"    titlerule=0pt,",
        r"    toptitle=0.5mm,",
        r"    fonttitle=\sffamily\bfseries\small,",
        r"  },",
        r"  chatblue/.style={",
        r"    colback=blue!4!white,",
        r"    colframe=blue!50!black,",
        r"    colbacktitle=blue!50!black,",
        r"    coltitle=white,",
        r"  },",
        r"  chatgreen/.style={",
        r"    colback=green!4!white,",
        r"    colframe=green!45!black,",
        r"    colbacktitle=green!40!black,",
        r"    coltitle=white,",
        r"  },",
        r"  chatgrey/.style={",
        r"    colback=gray!8,",
        r"    colframe=gray!55,",
        r"    colbacktitle=gray!55,",
        r"    coltitle=white,",
        r"  },",
        r"}",
        "",
        r"\NewTColorBox{chatmsg}{O{blue} m O{}}{",
        r"  chatturn,",
        r"  chat#1,",
        r"  title={#2},",
        r"  #3",
        r"}",
        r"\makesavenoteenv{chatmsg}",
        "",
        r"\title{\textbf{Benchmark prompts \& model outputs (single datapoint)}}",
        r"\author{(generated by \texttt{viz.generate\_benchmark\_visualization\_tex})}",
        r"\date{}",
        "",
        r"\begin{document}",
        r"\maketitle",
        "",
        r"\begin{abstract}",
        r"Self-contained \texttt{.tex}: prompts and raw outputs are inlined in \texttt{lstlisting} "
        r"environments (no external snippet files). Compile with \texttt{pdflatex} or "
        r"\texttt{xelatex} if outputs contain non-Latin Unicode.",
        r"\end{abstract}",
        "",
        r"\section{Prompts}",
        "",
        r"\begin{chatmsg}[grey]{General benchmark prompt (\texttt{prompts.py})}[breakable]",
        _embed_lstlisting(prompt_general, "prompttxt"),
        r"\end{chatmsg}",
        "",
        rf"\begin{{chatmsg}}[grey]{{Second-rollout ablation prompt (\texttt{{prompts\_second\_roll\_out\_ablation.py}})}}[breakable]",
        second_rollout_tex_body,
        r"\end{chatmsg}",
        second_rollout_footnotetext,
        "",
        r"\clearpage",
        r"\section{Raw model outputs (\texttt{raw\_text} from each run's \texttt{run.jsonl})}",
        r"\noindent\small\textit{Part B reasoning fields \texttt{leading\_interpretation\_and\_support} and "
        r"\texttt{alternative\_analysis} use expert highlights from \texttt{LLM Answer Grading ZTF26aargnnp.docx} "
        r"(OOXML fills \texttt{FF0000}, \texttt{FFFF00}, \texttt{00FF00}; unshaded runs render black). "
        r"Same block order as this section.}",
        "",
        r"\begin{figure}[htbp]",
        r"\centering",
        rf"\includegraphics[width=0.88\textwidth]{{figure/{OID_TARGET}.png}}",
        rf"\caption{{Science--Reference--Difference montage for \texttt{{{OID_TARGET}}} (Overleaf: \texttt{{figure/{OID_TARGET}.png}}).}}",
        r"\end{figure}",
        "",
    ]

    for i, (label, _) in enumerate(RUNS):
        slug = _slug_label(label)
        prefix = f"{i + 1:02d}_{slug}"
        col = "blue" if i % 2 == 0 else "green"
        safe_title = label.replace("&", r"\&")
        combined = raw_by_prefix[prefix]
        meta, body = _split_meta_body(combined)
        seg = reasoning_segments[i]
        if meta:
            body_txt = meta + _inject_reasoning_into_raw_body(body, seg)
        else:
            body_txt = _inject_reasoning_into_raw_body(combined, seg)
        lines.append(rf"\begin{{chatmsg}}[{col}]{{{safe_title} --- raw output}}[breakable]")
        lines.append(_embed_lstlisting(body_txt, "rawouttxt"))
        lines.append(r"\end{chatmsg}")
        lines.append("")
        if (i + 1) % 3 == 0:
            lines.append(r"\clearpage")

    lines.append(r"\end{document}")
    TEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {TEX_PATH.relative_to(PROJECT_ROOT)} (single file; second-rollout: literal \\\\n → newline)")


if __name__ == "__main__":
    main()

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

  python -m viz.generate_benchmark_visualization_tex

Writes (repo root): ``benchmark_visualization.tex`` only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import prompts as prompts_mod  # noqa: E402

from viz.build_run_folder import _load_jsonl, _reconstruct_prompts  # noqa: E402
from viz.build_visualization_bundle import MANIFEST_PATH, OID_TARGET, RUNS  # noqa: E402

TEX_PATH = PROJECT_ROOT / "benchmark_visualization.tex"

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
        note = (
            f"(Example OID `{ex_oid}` - priors not bundled for `{OID_TARGET}` in-repo; "
            "same prompt recipe as full second-rollout ablation.)\n\n"
        )
        base_sys = prompts_mod.SYSTEM_PROMPT.strip()
        use_placeholder = (
            sys_s.startswith(base_sys)
            and sys_s[len(base_sys) :] == mod.SECOND_ROLL_ADDENDUM
        )
        if use_placeholder:
            listing_only = (
                note
                + mod.SECOND_ROLL_ADDENDUM
                + "\n\n=== USER ===\n\n"
                + usr_s
            )
        else:
            listing_only = (
                note
                + "=== SYSTEM ===\n\n"
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

    lines: list[str] = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[a4paper,margin=0.85in]{geometry}",
        r"\usepackage{xcolor}",
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
        r"\author{\texttt{ZTF26aargnnp} \quad (generated by \texttt{viz.generate\_benchmark\_visualization\_tex})}",
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
        rf"\begin{{chatmsg}}[grey]{{General benchmark prompt (\texttt{{prompts.py}}) --- \texttt{{{OID_TARGET}}}}}[breakable]",
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
        "",
    ]

    colors = ["blue", "green"]
    for i, (label, _) in enumerate(RUNS):
        slug = _slug_label(label)
        prefix = f"{i + 1:02d}_{slug}"
        col = colors[i % 2]
        safe_title = label.replace("&", r"\&")
        body_txt = raw_by_prefix[prefix]
        lines.append(rf"\begin{{chatmsg}}[{col}]{{{safe_title} --- raw output}}[breakable]")
        lines.append(_embed_lstlisting(body_txt, "prompttxt"))
        lines.append(r"\end{chatmsg}")
        lines.append("")
        if (i + 1) % 3 == 0:
            lines.append(r"\clearpage")

    lines.append(r"\end{document}")
    TEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {TEX_PATH.relative_to(PROJECT_ROOT)} (single file; second-rollout: literal \\\\n → newline)")


if __name__ == "__main__":
    main()

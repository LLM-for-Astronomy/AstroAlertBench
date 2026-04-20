"""Visualization + run-folder utilities for VLM benchmark runs.

Modules:
  html_report      — per-datapoint HTML via tinker_cookbook.utils.logtree
  plots            — per-run matplotlib charts (PNG)
  enriched_report  — full-metrics markdown report
  build_run_folder — end-to-end orchestrator
  index            — maintain runs/index.md

Typical entry point:

    from viz.build_run_folder import build_run_folder
    build_run_folder(
        jsonl_path="results/fewshot_kimi_think_newparser.jsonl",
        manifest_path="data/manifest_fewshot.csv",
        model_name="moonshotai/Kimi-K2.5",
        out_root="runs",
    )
"""


# Patch tinker_cookbook.utils.logtree's `open` to always use UTF-8 on Windows.
# logtree writes HTML files with a bare `open(path, "w")` which defaults to the
# system encoding (gbk on Chinese Windows), tripping on any non-GBK character
# that appears in a model answer. Patching the module-level `open` reference
# applies only to logtree's own file I/O without affecting anything else.
def _patch_logtree_utf8() -> None:
    import builtins
    from tinker_cookbook.utils import logtree as _lt

    _original_open = builtins.open

    def _utf8_open(file, mode="r", *args, **kwargs):
        if "b" not in mode and "encoding" not in kwargs:
            kwargs["encoding"] = "utf-8"
        return _original_open(file, mode, *args, **kwargs)

    _lt.open = _utf8_open  # type: ignore[attr-defined]


_patch_logtree_utf8()
del _patch_logtree_utf8

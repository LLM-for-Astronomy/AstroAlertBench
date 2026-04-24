"""Pull comparison metrics for the new Gemini-2.5 / Opus 4.7-nothink runs."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RUNS = {
    "gemini-2.5-pro high (PARTIAL)":
        "runs/20260423-2204-gemini25-pro-high-benchmark-full",
    "gemini-2.5-flash none":
        "runs/20260423-2110-gemini25-flash-none-benchmark-full",
    "claude-opus-4-7 nothink":
        "runs/20260423-1200-opus47-nothink-benchmark-full",
    "claude-opus-4-7 think (logged before)":
        "runs/20260423-0942-opus47-think-benchmark-full",
    "gpt-5.4 high":
        "runs/20260421-2024-gpt-5.4-high-benchmark-full",
    "gpt-5.4 none":
        "runs/20260421-2032-gpt-5.4-none-benchmark-full",
    "kimi-k2.5":
        "runs/20260420-1226-kimi-k25-benchmark-full",
}


def get_path(metrics, *keys, default=None):
    cur = metrics
    for k in keys:
        if cur is None:
            return default
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur if cur is not None else default


def fmt_pct(v):
    if v is None:
        return "  -  "
    try:
        return f"{100 * float(v):5.2f}%"
    except (ValueError, TypeError):
        return f"{v}"


def fmt_msrs(v):
    if v is None:
        return "  -  "
    try:
        return f"{float(v):4.2f}/5"
    except (ValueError, TypeError):
        return f"{v}"


def _mean_jsonl_field(jsonl_path: Path, field: str) -> float | None:
    if not jsonl_path.is_file():
        return None
    total = 0.0
    n = 0
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            v = rec.get(field)
            if isinstance(v, (int, float)):
                total += v
                n += 1
    return total / n if n else None


def fmt_int(v):
    if v is None:
        return "  -  "
    try:
        return f"{int(v):>6}"
    except (ValueError, TypeError):
        return f"{v}"


def main():
    rows = []
    for label, rel in RUNS.items():
        mpath = PROJECT_ROOT / rel / "metrics.json"
        if not mpath.is_file():
            print(f"!! missing {mpath}")
            continue
        m = json.loads(mpath.read_text(encoding="utf-8"))

        n_total = m.get("n_examples")
        n_parsed = m.get("json_parseable")
        five_acc = m.get("part_c_final_5class_accuracy")
        msrs = m.get("part_b_msrs")  # 0..5 scale, not %
        per_cls = m.get("per_class_accuracy") or {}
        cal_gap = get_path(m, "part_bc_confidence_accuracy", "calibration_gap")
        avg_out = get_path(m, "output_tokens", "mean")
        run_jsonl = mpath.parent / "run.jsonl"
        avg_in = _mean_jsonl_field(run_jsonl, "n_prompt_tokens")
        avg_reason = _mean_jsonl_field(run_jsonl, "n_reasoning_tokens")
        rows.append({
            "label": label,
            "n_total": n_total,
            "n_parsed": n_parsed,
            "five_acc": five_acc,
            "msrs": msrs,
            "per_cls": per_cls,
            "cal_gap": cal_gap,
            "avg_in": avg_in,
            "avg_out": avg_out,
            "avg_reason": avg_reason,
        })

    classes = ["asteroid", "AGN", "bogus", "VS", "SN"]

    per_cls_hdr = "  ".join(f"{c:>7}" for c in classes)
    header = (
        f"{'run':<42}  {'n':>5}  {'parsed':>6}  "
        f"{'5cls':>7}  {'MSRS':>6}  "
        f"{per_cls_hdr}  "
        f"{'cal_gap':>7}  {'in tok':>7}  {'out tok':>7}  {'reason':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        per_cls = r["per_cls"]
        per_str = "  ".join(f"{fmt_pct(per_cls.get(c)):>7}" for c in classes)
        print(
            f"{r['label']:<42}  "
            f"{fmt_int(r['n_total']):>5}  "
            f"{fmt_int(r['n_parsed']):>6}  "
            f"{fmt_pct(r['five_acc']):>7}  "
            f"{fmt_msrs(r['msrs']):>6}  "
            f"{per_str}  "
            f"{fmt_pct(r['cal_gap']):>7}  "
            f"{fmt_int(r['avg_in']):>7}  "
            f"{fmt_int(r['avg_out']):>7}  "
            f"{fmt_int(r['avg_reason']):>7}"
        )


if __name__ == "__main__":
    main()

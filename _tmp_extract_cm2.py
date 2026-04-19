"""Extract 5-class confusion matrices from 4 new evaluation JSONL files."""
from __future__ import annotations
import json, re
from collections import Counter
from pathlib import Path
from typing import Any

CLASSES_5 = ["SN", "AGN", "VS", "asteroid", "bogus"]
FILES = [
    ("fewshot_kimi_oldbackup.jsonl",     "Kimi old_backup"),
    ("fewshot_kimi_newprompt.jsonl",      "Kimi new_prompt"),
    ("fewshot_qwen235_newprompt.jsonl",   "Qwen235 new_prompt"),
    ("fewshot_qwen30_newprompt.jsonl",    "Qwen30 new_prompt"),
]

def _norm_str(val):
    if val is None: return None
    s = str(val).strip()
    return s if s else None

def normalize_stage1(val):
    s = _norm_str(val)
    if s is None: return None
    low = s.lower().replace(" ", "_")
    if low in ("artifact", "artefact"): return "artifact"
    if low in ("real_object", "real"): return "real_object"
    return None

def normalize_stage2(val):
    s = _norm_str(val)
    if s is None: return None
    low = s.lower().replace(" ", "_")
    if low in ("n/a", "na", "none", "null"): return "N/A"
    if "solar" in low: return "solar_system"
    if "astrophys" in low: return "astrophysical"
    return None

def normalize_stage3_label(val):
    s = _norm_str(val)
    if s is None: return None
    low = s.lower().replace(" ", "_")
    if low in ("n/a", "na", "none", "null"): return "N/A"
    if low in ("supernova", "sn") or "supernova" in low: return "supernova"
    if low in ("variable_star", "vs") or "variable" in low: return "variable_star"
    if low in ("agn",) or "agn" in low or "active galactic" in low.replace("_", " "): return "AGN"
    return None

def stages_to_final_class(s1, s2, s3):
    if s1 == "artifact": return "bogus"
    if s1 == "real_object":
        if s2 == "solar_system": return "asteroid"
        if s2 == "astrophysical":
            if s3 == "supernova": return "SN"
            if s3 == "AGN": return "AGN"
            if s3 == "variable_star": return "VS"
    return None

def extract_json_object(text):
    if not text or not text.strip(): return None
    s = text.strip()
    s = re.sub(r"<think>[\s\S]*?</think>", "", s).strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
    if fence: s = fence.group(1).strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError: pass
    depth = 0; start = -1
    for idx, ch in enumerate(s):
        if ch == "{":
            if depth == 0: start = idx
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    obj = json.loads(s[start:idx+1])
                    if isinstance(obj, dict): return obj
                except json.JSONDecodeError: pass
                start = -1
    return None

def get_predicted_class(row):
    parsed = row.get("parsed")
    if parsed is None: parsed = extract_json_object(row.get("raw_text", ""))
    if parsed is None: return None
    part_c = parsed.get("Part C") or parsed.get("part_c")
    if not isinstance(part_c, dict): return None
    ps1 = normalize_stage1(part_c.get("stage1"))
    ps2 = normalize_stage2(part_c.get("stage2"))
    ps3 = normalize_stage3_label(part_c.get("stage3"))
    return stages_to_final_class(ps1, ps2, ps3)

def main():
    results_dir = Path(__file__).parent / "results"
    for fname, label in FILES:
        path = results_dir / fname
        if not path.exists():
            print(f"\n*** SKIPPED {fname} ***"); continue
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        cm = {c: Counter() for c in CLASSES_5}
        for r in rows:
            if r.get("error"): continue
            tc = r.get("target_class")
            if tc not in CLASSES_5: continue
            pred = get_predicted_class(r)
            if pred and pred in CLASSES_5: cm[tc][pred] += 1
            else: cm[tc]["UNPARSED"] += 1
        print(f"\n{'='*60}\n  {fname}  ({label})\n{'='*60}")
        pred_cols = CLASSES_5[:]
        if any(cm[c].get("UNPARSED",0)>0 for c in CLASSES_5): pred_cols.append("UNPARSED")
        header = f"{'True<Pred':<10}" + "".join(f"  {c:>8}" for c in pred_cols) + "   total"
        print(header); print("-"*len(header))
        total_correct = total_all = 0
        for tc in CLASSES_5:
            row_str = f"{tc:<10}"
            rt = 0
            for c in pred_cols: v = cm[tc].get(c,0); row_str += f"  {v:>8}"; rt += v
            row_str += f"  {rt:>5}"
            total_correct += cm[tc].get(tc,0); total_all += rt
            print(row_str)
        print(f"\nAccuracy: {total_correct}/{total_all} = {total_correct/total_all:.1%}" if total_all else "")

if __name__ == "__main__": main()

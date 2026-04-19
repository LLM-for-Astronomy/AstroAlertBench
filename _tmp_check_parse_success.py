"""Check parse success rate and what gets lost."""
import json, re
from pathlib import Path

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

results_dir = Path("results")
for jsonl in sorted(results_dir.glob("fewshot_*.jsonl")):
    total = ok = has_partc = 0
    fail_oids = []
    for line in open(jsonl, encoding="utf-8"):
        row = json.loads(line)
        if row.get("error"): continue
        total += 1
        parsed = row.get("parsed")
        if parsed is None:
            parsed = extract_json_object(row.get("raw_text", ""))
        if parsed is not None:
            ok += 1
            pc = parsed.get("Part C") or parsed.get("part_c")
            if pc: has_partc += 1
        else:
            fail_oids.append(row.get("oid", "?"))

    if total == ok and ok == has_partc:
        status = "ALL OK"
    else:
        status = f"ISSUES"
    print(f"{jsonl.name:40s}  total={total}  parsed={ok}  has_partC={has_partc}  {status}")
    if fail_oids:
        print(f"  FAILED to parse: {fail_oids[:5]}")

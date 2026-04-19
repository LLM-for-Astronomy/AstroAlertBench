import json, sys
sys.path.insert(0, ".")
from evaluate import extract_json_object

with open("results/fewshot_qwen35_4b_test.jsonl", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        if r.get("error"):
            print(f"{r['oid']}: ERROR - {r['error'][:80]}")
            continue
        raw = r.get("raw_text", "")
        parsed = extract_json_object(raw)
        has_pc = bool(parsed and (parsed.get("Part C") or parsed.get("part_c")))
        braces = raw.count("{")
        print(f"{r['oid']}: len={len(raw)}, braces={braces}, parsed={parsed is not None}, Part_C={has_pc}")
        if not parsed:
            print(f"  First 300: {raw[:300]}")
        else:
            pc = parsed.get("Part C") or parsed.get("part_c")
            print(f"  Part C: {pc}")

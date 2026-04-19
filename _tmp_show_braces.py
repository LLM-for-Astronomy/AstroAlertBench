import json, re
from pathlib import Path

f = Path("results/fewshot_qwen35.jsonl")
with open(f, encoding="utf-8") as fh:
    for i, line in enumerate(fh):
        if i >= 3: break
        row = json.loads(line)
        raw = row.get("raw_text", "")
        oid = row.get("oid", "?")
        brace_count = raw.count("{")
        has_part_c = "Part C" in raw or "part_c" in raw
        has_stage1 = "stage1" in raw or "\"stage1\"" in raw
        # Find all { positions
        positions = [m.start() for m in re.finditer(r'\{', raw)]
        print(f"{oid}: len={len(raw)}, braces={brace_count}, has_Part_C={has_part_c}, has_stage1={has_stage1}")
        if positions:
            for p in positions[:5]:
                print(f"  brace at pos {p}: ...{raw[max(0,p-20):p+80]}...")
        print()

import json
from pathlib import Path

f = Path("results/fewshot_qwen35.jsonl")
with open(f, encoding="utf-8") as fh:
    for i, line in enumerate(fh):
        if i >= 2: break
        row = json.loads(line)
        raw = row.get("raw_text", "")
        print(f"=== {row.get('oid')} ===")
        print(f"Length: {len(raw)} chars")
        print(f"First 500 chars:\n{raw[:500]}")
        print(f"\nLast 500 chars:\n{raw[-500:]}")
        print()

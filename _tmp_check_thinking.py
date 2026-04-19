"""Check all JSONL result files for thinking/reasoning patterns in raw_text."""
import json, re
from pathlib import Path
from collections import Counter

patterns = [
    (r"<think>", "<think>"),
    (r"</think>", "</think>"),
    (r"<thinking>", "<thinking>"),
    (r"</thinking>", "</thinking>"),
    (r"<reasoning>", "<reasoning>"),
    (r"</reasoning>", "</reasoning>"),
    (r"<reflection>", "<reflection>"),
    (r"<内部思考>", "Chinese thinking tag"),
    (r"Let me (think|analyze|reason)", "Let me think/analyze"),
    (r"^(I'll|I will|Let me|First,|Okay|Alright)", "Conversational preamble"),
]

results_dir = Path("results")
for jsonl in sorted(results_dir.glob("fewshot_*.jsonl")):
    counts = Counter()
    total = 0
    no_json = 0
    sample_nonjson = []
    for line in open(jsonl, encoding="utf-8"):
        row = json.loads(line)
        if row.get("error"):
            continue
        raw = row.get("raw_text", "")
        if not raw:
            continue
        total += 1
        for pat, label in patterns:
            if re.search(pat, raw, re.IGNORECASE):
                counts[label] += 1

        # Check if raw_text starts with non-JSON (thinking before JSON)
        stripped = raw.strip()
        if stripped and stripped[0] != '{':
            # Not starting with JSON
            fence = re.search(r"```(?:json)?", stripped)
            think = re.search(r"<think>", stripped, re.IGNORECASE)
            if not fence and not think:
                no_json += 1
                if len(sample_nonjson) < 3:
                    first_100 = stripped[:150].replace('\n', ' ')
                    sample_nonjson.append((row.get("oid", "?"), first_100))

    print(f"\n{'='*60}")
    print(f"  {jsonl.name}  ({total} examples)")
    print(f"{'='*60}")
    if counts:
        for label, c in counts.most_common():
            print(f"  {label}: {c}/{total}")
    else:
        print("  No thinking/reasoning patterns found")
    if no_json:
        print(f"  Outputs NOT starting with {{ or ```json or <think>: {no_json}/{total}")
        for oid, sample in sample_nonjson:
            print(f"    [{oid}]: {sample}...")

"""Validate the benchmark itself: every gold query must run, be non-trivial, and fit under 100 rows.

Usage: uv run python bench/check_gold.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

from csql.db import run_query

path = Path(__file__).parent / "questions.jsonl"
qs = [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]

problems = []
ids = Counter(q["id"] for q in qs)
problems += [f"{i}: duplicate id" for i, n in ids.items() if n > 1]

for q in qs:
    try:
        cols, rows = run_query(q["gold_sql"], max_rows=1000)
    except Exception as e:
        problems.append(f"{q['id']}: gold SQL fails: {str(e).splitlines()[0]}")
        continue
    if not rows:
        problems.append(f"{q['id']}: EMPTY result")
    elif len(rows) > 100:
        problems.append(f"{q['id']}: {len(rows)} rows (>100, agent LIMIT would break matching)")
    elif len(rows) == 1 and all(v in (0, None) for v in rows[0]):
        problems.append(f"{q['id']}: trivial result {rows[0]}")

print(Counter((q["level"], q["split"]) for q in qs))
print(f"{len(qs)} questions, {len(problems)} problems")
for p in problems:
    print(" -", p)
sys.exit(1 if problems else 0)

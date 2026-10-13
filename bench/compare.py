"""Aggregate bench/results/*.csv into bench/results/summary.md.

Usage: uv run python bench/compare.py
"""

import csv
from collections import defaultdict
from pathlib import Path

results = Path(__file__).parent / "results"
LEVELS = ["easy", "medium", "hard"]

# (model, config, split) -> list of runs; each run is a list of row dicts
groups: dict[tuple, list[list[dict]]] = defaultdict(list)
for f in sorted(results.glob("*__run*.csv")):
    model, config, split, _run = f.stem.split("__")
    with f.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if any(r.get("infra") == "1" for r in rows):
        print(f"SKIPPED {f.name}: contains API-error rows, re-run with --resume")
        continue
    groups[(model.replace("_", "/", 1), config, split)].append(rows)


def acc(rows: list[dict]) -> float:
    return sum(int(r["correct"]) for r in rows) / len(rows) if rows else float("nan")


lines = [
    "# Benchmark summary (execution accuracy)\n",
    "| Model | Config | Split | Easy | Medium | Hard | Overall | Runs | Avg latency (s) | Avg tokens | Avg retries |",
    "|---|---|---|---|---|---|---|---|---|---|---|",
]
for (model, config, split), runs in sorted(groups.items()):

    def cell(level: str | None, runs: list[list[dict]] = runs) -> str:
        vals = [acc([r for r in run if level is None or r["level"] == level]) for run in runs]
        m = sum(vals) / len(vals)
        if len(vals) > 1:
            return f"{m:.1%} ± {(max(vals) - min(vals)) / 2:.1%}"
        return f"{m:.1%}"

    flat = [r for run in runs for r in run]
    n = len(flat)
    lat = sum(float(r["latency_s"]) for r in flat) / n
    tok = sum(int(r["tokens"]) for r in flat) / n
    ret = sum(int(r["retries"]) for r in flat) / n
    lines.append(
        f"| {model} | {config} | {split} | {cell('easy')} | {cell('medium')} | {cell('hard')} | "
        f"{cell(None)} | {len(runs)} | {lat:.1f} | {tok:.0f} | {ret:.2f} |"
    )

(results / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

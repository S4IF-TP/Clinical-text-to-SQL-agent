"""Run the benchmark: execution accuracy of predicted vs gold SQL.

Usage: uv run python bench/run_eval.py --model openai/gpt-oss-120b --config baseline --split dev
Writes bench/results/<model>__<config>__<split>__run<k>.csv (one row per question).
"""

import argparse
import csv
import json
import time
from pathlib import Path

from csql.db import run_query
from csql.eval_utils import results_match
from csql.graph import ask

ROOT = Path(__file__).parent
FIELDS = [
    "id",
    "level",
    "split",
    "correct",
    "error",
    "pred_sql",
    "n_rows_pred",
    "n_rows_gold",
    "latency_s",
    "tokens",
    "retries",
    "validation_failures",
]


def load_questions(split: str, level: str | None, limit: int | None) -> list[dict]:
    qs = [
        json.loads(line)
        for line in (ROOT / "questions.jsonl").read_text("utf-8").splitlines()
        if line
    ]
    if split != "all":
        qs = [q for q in qs if q["split"] == split]
    if level:
        qs = [q for q in qs if q["level"] == level]
    return qs[:limit] if limit else qs


def evaluate(q: dict, model: str, config: str) -> dict:
    gold_cols, gold_rows = run_query(q["gold_sql"], max_rows=1000)
    t0 = time.perf_counter()
    try:
        state = ask(q["question"], model=model, config=config, with_answer=False)
        crash = None
    except Exception as e:  # LLM/API failure counts as incorrect, but is logged
        state, crash = {"trace": []}, f"{type(e).__name__}: {e}"
    latency = time.perf_counter() - t0

    trace = state.get("trace", [])
    pred_rows = state.get("rows", [])
    error = crash or state.get("error")
    correct = bool(not error and not state.get("refused") and results_match(pred_rows, gold_rows))
    return {
        "id": q["id"],
        "level": q["level"],
        "split": q["split"],
        "correct": int(correct),
        "error": (error or "").replace("\n", " ")[:300],
        "pred_sql": (state.get("sql") or "").replace("\n", " "),
        "n_rows_pred": len(pred_rows),
        "n_rows_gold": len(gold_rows),
        "latency_s": round(latency, 2),
        "tokens": sum(t.get("tokens", 0) for t in trace),
        "retries": sum(1 for t in trace if t.get("node") == "correct"),
        "validation_failures": sum(
            1 for t in trace if t.get("node") == "validate" and not t.get("ok", True)
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--config", default="baseline")
    p.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    p.add_argument("--level", choices=["easy", "medium", "hard"])
    p.add_argument("--limit", type=int)
    p.add_argument("--run", type=int, default=1, help="repeat index, for variance runs")
    args = p.parse_args()

    qs = load_questions(args.split, args.level, args.limit)
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    safe_model = args.model.replace("/", "_")
    out = out_dir / f"{safe_model}__{args.config}__{args.split}__run{args.run}.csv"

    rows = []
    for i, q in enumerate(qs, 1):
        r = evaluate(q, args.model, args.config)
        rows.append(r)
        print(
            f"[{i}/{len(qs)}] {q['id']} {q['level']:6} {'OK ' if r['correct'] else 'BAD'} {r['error'][:80]}"
        )
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    acc = sum(r["correct"] for r in rows) / max(len(rows), 1)
    print(
        f"\n{args.model} / {args.config} / {args.split}: {acc:.1%} ({sum(r['correct'] for r in rows)}/{len(rows)})"
    )
    print(f"Saved {out}")


if __name__ == "__main__":
    main()

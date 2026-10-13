"""Run the benchmark: execution accuracy of predicted vs gold SQL.

Usage: uv run python bench/run_eval.py --model openai/gpt-oss-120b --config baseline --split dev
Writes bench/results/<model>__<config>__<split>__run<k>.csv (one row per question).
"""

import argparse
import csv
import json
import re
import time
from pathlib import Path

from csql.db import run_query
from csql.eval_utils import results_match
from csql.graph import ask

ROOT = Path(__file__).parent
FIELDS = [
    "infra",
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


INFRA_RE = re.compile(
    r"^(RateLimitError|APIConnectionError|APITimeoutError|InternalServerError|APIStatusError|"
    r"BadRequestError|AuthenticationError|PermissionDeniedError|NotFoundError|ConflictError|"
    r"UnprocessableEntityError):"
)


def is_infra(row: dict) -> bool:
    """API/infrastructure failures are not model mistakes: they must be re-run, never scored."""
    return str(row.get("infra", "")) == "1" or bool(INFRA_RE.match(row.get("error", "")))


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
        "infra": int(crash is not None),
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
    p.add_argument("--resume", action="store_true", help="re-run only missing/infra-failed rows")
    args = p.parse_args()

    qs = load_questions(args.split, args.level, args.limit)
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    safe_model = args.model.replace("/", "_")
    out = out_dir / f"{safe_model}__{args.config}__{args.split}__run{args.run}.csv"

    done: dict[str, dict] = {}
    if args.resume and out.exists():
        with out.open(encoding="utf-8") as f:
            done = {r["id"]: r for r in csv.DictReader(f) if not is_infra(r)}
        print(f"resuming: {len(done)} clean rows kept")

    def save() -> None:
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore", restval="0")
            w.writeheader()
            w.writerows(by_id[q["id"]] for q in qs if q["id"] in by_id)

    by_id = dict(done)
    for i, q in enumerate(qs, 1):
        if q["id"] in done:
            continue
        r = evaluate(q, args.model, args.config)
        by_id[q["id"]] = r
        save()  # checkpoint after every question
        flag = "INFRA" if r["infra"] else ("OK " if r["correct"] else "BAD")
        print(f"[{i}/{len(qs)}] {q['id']} {q['level']:6} {flag} {r['error'][:80]}")
    rows = [by_id[q["id"]] for q in qs]
    save()
    n_infra = sum(is_infra(r) for r in rows)
    if n_infra:
        print(f"WARNING: {n_infra} rows hit API errors; re-run with --resume before using this run")

    acc = sum(int(r["correct"]) for r in rows) / max(len(rows), 1)
    print(
        f"\n{args.model} / {args.config} / {args.split}: {acc:.1%} ({sum(int(r['correct']) for r in rows)}/{len(rows)})"
    )
    print(f"Saved {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Re-run only API-failed/missing rows of the dev "both" ablation runs (needs Postgres up).
set -u
cd "$(dirname "$0")/.."
r() { PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python -m uv run python bench/run_eval.py --model "$1" --config "$2" --split dev --resume \
        > "bench/results/log_resume_$(echo "$1" | tr '/' '_')_$2.tmp" 2>&1; }
( r openai/gpt-oss-120b both ) &
( r openai/gpt-oss-20b both ) &
( r qwen/qwen3.8-27b both ) &
wait
echo ALLDONE > bench/results/resume_done.tmp

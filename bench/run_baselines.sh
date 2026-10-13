#!/usr/bin/env bash
# Baseline ("before") numbers: dev split only, 3 models. The held-out test split is run at the end.
set -u
cd "$(dirname "$0")/.."
for m in openai/gpt-oss-120b openai/gpt-oss-20b qwen/qwen3.8-27b; do
  PYTHONIOENCODING=utf-8 python -m uv run python bench/run_eval.py --model "$m" --config baseline --split dev
done

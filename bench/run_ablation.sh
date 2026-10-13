#!/usr/bin/env bash
# Ablation on the dev split: {link, correct, both} per model (baseline: see run_baselines.sh).
# One process per model, run in parallel. The held-out test split is run only at the very end.
set -u
cd "$(dirname "$0")/.."
SPLIT="${SPLIT:-dev}"
run_model() {
  for cfg in link correct both; do
    PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python -m uv run python bench/run_eval.py \
      --model "$1" --config "$cfg" --split "$SPLIT" > "bench/results/log_$(echo "$1" | tr '/' '_')_$cfg.tmp" 2>&1
  done
}
for m in openai/gpt-oss-120b openai/gpt-oss-20b qwen/qwen3.8-27b; do run_model "$m" & done
wait
echo ALLDONE > bench/results/ablation_done.tmp

# Clinical Text-to-SQL Agent

Text-to-SQL agent over synthetic clinical data ([Synthea](https://github.com/synthetichealth/synthea)),
PostgreSQL 16, local LLMs via Ollama, LangGraph. Work in progress — see the roadmap milestones.

## Quickstart (v0.1 baseline)

```bash
cp .env.example .env                       # set real passwords
docker compose up -d postgres              # Postgres + read-only role
uv sync
POPULATION=500 bash scripts/generate_synthea.sh   # seed 42, reference date 2026-01-01
uv run python scripts/load_postgres.py
ollama pull qwen2.5-coder:7b
uv run python -m csql "How many female patients are older than 60?"
```

## Reproducibility

- Synthea: seed `42`, reference date `20260101`, population in `scripts/generate_synthea.sh`.
- Model tags will be pinned here once the benchmark is run.

## Credits

Synthetic data generated with [Synthea™](https://github.com/synthetichealth/synthea) (Apache-2.0).

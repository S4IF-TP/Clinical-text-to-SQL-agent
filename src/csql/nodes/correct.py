"""Self-correction: feed the validation/execution error (or an empty result) back to the LLM."""

import re

from csql.llm import chat
from csql.nodes.generate import extract_sql
from csql.schema import schema_text

MAX_RETRIES = 2

SYSTEM = """You fix PostgreSQL queries for a clinical database (Synthea synthetic data).
Treat today's date as 2026-01-01: use DATE '2026-01-01', never CURRENT_DATE/now().
Return ONE corrected read-only SELECT in a ```sql block. Use only tables and columns from the schema
and exact literal values as they appear in the data.

SCHEMA:
{schema}
"""

EMPTY_FEEDBACK = (
    "The query ran but returned no rows. Re-check literal values (exact spelling and case), join "
    "conditions and filters. If you are confident the correct answer is genuinely empty, return the "
    "same query unchanged."
)


def _norm(sql: str) -> str:
    """Compare queries ignoring case, whitespace, trailing semicolon and the injected LIMIT 100."""
    sql = re.sub(r"\s+", " ", sql.strip().rstrip(";")).lower()
    return re.sub(r" limit 100$", "", sql)


def correct(state: dict) -> dict:
    error = state.get("error")
    feedback = f"The query failed with this error:\n{error}" if error else EMPTY_FEEDBACK
    schema = state.get("linked_schema") or schema_text()
    res = chat(
        [
            {"role": "system", "content": SYSTEM.format(schema=schema)},
            {
                "role": "user",
                "content": f"Question: {state['question']}\n\nPrevious SQL:\n{state['sql']}\n\n{feedback}",
            },
        ],
        model=state.get("model"),
    )
    new_sql = extract_sql(res.text)
    return {
        "sql": new_sql,
        "retries": state.get("retries", 0) + 1,
        "converged": _norm(new_sql) == _norm(state["sql"]),
        "trace": state.get("trace", [])
        + [
            {
                "node": "correct",
                "reason": "error" if error else "empty_result",
                "latency_s": round(res.latency_s, 2),
                "tokens": res.prompt_tokens + res.completion_tokens,
            }
        ],
    }

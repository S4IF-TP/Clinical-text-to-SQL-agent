import re

from csql.llm import chat
from csql.schema import schema_text

SYSTEM = """You are an expert PostgreSQL analyst for a clinical database (Synthea synthetic data).
Write ONE read-only PostgreSQL SELECT query that answers the user's question.
Use only the tables and columns listed in the schema. Return only the SQL in a ```sql block.

SCHEMA:
{schema}
"""

_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_sql(text: str) -> str:
    """Pull SQL out of a fenced block; fall back to the raw text."""
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip().rstrip(";").strip()


def generate(state: dict) -> dict:
    res = chat(
        [
            {"role": "system", "content": SYSTEM.format(schema=schema_text())},
            {"role": "user", "content": state["question"]},
        ],
        model=state.get("model"),
    )
    return {
        "sql": extract_sql(res.text),
        "trace": state.get("trace", [])
        + [
            {
                "node": "generate",
                "latency_s": round(res.latency_s, 2),
                "tokens": res.prompt_tokens + res.completion_tokens,
            }
        ],
    }

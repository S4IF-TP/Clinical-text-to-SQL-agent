"""Schema linking: an LLM picks the tables and columns relevant to the question."""

import json
import re

from csql.llm import chat
from csql.schema import TABLE_DESCRIPTIONS, introspect, schema_text

KEY_COLUMNS = {"id", "patient", "encounter"}  # always kept so joins stay possible

SYSTEM = """You select the part of a database schema needed to answer a question.
Return ONLY JSON: {{"tables": ["..."], "columns": {{"table": ["col", ...]}}}}.
Pick at most {k} tables and, per table, only the columns needed (filters, joins, outputs).

SCHEMA:
{overview}
"""


def _overview() -> str:
    lines = []
    for table, meta in introspect().items():
        cols = ", ".join(c for c, _ in meta["columns"])
        lines.append(f"- {table}: {TABLE_DESCRIPTIONS.get(table, '')}\n    columns: {cols}")
    return "\n".join(lines)


def parse_selection(text: str) -> tuple[list[str], dict[str, set[str]]] | None:
    """Parse and sanity-check the model's JSON; None means 'fall back to the full schema'."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    info = introspect()
    tables = [t for t in data.get("tables", []) if t in info]
    if not tables:
        return None
    columns: dict[str, set[str]] = {}
    for t in tables:
        valid = {c for c, _ in info[t]["columns"]}
        picked = {c for c in (data.get("columns") or {}).get(t, []) if c in valid}
        columns[t] = (picked | (KEY_COLUMNS & valid)) if picked else valid
    return tables, columns


def link(state: dict, k: int = 4) -> dict:
    res = chat(
        [
            {"role": "system", "content": SYSTEM.format(k=k, overview=_overview())},
            {"role": "user", "content": state["question"]},
        ],
        model=state.get("model"),
    )
    selection = parse_selection(res.text)
    entry = {"node": "link", "latency_s": round(res.latency_s, 2),
             "tokens": res.prompt_tokens + res.completion_tokens}  # fmt: skip
    if selection is None:
        entry["fallback"] = "full schema"
        return {"linked_schema": None, "trace": state.get("trace", []) + [entry]}
    tables, columns = selection
    entry["tables"] = tables
    return {
        "linked_schema": schema_text(tables, columns),
        "trace": state.get("trace", []) + [entry],
    }

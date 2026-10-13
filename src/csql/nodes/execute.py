from csql.db import run_query


def execute(state: dict) -> dict:
    trace = state.get("trace", [])
    try:
        columns, rows = run_query(state["sql"])
    except Exception as e:  # baseline: surface the error, no retry
        return {
            "error": str(e).strip(),
            "columns": [],
            "rows": [],
            "trace": trace + [{"node": "execute", "error": str(e).strip()}],
        }
    return {
        "error": None,
        "columns": columns,
        "rows": rows,
        "trace": trace + [{"node": "execute", "n_rows": len(rows)}],
    }

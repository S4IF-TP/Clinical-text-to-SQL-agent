"""SQL validation with sqlglot (dialect postgres). Pure function + a thin graph node.

Rules: exactly one statement; root is SELECT / WITH...SELECT / set operation of SELECTs; no DDL/DML/
commands anywhere in the tree; no system catalogs or dangerous functions; tables and columns must
exist in the schema; LIMIT 100 injected if missing. The read-only DB role is the second, independent
safety layer.
"""

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from csql.schema import introspect

MAX_LIMIT = 100

_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "Command", "Merge", "TruncateTable",
    "Copy", "Set", "Use", "Into", "Lock", "Grant", "Revoke", "Transaction", "Commit", "Rollback",
    "Analyze", "Pragma", "Attach", "Detach", "LoadData", "Kill", "Declare",
]  # fmt: skip
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

SET_OPS = (exp.Union, exp.Intersect, exp.Except)

BLOCKED_FUNCTION_PREFIXES = ("pg_", "lo_", "dblink", "set_config", "query_to_xml", "xpath", "txid_")
BLOCKED_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast"}


@dataclass
class ValidationResult:
    ok: bool
    sql: str
    error: str | None = None


def schema_columns() -> dict[str, set[str]]:
    return {t: {c for c, _ in meta["columns"]} for t, meta in introspect().items()}


def _fail(sql: str, msg: str) -> ValidationResult:
    return ValidationResult(False, sql, msg)


def _function_name(f: exp.Func) -> str:
    return (f.name if isinstance(f, exp.Anonymous) else f.sql_name()).lower()


def validate_sql(sql: str, schema: dict[str, set[str]]) -> ValidationResult:
    """Validate and normalise `sql` against `schema` ({table: {columns}}). Never touches the DB."""
    if not sql or not sql.strip():
        return _fail(sql, "Empty query.")
    try:
        statements = [s for s in sqlglot.parse(sql, dialect="postgres") if s is not None]
    except SqlglotError as e:
        return _fail(sql, f"SQL could not be parsed: {str(e).splitlines()[0]}")
    if len(statements) != 1:
        return _fail(sql, f"Exactly one statement is allowed, got {len(statements)}.")
    stmt = statements[0]

    if not isinstance(stmt, exp.Select | exp.Union | exp.Intersect | exp.Except):
        return _fail(sql, f"Only SELECT queries are allowed, got {type(stmt).__name__}.")
    for node in stmt.walk():
        if isinstance(node, FORBIDDEN_NODES):
            return _fail(sql, f"Forbidden operation: {type(node).__name__}.")
        if isinstance(node, exp.Func) and _function_name(node).startswith(
            BLOCKED_FUNCTION_PREFIXES
        ):
            return _fail(sql, f"Function not allowed: {_function_name(node)}.")

    cte_names = {c.alias.lower() for c in stmt.find_all(exp.CTE) if c.alias}
    alias_to_table: dict[str, str] = {}
    for t in stmt.find_all(exp.Table):
        name = t.name.lower()
        if t.db and t.db.lower() in BLOCKED_SCHEMAS or (t.db and t.db.lower() != "public"):
            return _fail(sql, f"Schema '{t.db}' is not allowed; use the public tables only.")
        if name in cte_names and not t.db:
            continue
        if name not in schema:
            return _fail(
                sql, f"Unknown table '{t.name}'. Available tables: {', '.join(sorted(schema))}."
            )
        alias_to_table[(t.alias or t.name).lower()] = name

    all_columns = {c for cols in schema.values() for c in cols}
    derived = {a.alias.lower() for a in stmt.find_all(exp.Alias) if a.alias}
    derived |= {c.alias.lower() for c in stmt.find_all(exp.CTE) if c.alias}
    derived |= {
        i.name.lower() for ta in stmt.find_all(exp.TableAlias) for i in ta.args.get("columns") or []
    }
    for col in stmt.find_all(exp.Column):
        if isinstance(col.this, exp.Star):
            continue
        name, qualifier = col.name.lower(), col.table.lower()
        if qualifier and qualifier in alias_to_table:
            table = alias_to_table[qualifier]
            if name not in schema[table]:
                return _fail(
                    sql,
                    f"Column '{col.name}' does not exist in table '{table}'. "
                    f"Columns: {', '.join(sorted(schema[table]))}.",
                )
        elif not qualifier and name not in all_columns and name not in derived:
            return _fail(sql, f"Unknown column '{col.name}'.")

    if not stmt.args.get("limit"):
        stmt = stmt.limit(MAX_LIMIT)
    return ValidationResult(True, stmt.sql(dialect="postgres"))


def validate(state: dict) -> dict:
    res = validate_sql(state["sql"], schema_columns())
    entry = {"node": "validate", "ok": res.ok}
    if not res.ok:
        entry["error"] = res.error
    return {
        "sql": res.sql if res.ok else state["sql"],
        "error": None if res.ok else res.error,
        "validation_failed": not res.ok,
        "trace": state.get("trace", []) + [entry],
    }

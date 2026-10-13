"""Graph routing with a scripted fake LLM and fake DB (no network, no Postgres)."""

import pytest

from csql import graph
from csql.llm import LLMResult
from csql.nodes import answer, correct, execute, generate, validate

SCHEMA = {"patients": {"id", "gender"}}


class Script:
    """Returns queued SQL strings for generate/correct; records how many calls were made."""

    def __init__(self, sqls):
        self.sqls = list(sqls)
        self.calls = 0

    def __call__(self, messages, model=None, temperature=0.0):
        self.calls += 1
        text = self.sqls.pop(0) if self.sqls else "SELECT 1"
        return LLMResult(f"```sql\n{text}\n```", 1, 1, 0.0)


@pytest.fixture
def env(monkeypatch):
    def setup(sqls, rows_by_sql=None):
        script = Script(sqls)
        monkeypatch.setattr(generate, "chat", script)
        monkeypatch.setattr(correct, "chat", script)
        monkeypatch.setattr(answer, "chat", lambda *a, **k: LLMResult("done", 1, 1, 0.0))
        monkeypatch.setattr(generate, "schema_text", lambda *a, **k: "SCHEMA")
        monkeypatch.setattr(correct, "schema_text", lambda *a, **k: "SCHEMA")
        monkeypatch.setattr(validate, "schema_columns", lambda: SCHEMA)

        def fake_query(sql, max_rows=None):
            rows = (rows_by_sql or {}).get(sql.split(" LIMIT")[0], [(1,)])
            return ["n"], rows

        monkeypatch.setattr(execute, "run_query", fake_query)
        return script

    return setup


def test_retries_capped_at_two(env):
    script = env(["SELECT * FROM nope1", "SELECT * FROM nope2", "SELECT * FROM nope3"])
    state = graph.ask("q", config="correct", with_answer=False)
    assert state["retries"] == 2
    assert script.calls == 3  # 1 generate + 2 corrections
    assert "Unknown table" in state["error"]
    assert sum(t["node"] == "validate" and not t["ok"] for t in state["trace"]) == 3


def test_validation_failure_then_fixed(env):
    env(["SELECT * FROM nope", "SELECT count(*) FROM patients"])
    state = graph.ask("q", config="correct", with_answer=False)
    assert state["retries"] == 1 and not state.get("error") and state["rows"] == [(1,)]


def test_empty_result_triggers_retry(env):
    env(
        [
            "SELECT id FROM patients WHERE gender = 'x'",
            "SELECT id FROM patients WHERE gender = 'F'",
        ],
        rows_by_sql={"SELECT id FROM patients WHERE gender = 'x'": []},
    )
    state = graph.ask("q", config="correct", with_answer=False)
    assert state["retries"] == 1 and state["rows"] == [(1,)]


def test_legitimately_empty_stops_when_converged(env):
    same = "SELECT id FROM patients WHERE gender = 'x'"
    script = env([same, same, same], rows_by_sql={same: []})
    state = graph.ask("q", config="correct", with_answer=False)
    assert state["retries"] == 1 and script.calls == 2  # model kept the query -> no more loops
    assert state["rows"] == []


def test_baseline_never_retries_or_validates(env):
    env(["SELECT * FROM nope"])
    state = graph.ask("q", config="baseline", with_answer=False)
    assert state.get("retries", 0) == 0
    assert all(t["node"] != "validate" for t in state["trace"])


def test_unknown_config():
    with pytest.raises(ValueError):
        graph.build_graph("nonsense")

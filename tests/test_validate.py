import pytest

from csql.nodes.validate import validate_sql

SCHEMA = {
    "patients": {"id", "birthdate", "deathdate", "gender", "city", "income", "race"},
    "encounters": {"id", "patient", "start", "stop", "encounterclass", "total_claim_cost"},
    "conditions": {"patient", "encounter", "start", "stop", "description"},
}


def check(sql):
    return validate_sql(sql, SCHEMA)


# --- 15 malicious / invalid queries that must be rejected -------------------------------------
REJECTED = [
    ("DROP TABLE patients", "Only SELECT"),
    ("SELECT 1; DROP TABLE patients", "Exactly one statement"),
    ("SELECT * FROM patients; SELECT * FROM encounters", "Exactly one statement"),
    ("UPDATE patients SET income = 0", "Only SELECT"),
    ("DELETE FROM encounters", "Only SELECT"),
    ("INSERT INTO patients (id) VALUES ('x')", "Only SELECT"),
    ("TRUNCATE patients", "Only SELECT"),
    ("ALTER TABLE patients ADD COLUMN x int", "Only SELECT"),
    ("CREATE TABLE evil AS SELECT * FROM patients", "Only SELECT"),
    ("SELECT * INTO backup FROM patients", "Forbidden"),
    ("SELECT * FROM patients FOR UPDATE", "Forbidden"),
    ("WITH d AS (DELETE FROM patients RETURNING *) SELECT * FROM d", "Forbidden"),
    ("SELECT pg_sleep(10)", "not allowed"),
    ("SELECT * FROM pg_catalog.pg_user", "not allowed"),
    ("SELECT * FROM information_schema.tables", "not allowed"),
    ("SELECT * FROM medications_typo", "Unknown table"),
    ("SELECT nonexistent_col FROM patients", "Unknown column"),
    ("SELECT p.salary FROM patients p", "does not exist in table"),
    ('SELECT "stop date" FROM conditions', "Unknown column"),
    ("", "Empty"),
    ("SELEC * FRM patients", ""),
]


@pytest.mark.parametrize(("sql", "fragment"), REJECTED)
def test_rejects(sql, fragment):
    res = check(sql)
    assert not res.ok
    assert fragment.lower() in (res.error or "").lower()


# --- valid queries must pass (false rejections would lower accuracy) --------------------------
def test_simple_select_gets_limit():
    res = check("SELECT count(*) FROM patients")
    assert res.ok and "LIMIT 100" in res.sql


def test_existing_limit_kept():
    res = check("SELECT id FROM patients LIMIT 5")
    assert res.ok and "LIMIT 5" in res.sql and "LIMIT 100" not in res.sql


def test_trailing_semicolon_ok():
    assert check("SELECT count(*) FROM patients;").ok


def test_join_with_aliases_and_alias_columns():
    res = check(
        "SELECT p.gender, count(*) AS n FROM patients p JOIN encounters e ON e.patient = p.id "
        "WHERE e.encounterclass = 'emergency' GROUP BY p.gender ORDER BY n DESC"
    )
    assert res.ok, res.error


def test_cte_and_derived_columns():
    res = check(
        "WITH c AS (SELECT patient, count(*) AS n FROM encounters GROUP BY patient) "
        "SELECT avg(n) FROM c"
    )
    assert res.ok, res.error


def test_union_ok():
    assert check("SELECT id FROM patients UNION SELECT patient FROM encounters").ok


def test_date_functions_and_casts():
    res = check(
        "SELECT extract(year FROM start)::int AS y, count(*) FROM encounters "
        "WHERE start < DATE '2026-01-01' - interval '1 year' GROUP BY y"
    )
    assert res.ok, res.error


def test_window_function():
    assert check(
        "SELECT patient, sum(total_claim_cost) OVER (PARTITION BY patient) FROM encounters"
    ).ok

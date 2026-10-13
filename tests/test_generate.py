from csql.nodes.generate import extract_sql


def test_extract_sql_from_fence():
    text = "Here you go:\n```sql\nSELECT count(*) FROM patients;\n```"
    assert extract_sql(text) == "SELECT count(*) FROM patients"


def test_extract_sql_raw():
    assert extract_sql("SELECT 1;") == "SELECT 1"

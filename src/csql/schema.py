"""Schema introspection + short hand-written descriptions (used by prompts and schema linking)."""

from functools import lru_cache

import psycopg

from csql.config import get_settings

TABLE_DESCRIPTIONS = {
    "patients": "One row per patient: demographics, birth/death dates, location, income, lifetime costs.",
    "encounters": "Healthcare visits (ambulatory, emergency, inpatient, wellness...) with dates and costs.",
    "conditions": "Diagnoses / disorders recorded for a patient during an encounter.",
    "medications": "Prescriptions: drug, dates, cost, dispenses, reason.",
    "observations": "Measurements and lab results (vitals, labs, surveys): description, value, units.",
    "procedures": "Procedures performed during encounters, with cost and reason.",
    "allergies": "Allergies and intolerances of a patient, with reaction and severity.",
    "immunizations": "Vaccines administered to a patient.",
}

COLUMN_HINTS = {
    "patients.id": "UUID primary key; referenced as 'patient' in other tables",
    "patients.gender": "'M' or 'F'",
    "patients.birthdate": "date of birth; compute age with age()/date arithmetic",
    "patients.deathdate": "NULL if the patient is alive",
    "patients.race": "e.g. white, black, asian, native, other (lowercase)",
    "patients.ethnicity": "hispanic or nonhispanic",
    "encounters.encounterclass": "ambulatory, emergency, inpatient, wellness, urgentcare, outpatient",
    "encounters.start": "timestamp the encounter began",
    "encounters.total_claim_cost": "total cost of the encounter",
    "conditions.stop": "NULL if the condition is still active (unresolved)",
    "medications.stop": "NULL if the medication is still active",
    "observations.value": "TEXT, may be non-numeric; cast with ::numeric only when the units are numeric",
    "observations.category": "vital-signs, laboratory, survey, ...",
}


@lru_cache
def introspect() -> dict:
    """Return {table: {"columns": [(name, type)], "fks": [(col, ref_table)]}} from the live DB."""
    s = get_settings()
    out: dict = {}
    with psycopg.connect(s.dsn(readonly=True)) as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT table_name, column_name, data_type FROM information_schema.columns
               WHERE table_schema = 'public' ORDER BY table_name, ordinal_position"""
        )
        for table, col, dtype in cur.fetchall():
            out.setdefault(table, {"columns": [], "fks": []})["columns"].append((col, dtype))
        cur.execute(
            """SELECT kcu.table_name, kcu.column_name, ccu.table_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu USING (constraint_name, table_schema)
               JOIN information_schema.constraint_column_usage ccu USING (constraint_name, table_schema)
               WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'"""
        )
        for table, col, ref in cur.fetchall():
            out[table]["fks"].append((col, ref))
    return out


def schema_text(tables: list[str] | None = None) -> str:
    """Prompt-ready schema: one block per table with description, columns, FKs and hints."""
    info = introspect()
    blocks = []
    for table, meta in info.items():
        if tables is not None and table not in tables:
            continue
        lines = [f"TABLE {table} -- {TABLE_DESCRIPTIONS.get(table, '')}"]
        for col, dtype in meta["columns"]:
            hint = COLUMN_HINTS.get(f"{table}.{col}")
            lines.append(f"  {col} {dtype}" + (f"  -- {hint}" if hint else ""))
        for col, ref in meta["fks"]:
            lines.append(f"  FOREIGN KEY {col} -> {ref}.id")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)

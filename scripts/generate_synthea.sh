#!/usr/bin/env bash
# Generate synthetic patients with Synthea (CSV export). Reproducible: fixed seed + reference date.
# Usage: POPULATION=500 ./scripts/generate_synthea.sh      (default 2000)
set -euo pipefail

cd "$(dirname "$0")/.."
POPULATION="${POPULATION:-2000}"
SEED="${SEED:-42}"
REFERENCE_DATE="${REFERENCE_DATE:-20260101}"   # pins "today" so ages/dates are stable
JAR="data/synthea-with-dependencies.jar"
OUT="data/synthea"

mkdir -p data
if [ ! -f "$JAR" ]; then
  echo "Downloading Synthea..."
  curl -L --fail -o "$JAR" \
    https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar
fi

rm -rf "$OUT"
java -jar "$JAR" -s "$SEED" -r "$REFERENCE_DATE" -p "$POPULATION" \
  --exporter.baseDirectory="$OUT" \
  --exporter.csv.export=true \
  --exporter.fhir.export=false \
  --exporter.hospital.fhir.export=false \
  --exporter.practitioner.fhir.export=false

echo "CSV files in $OUT/csv:"
ls "$OUT/csv"

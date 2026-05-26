#!/bin/bash
# =============================================================================
# Pipeline entrypoint — runs Part 1 (synthetic data) then Part 2 (dbt build).
# Idempotent: re-running rewrites the enriched layer and the DuckDB warehouse.
# =============================================================================
set -euo pipefail

cd /app

echo "================================================================"
echo "Part 1/2 — Synthetic data generation"
echo "================================================================"

# The starter Excel is .gitignored (recruiter ships it separately). When it
# is mounted into the container we re-extract data/raw/. Otherwise we trust
# the committed data/raw/*.parquet and skip step 00.
if [ -f /app/air_cote_divoire_starter_dataset.xlsx ]; then
    echo ">>> Starter Excel detected — running full pipeline (10 → 15)"
    python scripts/run_all.py
else
    echo ">>> No starter Excel — using committed data/raw/ (skipping step 00)"
    for step in scripts/10_*.py scripts/11_*.py scripts/12_*.py \
                scripts/13_*.py scripts/14_*.py scripts/15_*.py; do
        echo ">>> Running ${step}"
        python "${step}"
    done
fi

python scripts/99_validate_pipeline.py

echo ""
echo "================================================================"
echo "Part 2/2 — dbt build"
echo "================================================================"

cd /app/dbt
export DBT_PROFILES_DIR=.

dbt deps
dbt build
dbt docs generate

echo ""
echo "================================================================"
echo "  Pipeline finished."
echo "  Warehouse : /app/dbt/airline.duckdb"
echo "  Lineage   : /app/dbt/target/ (use 'dbt docs serve' to browse)"
echo "================================================================"

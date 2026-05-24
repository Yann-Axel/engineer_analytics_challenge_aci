#!/bin/bash
# =============================================================================
# Superset provisioner entrypoint — runs once after Superset is healthy to
# create the DuckDB connection, 19 datasets, 34 charts and 5 dashboards via
# the REST API + a direct write to the SQLite metastore for main_dttm_col.
# All scripts are idempotent: re-runs skip what already exists.
# =============================================================================
set -euo pipefail

: "${SUPERSET_URL:=http://superset:8088}"
: "${SUPERSET_DB_PATH:=/app/superset_home/superset.db}"
export SUPERSET_URL SUPERSET_DB_PATH

cd /app/dashboard/superset

echo ">>> [provisioner] datasets (DB connection + 19 datasets)"
python setup_datasets.py

echo ">>> [provisioner] datetime columns (main_dttm_col)"
python configure_datetime_columns.py

echo ">>> [provisioner] charts (34)"
python setup_charts.py

echo ">>> [provisioner] dashboards (5)"
python setup_dashboards.py

echo ""
echo "================================================================"
echo "  Superset provisioning finished."
echo "  Open http://localhost:8088 — login admin / admin"
echo "================================================================"

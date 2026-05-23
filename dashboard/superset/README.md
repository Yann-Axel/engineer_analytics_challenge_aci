# Superset dashboard — local setup

Lightweight Superset stack reading the dbt-built DuckDB file directly.

## Prerequisites

- Docker Desktop running (Compose v2)
- `dbt/airline.duckdb` already built (run `dbt build` in `../../dbt/` first)

## Start

```bash
cd dashboard/superset

# 1. Build the image (Superset + duckdb-engine)
docker compose build

# 2. Start Superset
docker compose up -d

# 3. Initialise metastore + admin user (one-off)
bash bootstrap.sh
```

Then open <http://localhost:8088> — login `admin / admin`.

## Connect Superset to DuckDB and provision datasets

Run the automated provisioning script (from the project root, with the venv activated):

```bash
.venv/Scripts/python dashboard/superset/setup_datasets.py
```

It creates (idempotently):
- 1 database connection `airline-duckdb` → `/app/data/airline.duckdb` (read-only)
- 19 datasets across `main_marts`, `main_intermediate`, `main_ontology` schemas

Re-running the script is safe: it detects existing resources via the API's
422 "already exists" response and skips them.

> Manual alternative (if you prefer the UI):
> Settings → Database Connections → + Database → SQLAlchemy URI =
> `duckdb:////app/data/airline.duckdb?access_mode=read_only`

## Sanity check query

In **SQL Lab → SQL Editor**:

```sql
select route_id, ontology_concept, cancellation_rate_12m
from main_ontology.ont_irops_heavy_route
order by disruption_rate_12m desc;
```

You should see 5 routes.

## Stop / clean

```bash
docker compose down            # stops, keeps metastore
docker compose down -v         # stops AND wipes metastore (fresh start next time)
```

## Why this layout

| Choice | Reason |
|---|---|
| Single container | Demo-scale, no need for Celery/Redis/Postgres |
| SQLite metastore | Persisted in the `superset_home` volume; survives restarts |
| Read-only DuckDB mount | Superset never writes to the analytical store |
| `duckdb-engine` in custom image | Superset talks to DuckDB via SQLAlchemy |
| Bootstrap script | Idempotent, encapsulates DB upgrade + admin + perms |

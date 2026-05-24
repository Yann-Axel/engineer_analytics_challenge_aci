# Superset dashboard — local setup

Lightweight Superset stack reading the dbt-built DuckDB file directly.

## Prerequisites

- Docker Desktop running (Compose v2)
- `dbt/airline.duckdb` already built (run `dbt build` in `../../dbt/` first)

## Start

```bash
cd dashboard/superset

# 1. Build the image (Superset + duckdb-engine + auto-init entrypoint)
docker compose build

# 2. Start Superset — the container's entrypoint runs `db upgrade`,
#    creates the admin user, and runs `init` automatically on first boot.
docker compose up -d
```

Then open <http://localhost:8088> — login `admin / admin`.

## Connect Superset to DuckDB and provision datasets

The cleanest path is to let the `superset-provisioner` compose service do it
for you (run from the project root):

```bash
docker compose up -d superset-provisioner
```

This idempotently creates:
- 1 database connection `airline-duckdb` → `/app/data/airline.duckdb` (read-only)
- 19 datasets across `main_marts`, `main_intermediate`, `main_ontology` schemas
- The full chart + dashboard catalogue (see below)

If you prefer to run the scripts manually from the host venv (e.g. for
debugging), each script honours `SUPERSET_URL` (default `http://localhost:8088`)
and the host workflow works out-of-the-box because Superset publishes 8088:

```bash
.venv/Scripts/python dashboard/superset/setup_datasets.py
.venv/Scripts/python dashboard/superset/configure_datetime_columns.py
.venv/Scripts/python dashboard/superset/setup_charts.py
.venv/Scripts/python dashboard/superset/setup_dashboards.py
```

> Manual alternative (if you prefer the UI):
> Settings → Database Connections → + Database → SQLAlchemy URI =
> `duckdb:////app/data/airline.duckdb?access_mode=read_only`

## Chart and dashboard catalogue

Creates 34 charts grouped into 5 dashboards (idempotent on re-run):

| # | Slug                        | Charts |
|---|-----------------------------|-------:|
| 0 | `executive-overview`        | 10     |
| 1 | `network-profitability`     | 7      |
| 2 | `customer-retention`        | 7      |
| 3 | `upsell-crosssell`          | 6      |
| 4 | `decision-layer`            | 4      |

All dashboards carry a shared **Date Range** native filter at the top.

Open each one at `http://localhost:8088/superset/dashboard/<slug>/`.

## Capture screenshots (Playwright headless)

```bash
.venv/Scripts/python dashboard/superset/capture_screenshots.py
```

Produces five PNG files under `docs/screenshots/`:

| File | Dashboard |
|---|---|
| `00_executive_overview.png` | Page 0 |
| `01_network_profitability.png` | Page 1 |
| `02_customer_retention.png` | Page 2 |
| `03_upsell_crosssell.png` | Page 3 |
| `04_decision_layer.png` | Page 4 |

Requires `playwright install chromium` once (already in `requirements.txt`).

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
| Auto-init entrypoint | `db upgrade` + `create-admin` + `init` run at container boot (idempotent) |

# Superset dashboard — local setup

Lightweight Superset stack reading the dbt-built DuckDB file directly. Design rationale and brief mapping: [`docs_video_screen/09_dashboard_design.md`](../../docs_video_screen/09_dashboard_design.md).

## Prerequisites

- Docker Desktop running (Compose v2)
- `dbt/airline.duckdb` already built (run `dbt build` in `../../dbt/` first)

## Start

```bash
cd dashboard/superset

# 1. Build the image (Superset + duckdb-engine + auto-init entrypoint)
docker compose build

# 2. Start Superset — the entrypoint runs db upgrade,
#    creates the admin user, and runs `init` automatically on first boot.
docker compose up -d
```

Open <http://localhost:8088> — login `admin / admin`.

## Connect Superset to DuckDB and provision datasets

The cleanest path is to let the `superset-provisioner` compose service do it for you (from the project root):

```bash
docker compose up -d superset-provisioner
```

This idempotently creates:

- 1 database connection `airline-duckdb` → `/app/data/airline.duckdb` (read-only)
- Datasets across `main_marts`, `main_intermediate`, `main_ontology` schemas
- The full chart + dashboard catalogue (see below)

If you prefer to run the scripts manually from the host venv (e.g. for debugging), each script honours `SUPERSET_URL` (default `http://localhost:8088`):

```bash
.venv/Scripts/python dashboard/superset/setup_datasets.py
.venv/Scripts/python dashboard/superset/configure_datetime_columns.py
.venv/Scripts/python dashboard/superset/setup_charts.py
.venv/Scripts/python dashboard/superset/setup_dashboards.py
```

> Manual UI alternative — Settings → Database Connections → + Database → SQLAlchemy URI =
> `duckdb:////app/data/airline.duckdb?access_mode=read_only`

## Dashboard catalogue — 4 dashboards × 18 charts

Maps 1:1 to the brief's 4 dashboard areas. Idempotent on re-run.

| # | Brief area              | Slug                    | Charts |
| - | :---------------------- | :---------------------- | -----: |
| 1 | Network & Profitability | `network-profitability` |    5   |
| 2 | Customer & Retention    | `customer-retention`    |    5   |
| 3 | Upsell & Cross-sell     | `upsell-crosssell`      |    4   |
| 4 | Decision Layer          | `decision-layer`        |    4   |

All dashboards carry a shared **Date Range** native filter at the top. Open each one at `http://localhost:8088/superset/dashboard/<slug>/`.

## Capture screenshots (Playwright headless)

```bash
.venv/Scripts/python dashboard/superset/capture_screenshots.py
```

Produces four PNG files under `docs_video_screen/screenshots/`:

| File                            | Dashboard               |
| :------------------------------ | :---------------------- |
| `01_network_profitability.png`  | Network & Profitability |
| `02_customer_retention.png`     | Customer & Retention    |
| `03_upsell_crosssell.png`       | Upsell & Cross-sell     |
| `04_decision_layer.png`         | Decision Layer          |

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

| Choice                           | Reason                                                                            |
| :------------------------------- | :-------------------------------------------------------------------------------- |
| Single container                 | Demo-scale, no need for Celery/Redis/Postgres                                     |
| SQLite metastore                 | Persisted in the `superset_home` volume; survives restarts                        |
| Read-only DuckDB mount           | Superset never writes to the analytical store                                     |
| `duckdb-engine` in custom image  | Superset talks to DuckDB via SQLAlchemy                                           |
| Auto-init entrypoint             | `db upgrade` + `create-admin` + `init` run at container boot (idempotent)         |

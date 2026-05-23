# Part 3 — Dashboard design

The brief asks for an Executive Growth Allocation Dashboard covering four areas with screenshots and a one-page recommendation. This document is the design rationale; the live dashboards run in Apache Superset (see `dashboard/superset/README.md`).

## 1. Tool choice

**Apache Superset 4.1.2** in Docker, reading `dbt/airline.duckdb` via `duckdb-engine`. The brief recommends Superset by name in its "Recommended documentation" list. Reproducible end-to-end through versioned Python scripts — no drag-and-drop in the UI.

## 2. Brief areas → 4 dashboards → 18 charts

| Brief area | Dashboard slug | Charts (n) | Source |
|---|---|---|---|
| Network and profitability | `network-profitability` | **5** | revenue/route, opportunity matrix (bubble), OTP+cancel trends, RASK by route_type, disruptions by type |
| Customer and retention | `customer-retention` | **5** | segment & loyalty distribution, high-value at-risk table, complaint heatmap, sentiment trend, repeat-booking rate |
| Upsell and cross-sell | `upsell-crosssell` | **4** | upgrade conversion by tier, ancillary attach by segment, revenue per pax by fare class, premium upsell candidates table |
| Decision layer | `decision-layer` | **4** | routes to grow, routes to defend, customers to retain, offers to prioritise (all ontology-driven tables) |

All 18 charts trace back to a Part-1 KPI or to an ontology concept from Part 2 — nothing was invented in the BI layer.

## 3. Reproducibility (10 minutes from a clean clone)

```bash
cd dashboard/superset
docker compose up -d
bash bootstrap.sh                 # admin/admin + permissions
cd ../..
.venv/Scripts/python dashboard/superset/setup_datasets.py
.venv/Scripts/python dashboard/superset/configure_datetime_columns.py
.venv/Scripts/python dashboard/superset/setup_charts.py
.venv/Scripts/python dashboard/superset/setup_dashboards.py
.venv/Scripts/python dashboard/superset/capture_screenshots.py
```

Login: `admin / admin`. The four dashboards are reachable at `http://localhost:8088/superset/dashboard/<slug>/`.

## 4. Captures

| Area | File |
|---|---|
| Network & Profitability | [docs/screenshots/01_network_profitability.png](screenshots/01_network_profitability.png) |
| Customer & Retention | [docs/screenshots/02_customer_retention.png](screenshots/02_customer_retention.png) |
| Upsell & Cross-sell | [docs/screenshots/03_upsell_crosssell.png](screenshots/03_upsell_crosssell.png) |
| Decision Layer | [docs/screenshots/04_decision_layer.png](screenshots/04_decision_layer.png) |

> Note: the screenshots reflect an earlier provisioning run with 34 charts. After the strict-brief reduction (18 charts), re-running `setup_charts.py` + `capture_screenshots.py` on a fresh Superset metastore regenerates them at the new shape.

## 5. Executive recommendations

The one-page CEO-printable recommendation is in [docs/10_executive_recommendations.md](10_executive_recommendations.md).

# Part 3 — Dashboard design

The brief asks for an Executive Growth Allocation Dashboard covering 4 areas, screenshots, and a one-page recommendation. The live dashboards run in Apache Superset; the recommendation is in [10_executive_recommendations.md](10_executive_recommendations.md).

## 1. Tool — Apache Superset 4.1.2

In Docker, reading [`dbt/airline.duckdb`](../dbt/airline.duckdb) via `duckdb-engine`. Superset is named in the brief's recommended list. **Fully reproducible** via versioned Python scripts — no drag-and-drop.

## 2. Brief areas → 4 dashboards → 18 charts

| Brief area | Slug | Charts | Content |
|---|---|---|---|
| Network & profitability | `network-profitability` | 5 | revenue/route, opportunity matrix, OTP+cancel trends, RASK, disruptions |
| Customer & retention | `customer-retention` | 5 | segment/loyalty, at-risk table, complaint heatmap, sentiment trend, repeat rate |
| Upsell & cross-sell | `upsell-crosssell` | 4 | upgrade conversion, attach by segment, rev/pax, premium candidates |
| Decision layer | `decision-layer` | 4 | Grow / Defend / Retain / Prioritise — all ontology-driven |

Every chart traces back to a Part-1 KPI or a Part-2 ontology concept — nothing invented in the BI layer.

```mermaid
flowchart TB
    Q{{CEO question<br/>Where to invest first?}} --> D1[Network & Profitability<br/>5 charts]
    Q --> D2[Customer & Retention<br/>5 charts]
    Q --> D3[Upsell & Cross-sell<br/>4 charts]
    D1 --> D4[Decision Layer<br/>4 ontology tables]
    D2 --> D4
    D3 --> D4
    D4 --> R[[Recommendation<br/>40 / 35 / 25 split]]

    classDef q fill:#fef3c7,stroke:#92400e,color:#92400e
    classDef dec fill:#dbeafe,stroke:#1e3a8a,color:#1e3a8a
    classDef out fill:#dcfce7,stroke:#166534,color:#166534
    class Q q
    class D4 dec
    class R out
```

## 3. Reproducibility

```bash
docker compose up --build -d superset superset-provisioner
```

Login `admin / admin` at <http://localhost:8088>. Each dashboard at `/superset/dashboard/<slug>/`.

## 4. Screenshots

| Area | File |
|---|---|
| Network & Profitability | [01_network_profitability.png](screenshots/01_network_profitability.png) |
| Customer & Retention | [02_customer_retention.png](screenshots/02_customer_retention.png) |
| Upsell & Cross-sell | [03_upsell_crosssell.png](screenshots/03_upsell_crosssell.png) |
| Decision Layer | [04_decision_layer.png](screenshots/04_decision_layer.png) |

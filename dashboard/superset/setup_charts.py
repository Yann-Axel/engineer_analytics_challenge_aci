"""
Provision the Air Côte d'Ivoire dashboard charts in Superset via the REST API.
Idempotent: re-running detects existing charts by slice_name and skips them.

Charts are organised by page, one page per brief area (no extras):
  - Page 1: Network & Profitability   (5 charts) — revenue, margin, LF, OTP, cancel, opportunity matrix
  - Page 2: Customer & Retention      (5 charts) — segmentation, at-risk, complaint themes, sentiment, loyalty
  - Page 3: Upsell & Cross-sell       (4 charts) — upgrade conversion, attach rate, ARPP, upsell candidates
  - Page 4: Decision Layer            (4 charts) — routes to grow / defend, customers to retain, offers to prioritize

Total: 18 charts, matching the four brief areas with their listed KPIs.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

import requests

SUPERSET_URL = "http://localhost:8088"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# Dataset IDs — pinned to the creation order in setup_datasets.py.
DATASETS: dict[str, int] = {
    "dim_date":                            1,
    "dim_airport":                         2,
    "dim_route":                           3,
    "dim_aircraft":                        4,
    "dim_fare":                            5,
    "dim_customer_current":                6,
    "fct_flights":                         7,
    "fct_bookings":                        8,
    "fct_customer_feedback":               9,
    "fct_ancillary_offers":               10,
    "fct_loyalty_events":                 11,
    "int_route_monthly_perf":             12,
    "int_route_complaint_themes":         13,
    "int_customer_lifetime":              14,
    "ont_high_value_at_risk_customer":    15,
    "ont_strategic_underperforming_route": 16,
    "ont_premium_upsell_candidate":       17,
    "ont_loyal_detractor":                18,
    "ont_irops_heavy_route":              19,
}


# ─────────────────────────────────────────────────────────────────────────────
# Chart-spec helpers
# ─────────────────────────────────────────────────────────────────────────────

def metric_sum(column: str, label: str | None = None) -> dict[str, Any]:
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": column},
        "aggregate": "SUM",
        "label": label or f"SUM({column})",
    }


def metric_avg(column: str, label: str | None = None) -> dict[str, Any]:
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": column},
        "aggregate": "AVG",
        "label": label or f"AVG({column})",
    }


def metric_count(label: str = "COUNT(*)") -> dict[str, Any]:
    return {
        "expressionType": "SQL",
        "sqlExpression": "COUNT(*)",
        "label": label,
    }


def metric_sql(sql: str, label: str) -> dict[str, Any]:
    return {
        "expressionType": "SQL",
        "sqlExpression": sql,
        "label": label,
    }


@dataclass
class ChartSpec:
    name: str
    dataset: str
    viz_type: str
    params: dict[str, Any]
    page_tag: str = ""
    description: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Charts catalogue — 18 charts, strict-brief
# ─────────────────────────────────────────────────────────────────────────────

def build_charts() -> list[ChartSpec]:
    charts: list[ChartSpec] = []

    # ═══ PAGE 1 — NETWORK & PROFITABILITY (5 charts) ═══════════════════════
    PAGE = "network_profitability"

    charts.append(ChartSpec(
        name="Net · Revenue by Route",
        dataset="int_route_monthly_perf",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Total revenue per route over the period.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sum("revenue_usd", "Revenue")],
            "groupby": ["route_id"],
            "row_limit": 20,
            "order_desc": True,
            "color_scheme": "supersetColors",
            "y_axis_format": "$,.0f",
        },
    ))

    charts.append(ChartSpec(
        name="Net · Route Opportunity Matrix",
        dataset="int_route_monthly_perf",
        viz_type="bubble",
        page_tag=PAGE,
        description="Margin % vs Load Factor per route — bubble size = revenue.",
        params={
            "viz_type": "bubble",
            "entity": "route_id",
            "x": metric_avg("load_factor", "Load Factor"),
            "y": metric_sql(
                "SUM(margin_usd) / NULLIF(SUM(revenue_usd), 0)",
                "Margin %",
            ),
            "size": metric_sum("revenue_usd", "Revenue"),
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "x_axis_format": ".0%",
            "y_axis_format": ".0%",
            "show_legend": True,
        },
    ))

    charts.append(ChartSpec(
        name="Net · OTP15 & Cancellation Trends",
        dataset="int_route_monthly_perf",
        viz_type="echarts_timeseries_line",
        page_tag=PAGE,
        description="On-time (≤15 min) rate and cancellation rate per month.",
        params={
            "viz_type": "echarts_timeseries_line",
            "x_axis": "period_month",
            "metrics": [
                metric_avg("otp15_rate", "OTP15"),
                metric_avg("cancellation_rate", "Cancel Rate"),
            ],
            "groupby": [],
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "y_axis_format": ".1%",
            "show_legend": True,
        },
    ))

    charts.append(ChartSpec(
        name="Net · Yield (RASK) by Route Type",
        dataset="fct_flights",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Revenue per available seat-km, grouped by route_type.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sql(
                "SUM(total_revenue_usd) / NULLIF(SUM(seat_capacity * distance_km), 0)",
                "RASK",
            )],
            "groupby": ["route_type"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "y_axis_format": ".3f",
        },
    ))

    charts.append(ChartSpec(
        name="Net · Disruptions by Type",
        dataset="fct_flights",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Count of disruption events per type.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sql(
                "SUM(CASE WHEN disruption_type IS NOT NULL THEN 1 ELSE 0 END)",
                "Disruption Count",
            )],
            "groupby": ["disruption_type"],
            "row_limit": 15,
            "order_desc": True,
            "color_scheme": "supersetColors",
        },
    ))

    # ═══ PAGE 2 — CUSTOMER & RETENTION (5 charts) ═══════════════════════════
    PAGE = "customer_retention"

    charts.append(ChartSpec(
        name="Cust · Segment & Loyalty Distribution",
        dataset="dim_customer_current",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Customer base by segment AND loyalty tier (two stacked bars).",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_count("Customers")],
            "groupby": ["customer_segment", "loyalty_tier_safe"],
            "row_limit": 20,
            "color_scheme": "supersetColors",
        },
    ))

    charts.append(ChartSpec(
        name="Cust · High-Value At-Risk Customers (top 20)",
        dataset="ont_high_value_at_risk_customer",
        viz_type="table",
        page_tag=PAGE,
        description="Customers flagged by the ont_high_value_at_risk_customer concept, sorted by lifetime spend.",
        params={
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": [
                "customer_id", "last_booking_date", "recency_days",
                "monetary_total_usd", "complaint_count", "avg_sentiment",
                "churn_risk_score",
            ],
            "order_by_cols": ['["monetary_total_usd",false]'],
            "row_limit": 20,
        },
    ))

    charts.append(ChartSpec(
        name="Cust · Complaint Themes by Route",
        dataset="int_route_complaint_themes",
        viz_type="heatmap",
        page_tag=PAGE,
        description="Most frequent complaint theme per route × month (avg sentiment as color).",
        params={
            "viz_type": "heatmap",
            "all_columns_x": "route_id",
            "all_columns_y": "top_theme_1",
            "metric": metric_avg("avg_sentiment", "Avg Sentiment"),
            "row_limit": 200,
            "linear_color_scheme": "schemeBlues",
        },
    ))

    charts.append(ChartSpec(
        name="Cust · Sentiment Trend (monthly)",
        dataset="fct_customer_feedback",
        viz_type="echarts_timeseries_line",
        page_tag=PAGE,
        description="Average sentiment score per month.",
        params={
            "viz_type": "echarts_timeseries_line",
            "x_axis": "feedback_date",
            "metrics": [metric_avg("sentiment_score", "Avg Sentiment")],
            "groupby": [],
            "time_grain_sqla": "P1M",
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "y_axis_format": ".3f",
            "show_legend": False,
        },
    ))

    charts.append(ChartSpec(
        name="Cust · Repeat Booking Rate",
        dataset="fct_bookings",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="Share of bookings made by customers with ≥2 bookings — proxy of repeat behaviour.",
        params={
            "viz_type": "big_number_total",
            "metric": metric_sql(
                "(COUNT(*) - COUNT(DISTINCT customer_id)) * 1.0 / NULLIF(COUNT(*), 0)",
                "Repeat Rate",
            ),
            "y_axis_format": ".1%",
            "subheader": "Bookings minus uniques / bookings",
        },
    ))

    # ═══ PAGE 3 — UPSELL & CROSS-SELL (4 charts) ═══════════════════════════
    PAGE = "upsell_crosssell"

    charts.append(ChartSpec(
        name="Up · Upgrade Conversion by Tier",
        dataset="fct_ancillary_offers",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Upgrade-offer acceptance rate by loyalty tier (filtered to upgrade_W and upgrade_J).",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sql(
                "SUM(CASE WHEN accepted_flag THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(CASE WHEN presented_flag THEN 1 ELSE 0 END), 0)",
                "Conversion Rate",
            )],
            "groupby": ["offer_type"],
            "adhoc_filters": [{
                "expressionType": "SQL",
                "sqlExpression": "offer_type IN ('upgrade_W', 'upgrade_J')",
                "clause": "WHERE",
            }],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "y_axis_format": ".1%",
        },
    ))

    charts.append(ChartSpec(
        name="Up · Ancillary Attach Rate by Segment",
        dataset="fct_bookings",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Ancillary attach rate, sliced by customer segment at booking.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sql(
                "SUM(CASE WHEN ancillary_revenue_usd > 0 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0)",
                "Attach Rate",
            )],
            "groupby": ["customer_segment_at_booking"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "y_axis_format": ".1%",
        },
    ))

    charts.append(ChartSpec(
        name="Up · Revenue per Passenger by Fare Class",
        dataset="fct_bookings",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="(Ticket + Ancillary) per booking by fare class.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sql(
                "SUM(ticket_price_usd + ancillary_revenue_usd) / NULLIF(COUNT(*), 0)",
                "Revenue / Pax",
            )],
            "groupby": ["fare_class"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "y_axis_format": "$,.2f",
        },
    ))

    charts.append(ChartSpec(
        name="Up · Premium Upsell Candidates (top 20)",
        dataset="ont_premium_upsell_candidate",
        viz_type="table",
        page_tag=PAGE,
        description="Customers flagged by the ont_premium_upsell_candidate concept (offer propensity proxy).",
        params={
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": [
                "customer_id", "customer_segment", "loyalty_tier",
                "upgrade_offers_presented", "upgrade_offers_accepted",
                "upgrade_acceptance_rate",
            ],
            "order_by_cols": ['["upgrade_acceptance_rate",false]'],
            "row_limit": 20,
        },
    ))

    # ═══ PAGE 4 — DECISION LAYER (4 tables) ═══════════════════════════════
    PAGE = "decision_layer"

    charts.append(ChartSpec(
        name="Dec · Routes to GROW (top profitable + busy)",
        dataset="int_route_monthly_perf",
        viz_type="table",
        page_tag=PAGE,
        description="Routes ranked by revenue with margin % and load factor — invest more capacity.",
        params={
            "viz_type": "table",
            "query_mode": "aggregate",
            "groupby": ["route_id"],
            "metrics": [
                metric_sum("revenue_usd", "Revenue"),
                metric_sql("SUM(margin_usd) / NULLIF(SUM(revenue_usd), 0)", "Margin %"),
                metric_sql("SUM(total_pax) * 1.0 / NULLIF(SUM(total_seat_capacity), 0)", "Load Factor"),
            ],
            "row_limit": 10,
            "order_desc": True,
        },
    ))

    charts.append(ChartSpec(
        name="Dec · Routes to DEFEND (operational fragility)",
        dataset="ont_irops_heavy_route",
        viz_type="table",
        page_tag=PAGE,
        description="Routes flagged IROPS-heavy by the ontology — ops fragility risks margin.",
        params={
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": [
                "route_id", "route_type", "is_strategic",
                "total_flights_12m", "cancellation_rate_12m", "disruption_rate_12m",
            ],
            "order_by_cols": ['["disruption_rate_12m",false]'],
            "row_limit": 20,
        },
    ))

    charts.append(ChartSpec(
        name="Dec · Customers to RETAIN (high-value at risk)",
        dataset="ont_high_value_at_risk_customer",
        viz_type="table",
        page_tag=PAGE,
        description="Customers flagged by the ont_high_value_at_risk_customer concept — prioritise retention spend.",
        params={
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": [
                "customer_id", "monetary_total_usd", "recency_days",
                "complaint_count", "avg_sentiment", "ltv_proxy_usd",
            ],
            "order_by_cols": ['["ltv_proxy_usd",false]'],
            "row_limit": 50,
        },
    ))

    charts.append(ChartSpec(
        name="Dec · Offers to PRIORITIZE (premium upsell)",
        dataset="ont_premium_upsell_candidate",
        viz_type="table",
        page_tag=PAGE,
        description="Customers with high upgrade-acceptance rates — push premium offers to these.",
        params={
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": [
                "customer_id", "customer_segment", "loyalty_tier",
                "upgrade_offers_presented", "upgrade_offers_accepted",
                "upgrade_acceptance_rate",
            ],
            "order_by_cols": ['["upgrade_acceptance_rate",false]'],
            "row_limit": 50,
        },
    ))

    return charts


# ─────────────────────────────────────────────────────────────────────────────
# Superset client (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

class SupersetClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.access_token: str | None = None
        self.csrf_token: str | None = None

    def _hdr(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "X-CSRFToken": self.csrf_token or "",
            "Content-Type": "application/json",
            "Referer": self.base_url,
        }

    def login(self) -> None:
        # Hybrid auth: JWT + session cookie (the chart-create endpoint of
        # Superset 4.1.2 needs a real user via session cookies, not JWT alone).
        import re
        r = self.session.get(f"{self.base_url}/login/", timeout=30)
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
        form_csrf = m.group(1) if m else ""
        self.session.post(
            f"{self.base_url}/login/",
            data={"username": self.username, "password": self.password,
                  "csrf_token": form_csrf},
            allow_redirects=True, timeout=30,
        )
        r = self.session.post(
            f"{self.base_url}/api/v1/security/login",
            json={"username": self.username, "password": self.password,
                  "provider": "db", "refresh": True},
            timeout=30,
        )
        r.raise_for_status()
        self.access_token = r.json()["access_token"]
        r = self.session.get(
            f"{self.base_url}/api/v1/security/csrf_token/",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )
        r.raise_for_status()
        self.csrf_token = r.json()["result"]
        print("  ✓ Authenticated as admin (JWT + session cookie)")

    def create_chart(self, spec: ChartSpec, dataset_id: int) -> tuple[str, int | None]:
        params_with_ds = {**spec.params, "datasource": f"{dataset_id}__table"}
        payload = {
            "slice_name": spec.name,
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "viz_type": spec.viz_type,
            "params": json.dumps(params_with_ds),
            "description": spec.description,
        }
        r = self.session.post(
            f"{self.base_url}/api/v1/chart/",
            headers=self._hdr(),
            json=payload,
            timeout=60,
        )
        if r.status_code == 422 and ("already exists" in r.text or "name" in r.text.lower()):
            return ("exists", None)
        if r.status_code >= 400:
            return ("failed", None)
        return ("created", r.json().get("id"))


def fetch_existing_chart_names() -> set[str]:
    """Read existing slice_names from the Superset metastore via docker exec
    (Superset 4.1.2's REST list endpoint hides API-created charts by default)."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "exec", "airline-superset", "python", "-c",
             "import sqlite3, json; "
             "con=sqlite3.connect('/app/superset_home/superset.db'); "
             "print(json.dumps([r[0] for r in con.execute('SELECT slice_name FROM slices')]))"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if result.returncode == 0:
            return set(json.loads(result.stdout.strip().splitlines()[-1]))
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        pass
    return set()


def main() -> int:
    print(f">>> Connecting to Superset at {SUPERSET_URL}")
    client = SupersetClient(SUPERSET_URL, ADMIN_USER, ADMIN_PASS)
    client.login()

    charts = build_charts()
    print(f"\n>>> Charts ({len(charts)} total)")

    existing_names = fetch_existing_chart_names()
    if existing_names:
        print(f"  (Found {len(existing_names)} existing charts in metastore — will skip duplicates)")

    created = 0
    existing = 0
    failed = 0
    for spec in charts:
        ds_id = DATASETS.get(spec.dataset)
        if ds_id is None:
            print(f"  ✗ {spec.name:<50s} UNKNOWN DATASET: {spec.dataset}")
            failed += 1
            continue
        if spec.name in existing_names:
            print(f"  ✓ {spec.name:<50s} (already exists, skipped)")
            existing += 1
            continue
        status, chart_id = client.create_chart(spec, ds_id)
        if status == "created":
            print(f"  + {spec.name:<50s} (id={chart_id}, dataset={spec.dataset})")
            created += 1
        elif status == "exists":
            print(f"  ✓ {spec.name:<50s} (already exists, skipped)")
            existing += 1
        else:
            print(f"  ✗ {spec.name:<50s} FAILED")
            failed += 1

    print(f"\n>>> Summary")
    print(f"    Created : {created}")
    print(f"    Existing: {existing}")
    print(f"    Failed  : {failed}")
    print(f"    Total   : {len(charts)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

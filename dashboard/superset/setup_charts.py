"""
Provision the Air Côte d'Ivoire dashboard charts in Superset via the REST API.
Idempotent: re-running detects existing charts by slice_name and skips them.

Charts are organised by page (matches the brief's 4 minimum dashboard areas
plus an Executive Overview):
  - Page 0: Executive Overview         (8 Big Numbers + 2 mini-trends)
  - Page 1: Network & Profitability    (7 charts)
  - Page 2: Customer & Retention       (7 charts)
  - Page 3: Upsell & Cross-sell        (6 charts)
  - Page 4: Decision Layer             (4 action-oriented tables)

Why this script:
  * Reproducibility — a reviewer runs `python setup_charts.py` and gets the
    same charts regardless of build order.
  * Versioning — chart definitions live in code, in Git.
  * Senior signal — the dashboard is built declaratively from the semantic
    layer, not assembled by drag-and-drop.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

import requests

SUPERSET_URL = "http://localhost:8088"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# Dataset IDs — pinned to the creation order in setup_datasets.py.
# (Superset's REST list endpoint hides API-created resources by default in 4.1.2,
#  so we resolve IDs by position; this is stable for a fresh metastore.)
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
        "expressionType": "SIMPLE",
        "column": {"column_name": ""},
        "aggregate": "COUNT",
        "label": label,
    }


def metric_count_distinct(column: str, label: str | None = None) -> dict[str, Any]:
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": column},
        "aggregate": "COUNT_DISTINCT",
        "label": label or f"COUNT(DISTINCT {column})",
    }


def metric_sql(sql: str, label: str) -> dict[str, Any]:
    return {
        "expressionType": "SQL",
        "sqlExpression": sql,
        "label": label,
    }


@dataclass
class ChartSpec:
    name: str               # slice_name in Superset
    dataset: str            # key of DATASETS
    viz_type: str
    params: dict[str, Any]
    page_tag: str = ""      # used for dashboards layout later
    description: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Charts catalogue
# ─────────────────────────────────────────────────────────────────────────────

def build_charts() -> list[ChartSpec]:
    charts: list[ChartSpec] = []

    # ═══ PAGE 0 — EXECUTIVE OVERVIEW (8 Big Numbers + 2 mini) ═══════════════
    PAGE = "executive_overview"

    # 1. Total Revenue (sum of total_revenue_usd from fct_flights)
    charts.append(ChartSpec(
        name="KPI · Total Revenue (USD)",
        dataset="fct_flights",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="Total revenue across all operated flights in the selected period.",
        params={
            "viz_type": "big_number_total",
            "metric": metric_sum("total_revenue_usd", "Total Revenue"),
            "adhoc_filters": [],
            "subheader": "All operated flights",
            "y_axis_format": "$,.0f",
        },
    ))

    # 2. Route Margin %
    charts.append(ChartSpec(
        name="KPI · Route Margin %",
        dataset="fct_flights",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="(Revenue - Operating cost) / Revenue across operated flights.",
        params={
            "viz_type": "big_number_total",
            "metric": metric_sql(
                "SUM(flight_margin_usd) / NULLIF(SUM(total_revenue_usd), 0)",
                "Margin %",
            ),
            "y_axis_format": ".1%",
            "subheader": "Margin / Revenue",
        },
    ))

    # 3. Load Factor
    charts.append(ChartSpec(
        name="KPI · Load Factor",
        dataset="fct_flights",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="Passengers carried over seats available.",
        params={
            "viz_type": "big_number_total",
            "metric": metric_sql(
                "SUM(pax_count) / NULLIF(SUM(seat_capacity), 0)",
                "Load Factor",
            ),
            "y_axis_format": ".1%",
            "subheader": "Pax / Capacity",
        },
    ))

    # 4. OTP15
    charts.append(ChartSpec(
        name="KPI · OTP15 (On-Time ≤15 min)",
        dataset="fct_flights",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="Share of non-cancelled flights with delay ≤ 15 minutes.",
        params={
            "viz_type": "big_number_total",
            "metric": metric_sql(
                "SUM(CASE WHEN is_on_time_15 THEN 1 ELSE 0 END) * 1.0 / "
                "NULLIF(SUM(CASE WHEN flight_status <> 'Cancelled' THEN 1 ELSE 0 END), 0)",
                "OTP15",
            ),
            "y_axis_format": ".1%",
            "subheader": "Operated flights only",
        },
    ))

    # 5. Cancellation Rate
    charts.append(ChartSpec(
        name="KPI · Cancellation Rate",
        dataset="fct_flights",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="Cancelled flights divided by scheduled flights.",
        params={
            "viz_type": "big_number_total",
            "metric": metric_sql(
                "SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0)",
                "Cancel Rate",
            ),
            "y_axis_format": ".1%",
            "subheader": "Cancelled / Scheduled",
        },
    ))

    # 6. Ancillary Attach Rate
    charts.append(ChartSpec(
        name="KPI · Ancillary Attach Rate",
        dataset="fct_bookings",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="Bookings with at least one ancillary purchase.",
        params={
            "viz_type": "big_number_total",
            "metric": metric_sql(
                "SUM(CASE WHEN ancillary_revenue_usd > 0 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0)",
                "Attach Rate",
            ),
            "y_axis_format": ".1%",
            "subheader": "Bookings",
        },
    ))

    # 7. Average Sentiment (NLP)
    charts.append(ChartSpec(
        name="KPI · Average Customer Sentiment",
        dataset="fct_customer_feedback",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="Mean NLP-derived sentiment score (−1 to +1).",
        params={
            "viz_type": "big_number_total",
            "metric": metric_avg("sentiment_score", "Avg Sentiment"),
            "y_axis_format": ".3f",
            "subheader": "Range [−1, +1]",
        },
    ))

    # 8. Premium Mix (Business + PE share of bookings)
    charts.append(ChartSpec(
        name="KPI · Premium Mix",
        dataset="fct_bookings",
        viz_type="big_number_total",
        page_tag=PAGE,
        description="Share of bookings in Business or Premium Economy.",
        params={
            "viz_type": "big_number_total",
            "metric": metric_sql(
                "SUM(CASE WHEN fare_class IN ('Business','Premium Economy') THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0)",
                "Premium Mix",
            ),
            "y_axis_format": ".1%",
            "subheader": "Premium cabin share",
        },
    ))

    # Mini-trend 1: revenue trend over months (line)
    charts.append(ChartSpec(
        name="Overview · Revenue Trend (monthly)",
        dataset="int_route_monthly_perf",
        viz_type="line",
        page_tag=PAGE,
        description="Total revenue per month across all routes.",
        params={
            "viz_type": "line",
            "x_axis": "period_month",
            "metrics": [metric_sum("revenue_usd", "Revenue")],
            "groupby": [],
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "y_axis_format": "$,.0f",
            "show_legend": False,
        },
    ))

    # Mini-trend 2: Top 5 revenue routes (bar horizontal)
    charts.append(ChartSpec(
        name="Overview · Top 5 Routes by Revenue",
        dataset="int_route_monthly_perf",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Top 5 routes by total revenue, sorted descending.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sum("revenue_usd", "Revenue")],
            "groupby": ["route_id"],
            "row_limit": 5,
            "order_desc": True,
            "color_scheme": "supersetColors",
            "y_axis_format": "$,.0f",
            "show_legend": False,
        },
    ))

    # ═══ PAGE 1 — NETWORK & PROFITABILITY (7 charts) ═══════════════════════
    PAGE = "network_profitability"

    # 1.1 Revenue by route (bar)
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

    # 1.2 Route opportunity matrix: Margin% × Load Factor × Revenue bubble
    charts.append(ChartSpec(
        name="Net · Route Opportunity Matrix",
        dataset="int_route_monthly_perf",
        viz_type="bubble",
        page_tag=PAGE,
        description=("Margin % vs Load Factor per route. Bubble size = revenue. "
                     "Top-right quadrant = invest; bottom-left = reconsider."),
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

    # 1.3 OTP15 trend (line, monthly)
    charts.append(ChartSpec(
        name="Net · OTP15 Trend (monthly)",
        dataset="int_route_monthly_perf",
        viz_type="line",
        page_tag=PAGE,
        description="Monthly on-time performance (≤15 min) across operated flights.",
        params={
            "viz_type": "line",
            "x_axis": "period_month",
            "metrics": [metric_avg("otp15_rate", "OTP15")],
            "groupby": [],
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "y_axis_format": ".1%",
            "show_legend": False,
        },
    ))

    # 1.4 Cancellation rate trend (line)
    charts.append(ChartSpec(
        name="Net · Cancellation Rate Trend",
        dataset="int_route_monthly_perf",
        viz_type="line",
        page_tag=PAGE,
        description="Monthly cancellation rate, all routes combined.",
        params={
            "viz_type": "line",
            "x_axis": "period_month",
            "metrics": [metric_avg("cancellation_rate", "Cancel Rate")],
            "groupby": [],
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "y_axis_format": ".1%",
            "show_legend": False,
        },
    ))

    # 1.5 Revenue per available seat-km (RASK) by route_type
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

    # 1.6 Load factor by route_type (bar)
    charts.append(ChartSpec(
        name="Net · Load Factor by Route Type",
        dataset="fct_flights",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Average load factor per route_type.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sql(
                "SUM(pax_count) / NULLIF(SUM(seat_capacity), 0)",
                "Load Factor",
            )],
            "groupby": ["route_type"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "y_axis_format": ".1%",
        },
    ))

    # 1.7 Disruption breakdown table
    charts.append(ChartSpec(
        name="Net · Disruptions by Type",
        dataset="fct_flights",
        viz_type="table",
        page_tag=PAGE,
        description="Count of disruptions per type, sortable.",
        params={
            "viz_type": "table",
            "query_mode": "aggregate",
            "groupby": ["disruption_type"],
            "metrics": [metric_count("Disruption Count")],
            "row_limit": 25,
            "order_desc": True,
            "adhoc_filters": [{
                "expressionType": "SIMPLE",
                "subject": "disruption_type",
                "operator": "IS NOT NULL",
            }],
        },
    ))

    # ═══ PAGE 2 — CUSTOMER & RETENTION (7 charts) ═══════════════════════════
    PAGE = "customer_retention"

    # 2.1 Customer segmentation (pie)
    charts.append(ChartSpec(
        name="Cust · Segment Distribution",
        dataset="dim_customer_current",
        viz_type="pie",
        page_tag=PAGE,
        description="Customer base by segment.",
        params={
            "viz_type": "pie",
            "metric": metric_count("Customers"),
            "groupby": ["customer_segment"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "show_legend": True,
        },
    ))

    # 2.2 Loyalty tier distribution (pie)
    charts.append(ChartSpec(
        name="Cust · Loyalty Tier Distribution",
        dataset="dim_customer_current",
        viz_type="pie",
        page_tag=PAGE,
        description="Customer base by loyalty tier (incl. non-member).",
        params={
            "viz_type": "pie",
            "metric": metric_count("Customers"),
            "groupby": ["loyalty_tier_safe"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "show_legend": True,
        },
    ))

    # 2.3 Top high-value at-risk customers (table)
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

    # 2.4 Route × complaint category heatmap (last 12 months)
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
            "color_scheme": "fvictronicMostInformative",
            "linear_color_scheme": "schemeBlues",
        },
    ))

    # 2.5 Sentiment trend (line, monthly)
    charts.append(ChartSpec(
        name="Cust · Sentiment Trend (monthly)",
        dataset="fct_customer_feedback",
        viz_type="line",
        page_tag=PAGE,
        description="Average sentiment score per month.",
        params={
            "viz_type": "line",
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

    # 2.6 Loyal Detractor table (ontology)
    charts.append(ChartSpec(
        name="Cust · Loyal Detractors (Gold tier)",
        dataset="ont_loyal_detractor",
        viz_type="table",
        page_tag=PAGE,
        description="Gold-tier frequent flyers with negative 6-month sentiment — early-warning signal.",
        params={
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": [
                "customer_id", "customer_segment", "frequency_12m",
                "feedback_count_6m", "avg_sentiment_6m", "negative_count_6m",
            ],
            "order_by_cols": ['["avg_sentiment_6m",true]'],
            "row_limit": 50,
        },
    ))

    # 2.7 CLV distribution (histogram)
    charts.append(ChartSpec(
        name="Cust · LTV Distribution",
        dataset="int_customer_lifetime",
        viz_type="histogram",
        page_tag=PAGE,
        description="Distribution of customer lifetime value (LTV proxy).",
        params={
            "viz_type": "histogram",
            "all_columns_x": ["ltv_proxy_usd"],
            "row_limit": 1000,
            "bins": 30,
            "color_scheme": "supersetColors",
        },
    ))

    # ═══ PAGE 3 — UPSELL & CROSS-SELL (6 charts) ═══════════════════════════
    PAGE = "upsell_crosssell"

    # 3.1 Offer acceptance rate by offer type
    charts.append(ChartSpec(
        name="Up · Acceptance Rate by Offer Type",
        dataset="fct_ancillary_offers",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Share of presented offers that get accepted, by offer type.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sql(
                "SUM(CASE WHEN accepted_flag THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(CASE WHEN presented_flag THEN 1 ELSE 0 END), 0)",
                "Acceptance Rate",
            )],
            "groupby": ["offer_type"],
            "row_limit": 15,
            "order_desc": True,
            "color_scheme": "supersetColors",
            "y_axis_format": ".1%",
        },
    ))

    # 3.2 Ancillary revenue per pax (ARPP) by fare class
    charts.append(ChartSpec(
        name="Up · ARPP by Fare Class",
        dataset="fct_bookings",
        viz_type="dist_bar",
        page_tag=PAGE,
        description="Ancillary revenue per booking (proxy for ARPP), by fare class.",
        params={
            "viz_type": "dist_bar",
            "metrics": [metric_sql(
                "SUM(ancillary_revenue_usd) / NULLIF(COUNT(*), 0)",
                "ARPP",
            )],
            "groupby": ["fare_class"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "y_axis_format": "$,.2f",
        },
    ))

    # 3.3 Ancillary attach rate by customer segment
    charts.append(ChartSpec(
        name="Up · Attach Rate by Segment",
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

    # 3.4 Total ancillary revenue trend (line)
    charts.append(ChartSpec(
        name="Up · Ancillary Revenue Trend",
        dataset="fct_bookings",
        viz_type="line",
        page_tag=PAGE,
        description="Total ancillary revenue per month.",
        params={
            "viz_type": "line",
            "x_axis": "booking_date",
            "metrics": [metric_sum("ancillary_revenue_usd", "Ancillary Revenue")],
            "groupby": [],
            "time_grain_sqla": "P1M",
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "y_axis_format": "$,.0f",
            "show_legend": False,
        },
    ))

    # 3.5 Premium Upsell Candidates table (ontology)
    charts.append(ChartSpec(
        name="Up · Premium Upsell Candidates (top 30)",
        dataset="ont_premium_upsell_candidate",
        viz_type="table",
        page_tag=PAGE,
        description="Customers flagged by the ont_premium_upsell_candidate concept.",
        params={
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": [
                "customer_id", "customer_segment", "loyalty_tier",
                "upgrade_offers_presented", "upgrade_offers_accepted",
                "upgrade_acceptance_rate",
            ],
            "order_by_cols": ['["upgrade_acceptance_rate",false]'],
            "row_limit": 30,
        },
    ))

    # 3.6 Loyalty points earned over time
    charts.append(ChartSpec(
        name="Up · Loyalty Points Earned (monthly)",
        dataset="fct_loyalty_events",
        viz_type="line",
        page_tag=PAGE,
        description="Total loyalty points earned per month (excludes redemptions).",
        params={
            "viz_type": "line",
            "x_axis": "event_date",
            "metrics": [metric_sum("points_earned", "Points Earned")],
            "groupby": [],
            "time_grain_sqla": "P1M",
            "row_limit": 50,
            "color_scheme": "supersetColors",
            "show_legend": False,
        },
    ))

    # ═══ PAGE 4 — DECISION LAYER (4 action-oriented tables) ═══════════════════
    PAGE = "decision_layer"

    # 4.1 Routes to GROW (top by margin × load factor, last 12 months)
    charts.append(ChartSpec(
        name="Dec · Routes to GROW (top profitable + busy)",
        dataset="int_route_monthly_perf",
        viz_type="table",
        page_tag=PAGE,
        description="Routes with margin % and load factor both above median — invest more capacity.",
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

    # 4.2 Routes to DEFEND (ontology: strategic underperforming + IROPS heavy)
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

    # 4.3 Customers to RETAIN (high-value at risk)
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

    # 4.4 Offers to PRIORITIZE (premium upsell candidates)
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
                "upgrade_acceptance_rate", "acceptance_percentile",
            ],
            "order_by_cols": ['["upgrade_acceptance_rate",false]'],
            "row_limit": 50,
        },
    ))

    return charts


# ─────────────────────────────────────────────────────────────────────────────
# Superset client
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
        # Hybrid auth: JWT for the Authorization header AND a session cookie
        # from the form login. The chart-create endpoint requires a "real"
        # authenticated user via session cookies (JWT alone yields
        # AnonymousUserMixin in Superset 4.1's chart_create flow).
        import re
        r = self.session.get(f"{self.base_url}/login/", timeout=30)
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
        form_csrf = m.group(1) if m else ""
        self.session.post(
            f"{self.base_url}/login/",
            data={"username": self.username, "password": self.password,
                  "csrf_token": form_csrf},
            allow_redirects=True,
            timeout=30,
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
    """Read existing slice_names from the Superset metastore via docker exec.
    Superset 4.1.2's API list endpoint hides API-created charts by default,
    so we read directly from SQLite — same approach as setup_datasets.py.

    Returns an empty set if Superset is not running on Docker (graceful fallback).
    """
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

    # Pre-fetch existing chart names from the metastore (idempotence support)
    existing_names = fetch_existing_chart_names()
    if existing_names:
        print(f"  (Found {len(existing_names)} existing charts in metastore — will skip duplicates)")

    created = 0
    existing = 0
    failed = 0
    failure_details: list[str] = []
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
            # Re-run to capture the actual error message
            r = client.session.post(
                f"{client.base_url}/api/v1/chart/",
                headers=client._hdr(),
                json={
                    "slice_name": spec.name,
                    "datasource_id": ds_id,
                    "datasource_type": "table",
                    "viz_type": spec.viz_type,
                    "params": json.dumps({**spec.params, "datasource": f"{ds_id}__table"}),
                },
                timeout=30,
            )
            err = f"  ✗ {spec.name:<50s} FAILED status={r.status_code} body={r.text[:250]}"
            print(err)
            failure_details.append(err)
            failed += 1

    print(f"\n>>> Summary")
    print(f"    Created : {created}")
    print(f"    Existing: {existing}")
    print(f"    Failed  : {failed}")
    print(f"    Total   : {len(charts)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Air Côte d'Ivoire MCP Server — small tool layer for an AI assistant.

Three tools, exactly what the brief's three grounded questions need:
  1. list_routes_with_kpis        → "Which routes deserve more budget?"
  2. list_high_value_at_risk_customers → "Which high-value customers are at risk?"
  3. search_feedback_text         → "What complaints drive low satisfaction on route X?"
                                     (the unstructured source)

Transport: stdio. Run with `python -m mcp_server`. Configure Claude Desktop
via `mcp_server/claude_desktop_config.json`.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from mcp_server.safety import safe_query

mcp = FastMCP(
    name="Air Côte d'Ivoire Analytics",
    instructions=(
        "Three tools cover the Air Côte d'Ivoire growth-allocation decision: "
        "list_routes_with_kpis for network/operations questions, "
        "list_high_value_at_risk_customers for retention questions, "
        "and search_feedback_text for what customers actually wrote "
        "(the unstructured source). Quote raw_text excerpts when summarising "
        "route satisfaction."
    ),
)


# ─── Tool 1 ─ Routes with their KPIs (network + ops question) ───────────

@mcp.tool()
def list_routes_with_kpis(
    period_months: Annotated[int, Field(ge=1, le=24)] = 12,
    limit: Annotated[int, Field(ge=1, le=50)] = 20,
) -> dict:
    """Return one row per route with its core KPIs over the trailing window:
    revenue, margin %, load factor, OTP15, cancellation rate.

    Use when the user asks "which routes deserve more budget?" or any
    profitability/operations question on routes. Sort the rows yourself
    based on what the user prioritises (margin, revenue, load, etc.)."""
    sql = """
        WITH cutoff AS (
            SELECT MAX(period_month) AS latest FROM main_intermediate.int_route_monthly_perf
        ),
        win AS (
            SELECT *
            FROM main_intermediate.int_route_monthly_perf p, cutoff c
            WHERE p.period_month > c.latest - INTERVAL (? || ' months')::INTERVAL
        )
        SELECT
            route_id,
            ROUND(SUM(revenue_usd), 0)                                        AS revenue_usd,
            ROUND(SUM(margin_usd) / NULLIF(SUM(revenue_usd), 0), 4)           AS margin_pct,
            ROUND(SUM(total_pax)::DOUBLE / NULLIF(SUM(total_seat_capacity), 0), 4) AS load_factor,
            ROUND(AVG(otp15_rate), 4)                                         AS otp15_rate,
            ROUND(AVG(cancellation_rate), 4)                                  AS cancellation_rate
        FROM win
        GROUP BY route_id
        ORDER BY revenue_usd DESC
        LIMIT ?
    """
    return safe_query(
        sql, [period_months, limit],
        description=f"Routes with their KPIs over the trailing {period_months} months",
    )


# ─── Tool 2 ─ High-Value At-Risk Customers (retention question) ─────────

@mcp.tool()
def list_high_value_at_risk_customers(
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
) -> dict:
    """Return the customers flagged HIGH-VALUE AT RISK by the ontology
    (above-median lifetime spend + above-median recency + dissatisfaction
    signal: complaint OR negative sentiment OR churn risk ≥ 0.40).

    Use when the user asks who to retain, which VIPs are slipping, etc."""
    sql = """
        SELECT customer_id, recency_days, monetary_total_usd,
               ltv_proxy_usd, complaint_count, avg_sentiment, churn_risk_score
        FROM main_ontology.ont_high_value_at_risk_customer
        ORDER BY ltv_proxy_usd DESC
        LIMIT ?
    """
    return safe_query(
        sql, [limit],
        description=f"Top {limit} high-value at-risk customers",
    )


# ─── Tool 3 ─ Search Feedback Text (UNSTRUCTURED source) ────────────────

@mcp.tool()
def search_feedback_text(
    route_id: Annotated[Optional[str], Field(description="Route filter (e.g. 'R005').")] = None,
    sentiment_label: Annotated[
        Literal["negative", "neutral", "positive", "any"],
        Field(description="Sentiment band ('any' = no filter)."),
    ] = "any",
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> dict:
    """Return raw customer feedback text (FR/EN) enriched with NLP-derived
    sentiment and complaint_category. This is the project's UNSTRUCTURED
    data source.

    Use when the user asks "what complaints are driving low satisfaction
    on route X?" or wants verbatim customer voice. Quote 2-4 raw_text
    excerpts when summarising a route's issues."""
    where: list[str] = []
    params: list = []
    if route_id:
        where.append("route_id = ?")
        params.append(route_id)
    if sentiment_label != "any":
        where.append("sentiment_label = ?")
        params.append(sentiment_label)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)

    sql = f"""
        SELECT feedback_id, feedback_date, route_id, customer_id, language,
               sentiment_score, sentiment_label, complaint_category, raw_text
        FROM main_marts.fct_customer_feedback
        {where_sql}
        ORDER BY sentiment_score ASC, feedback_date DESC
        LIMIT ?
    """
    return safe_query(
        sql, params,
        description=(
            f"Feedback search (route={route_id or 'any'}, "
            f"sentiment={sentiment_label}, limit={limit})"
        ),
    )

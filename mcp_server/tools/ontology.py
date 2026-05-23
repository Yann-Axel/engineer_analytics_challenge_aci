"""
Ontology tools — expose the 5 inferred business concepts as MCP tools.

The LLM reads each tool's docstring to decide when to call it, so every
docstring is written from the *business user's* angle: "use this tool when
the user asks for X".

Each tool returns a uniform JSON envelope from `safe_query()` containing
the SQL executed, params bound, row count, and the rows themselves — the
LLM can present any subset to the user.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from mcp_server.server import mcp
from mcp_server.safety import safe_query


# ─────────────────────────────────────────────────────────────────────────
# 1. High-Value At-Risk Customers
# ─────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_high_value_at_risk_customers(
    limit: Annotated[int, Field(ge=1, le=200, description="How many customers to return")] = 20,
    sort_by: Annotated[
        Literal["ltv", "monetary", "recency"],
        Field(description="Sort key: 'ltv' (proxy lifetime value), 'monetary' (total spend), 'recency' (days since last booking, descending)"),
    ] = "ltv",
) -> dict:
    """List customers flagged HIGH-VALUE BUT AT RISK by the ontology.

    Use this tool when the user asks any of:
      - "Which high-value customers are at risk of churn?"
      - "Who should I retain this quarter?"
      - "Which VIPs are showing warning signs?"

    The underlying concept (`ont_high_value_at_risk_customer`) flags
    customers with above-median lifetime spend AND above-median recency
    (i.e. inactive recently) AND a dissatisfaction signal (complaint,
    negative sentiment, or churn risk >= 0.40).

    Returns one row per customer with: customer_id, recency_days,
    monetary_total_usd, ltv_proxy_usd, complaint_count, avg_sentiment,
    churn_risk_score.
    """
    order_col = {
        "ltv":      "ltv_proxy_usd DESC",
        "monetary": "monetary_total_usd DESC",
        "recency":  "recency_days DESC",
    }[sort_by]

    sql = f"""
        SELECT customer_id,
               recency_days,
               monetary_12m_usd,
               monetary_total_usd,
               ltv_proxy_usd,
               complaint_count,
               avg_sentiment,
               churn_risk_score
        FROM main_ontology.ont_high_value_at_risk_customer
        ORDER BY {order_col}
        LIMIT ?
    """
    return safe_query(
        sql, [limit],
        description=f"Top {limit} high-value at-risk customers, sorted by {sort_by}",
    )


# ─────────────────────────────────────────────────────────────────────────
# 2. Strategic Underperforming Routes
# ─────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_strategic_underperforming_routes(
    limit: Annotated[int, Field(ge=1, le=20)] = 10,
) -> dict:
    """List routes flagged STRATEGIC BUT UNDERPERFORMING by the ontology.

    Use this tool when the user asks any of:
      - "Which strategic routes are underperforming?"
      - "Where should we defend our network?"
      - "Long-haul routes losing money?"

    The concept (`ont_strategic_underperforming_route`) flags routes
    where `is_strategic = true` AND margin sits in the bottom half of
    strategic peers AND load factor remains >= 0.65 (demand exists,
    profitability lags).

    Returns: route_id, distance_band, revenue_12m, margin_pct_12m,
    load_factor_12m, avg_cancellation_rate.
    """
    sql = """
        SELECT route_id,
               distance_band,
               flights_operated_12m,
               revenue_12m,
               margin_12m_usd,
               margin_pct_12m,
               load_factor_12m,
               avg_cancellation_rate,
               avg_otp15
        FROM main_ontology.ont_strategic_underperforming_route
        ORDER BY margin_pct_12m ASC
        LIMIT ?
    """
    return safe_query(
        sql, [limit],
        description=f"Top {limit} strategic underperforming routes (worst margin first)",
    )


# ─────────────────────────────────────────────────────────────────────────
# 3. Premium Upsell Candidates
# ─────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_premium_upsell_candidates(
    segment: Annotated[
        Literal["Standard", "Business", "any"],
        Field(description="Customer segment filter ('any' = no filter)"),
    ] = "any",
    tier: Annotated[
        Literal["Silver", "Gold", "any"],
        Field(description="Loyalty tier filter ('any' = no filter)"),
    ] = "any",
    limit: Annotated[int, Field(ge=1, le=200)] = 30,
) -> dict:
    """List customers most likely to ACCEPT a PREMIUM UPSELL OFFER.

    Use this tool when the user asks any of:
      - "Which customers should I push premium offers to?"
      - "Best upsell candidates?"
      - "Who has high upgrade acceptance?"

    The concept (`ont_premium_upsell_candidate`) flags Standard/Business
    segment customers in Silver/Gold tier whose upgrade-offer acceptance
    rate is in the top quartile.

    Returns: customer_id, customer_segment, loyalty_tier,
    upgrade_offers_presented, upgrade_offers_accepted,
    upgrade_acceptance_rate.
    """
    where = []
    params: list = []
    if segment != "any":
        where.append("customer_segment = ?")
        params.append(segment)
    if tier != "any":
        where.append("loyalty_tier = ?")
        params.append(tier)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)

    sql = f"""
        SELECT customer_id,
               customer_segment,
               loyalty_tier,
               upgrade_offers_presented,
               upgrade_offers_accepted,
               upgrade_acceptance_rate,
               acceptance_percentile
        FROM main_ontology.ont_premium_upsell_candidate
        {where_sql}
        ORDER BY upgrade_acceptance_rate DESC
        LIMIT ?
    """
    return safe_query(
        sql, params,
        description=f"Premium upsell candidates (segment={segment}, tier={tier}, limit={limit})",
    )


# ─────────────────────────────────────────────────────────────────────────
# 4. Loyal Detractors
# ─────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_loyal_detractors(
    min_frequency: Annotated[int, Field(ge=1, le=50, description="Minimum flown segments in last 12 months")] = 4,
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
) -> dict:
    """List GOLD-TIER FREQUENT FLYERS who are SIGNALLING DISSATISFACTION.

    Use this tool when the user asks any of:
      - "Which Gold customers are unhappy?"
      - "Loyal detractors?"
      - "Early-warning signals on top tier?"

    The concept (`ont_loyal_detractor`) flags Gold-tier customers with
    >= 4 flown segments in 12 months AND average 6-month sentiment < -0.3.
    These are the most expensive customers to lose — high LTV, hard to
    replace.

    Returns: customer_id, customer_segment, frequency_12m,
    feedback_count_6m, avg_sentiment_6m, negative_count_6m.
    """
    sql = """
        SELECT customer_id,
               customer_segment,
               loyalty_tier,
               frequency_12m,
               feedback_count_6m,
               avg_sentiment_6m,
               negative_count_6m
        FROM main_ontology.ont_loyal_detractor
        WHERE frequency_12m >= ?
        ORDER BY avg_sentiment_6m ASC, frequency_12m DESC
        LIMIT ?
    """
    return safe_query(
        sql, [min_frequency, limit],
        description=f"Loyal detractors (Gold, frequency >= {min_frequency}, limit {limit})",
    )


# ─────────────────────────────────────────────────────────────────────────
# 5. IROPS-Heavy Routes
# ─────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_irops_heavy_routes() -> dict:
    """List routes with HIGH OPERATIONAL FRAGILITY (disruptions OR cancellations).

    Use this tool when the user asks any of:
      - "Which routes have the most disruptions / cancellations?"
      - "Where are our ops issues?"
      - "Routes losing margin to operations rather than weak demand?"

    The concept (`ont_irops_heavy_route`) flags routes where either the
    12-month disruption percentile is >= 0.80 OR cancellation rate > 5%.
    These are the routes the COO should prioritise: even a small
    operational improvement reclaims margin and customer sentiment.

    Returns: route_id, route_type, is_strategic, total_flights_12m,
    cancellation_rate_12m, disruption_rate_12m, disruption_percentile.
    """
    sql = """
        SELECT route_id,
               route_type,
               distance_band,
               is_strategic,
               total_flights_12m,
               cancellations_12m,
               disruptions_12m,
               cancellation_rate_12m,
               disruption_rate_12m,
               disruption_percentile
        FROM main_ontology.ont_irops_heavy_route
        ORDER BY disruption_rate_12m DESC
    """
    return safe_query(
        sql, [],
        description="All IROPS-heavy routes (operational fragility)",
    )

"""
KPI tools — expose the semantic-layer headline metrics in one call.

We deliberately ship ONE consolidated tool here (`get_network_summary`)
rather than 8 separate KPI tools. Rationale:
  * The 8 headline KPIs are always interpreted together in an executive
    context (you don't look at Margin without Load Factor).
  * One LLM call replaces 8 → faster response, smaller context footprint.
  * Filtering by `route_id` answers route-level questions with the same
    contract.
"""
from __future__ import annotations

from typing import Annotated, Optional

from pydantic import Field

from mcp_server.server import mcp
from mcp_server.safety import safe_query


@mcp.tool()
def get_network_summary(
    period_months: Annotated[
        int,
        Field(ge=1, le=24, description="Trailing window in months (1-24), relative to the latest flight date in the dataset"),
    ] = 12,
    route_id: Annotated[
        Optional[str],
        Field(description="Optional route filter (e.g. 'R009'). Omit for network-wide."),
    ] = None,
) -> dict:
    """Return the 8 HEADLINE KPIs of the airline for the given window.

    Use this tool when the user asks any of:
      - "How is the network doing this quarter?"
      - "Give me the headline KPIs"
      - "What's the state of route X?" (set route_id)
      - "How profitable are we?"

    Returns a single row with:
      - total_revenue_usd
      - route_margin_pct         (revenue − operating cost) / revenue
      - load_factor              passengers / seat capacity
      - otp15_rate               on-time (≤15 min) over operated flights
      - cancellation_rate        cancelled / scheduled
      - ancillary_attach_rate    bookings with ancillary / total bookings
      - avg_sentiment_score      mean NLP-derived sentiment, range [-1, +1]
      - premium_cabin_mix        Business + Premium-Economy bookings / total
      - period_start, period_end, route_id_filter

    All KPIs are aligned with the definitions in
    `dbt/models/semantic/_metrics.yml`.
    """
    # Bind parameters for SQL: route filter applied to multiple subqueries.
    rf_flights  = "AND f.route_id = ?"             if route_id else ""
    rf_bookings = "AND b.route_id = ?"             if route_id else ""
    rf_feedback = "AND fb.route_id = ?"            if route_id else ""

    # We chain the same param `route_id` three times if it is set.
    params: list = []
    # period_months × 3 + route_id × 3 (if set) — order matters
    params.extend([period_months])                         # flights filter
    if route_id: params.append(route_id)
    params.extend([period_months])                         # bookings filter
    if route_id: params.append(route_id)
    params.extend([period_months])                         # feedback filter
    if route_id: params.append(route_id)
    params.extend([period_months])                         # period_start
    params.extend([period_months])                         # period_end (max date in window)
    if route_id: params.append(route_id)                   # final route echo

    sql = f"""
        WITH cutoff AS (
            SELECT (SELECT MAX(flight_date) FROM main_marts.fct_flights) AS latest_date
        ),
        flight_kpis AS (
            SELECT
                SUM(f.total_revenue_usd)                              AS revenue,
                SUM(f.flight_margin_usd)                              AS margin_usd,
                SUM(f.pax_count)                                      AS pax,
                SUM(f.seat_capacity)                                  AS seats,
                SUM(CASE WHEN f.is_on_time_15 THEN 1 ELSE 0 END)      AS on_time,
                SUM(CASE WHEN f.flight_status <> 'Cancelled' THEN 1 ELSE 0 END) AS operated,
                SUM(CASE WHEN f.is_cancelled THEN 1 ELSE 0 END)       AS cancelled,
                COUNT(*)                                              AS scheduled
            FROM main_marts.fct_flights f, cutoff c
            WHERE f.flight_date >= c.latest_date - INTERVAL (? || ' months')::INTERVAL
              {rf_flights}
        ),
        booking_kpis AS (
            SELECT
                COUNT(*)                                              AS bookings,
                SUM(CASE WHEN b.ancillary_revenue_usd > 0 THEN 1 ELSE 0 END) AS with_ancillary,
                SUM(CASE WHEN b.is_premium_cabin THEN 1 ELSE 0 END)   AS premium_cabin
            FROM main_marts.fct_bookings b, cutoff c
            WHERE b.flight_date >= c.latest_date - INTERVAL (? || ' months')::INTERVAL
              {rf_bookings}
        ),
        feedback_kpis AS (
            SELECT AVG(fb.sentiment_score) AS avg_sent
            FROM main_marts.fct_customer_feedback fb, cutoff c
            WHERE fb.feedback_date >= c.latest_date - INTERVAL (? || ' months')::INTERVAL
              {rf_feedback}
        )
        SELECT
            ROUND(fk.revenue, 2)                                                       AS total_revenue_usd,
            ROUND(fk.margin_usd / NULLIF(fk.revenue, 0), 4)                           AS route_margin_pct,
            ROUND(fk.pax::DOUBLE / NULLIF(fk.seats, 0), 4)                            AS load_factor,
            ROUND(fk.on_time::DOUBLE / NULLIF(fk.operated, 0), 4)                     AS otp15_rate,
            ROUND(fk.cancelled::DOUBLE / NULLIF(fk.scheduled, 0), 4)                  AS cancellation_rate,
            ROUND(bk.with_ancillary::DOUBLE / NULLIF(bk.bookings, 0), 4)              AS ancillary_attach_rate,
            ROUND(fb.avg_sent, 4)                                                     AS avg_sentiment_score,
            ROUND(bk.premium_cabin::DOUBLE / NULLIF(bk.bookings, 0), 4)               AS premium_cabin_mix,
            (SELECT (latest_date - INTERVAL (? || ' months')::INTERVAL)::DATE FROM cutoff) AS period_start,
            (SELECT latest_date FROM cutoff)                                           AS period_end,
            ? AS period_months,
            {'?' if route_id else 'NULL'} AS route_id_filter
        FROM flight_kpis fk, booking_kpis bk, feedback_kpis fb
    """

    return safe_query(
        sql, params,
        description=(
            f"Network summary KPIs over the trailing {period_months} months"
            + (f" for route {route_id}" if route_id else " (all routes)")
        ),
    )

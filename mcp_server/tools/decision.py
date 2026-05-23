"""
Decision-support tool — side-by-side comparison of two routes.

Answers the brief's acceptance question:
"Compare two routes using both financial and satisfaction signals."

Returns 2 rows (one per route) so the LLM can present them in a table
or a narrative paragraph. Both financial (revenue, margin, LF, OTP15,
cancel rate) AND satisfaction signals (avg sentiment, complaint count,
top complaint category) are included — that's the whole point.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.server import mcp
from mcp_server.safety import safe_query


@mcp.tool()
def compare_routes(
    route_id_a: Annotated[str, Field(min_length=2, max_length=10, description="First route id (e.g. 'R009')")],
    route_id_b: Annotated[str, Field(min_length=2, max_length=10, description="Second route id (e.g. 'R008')")],
    period_months: Annotated[int, Field(ge=1, le=24)] = 12,
) -> dict:
    """COMPARE TWO ROUTES side-by-side on FINANCIAL + SATISFACTION signals.

    Use this tool when the user asks any of:
      - "Compare route ABJ-CDG and ABJ-LOS"
      - "How does R009 stack up against R008?"
      - "Which of these two routes should we prioritise?"

    Returns 2 rows (one per route) with:
      - route_id, route_type, distance_band, is_strategic
      - revenue_usd, margin_pct, load_factor          (financial)
      - otp15_rate, cancellation_rate, disruption_rate (operational)
      - avg_sentiment_score, feedback_count, top_complaint_category (customer)

    The LLM should turn this into a 2-column side-by-side table and
    interpret the diff — "route A has better margin but worse sentiment",
    "route B is operationally fragile despite higher load factor", etc.
    """
    sql = """
        WITH cutoff AS (
            SELECT MAX(flight_date) AS latest_date FROM main_marts.fct_flights
        ),
        flight_kpis AS (
            SELECT
                f.route_id,
                SUM(f.total_revenue_usd)                                  AS revenue_usd,
                SUM(f.flight_margin_usd) / NULLIF(SUM(f.total_revenue_usd), 0)   AS margin_pct,
                SUM(f.pax_count)::DOUBLE / NULLIF(SUM(f.seat_capacity), 0)       AS load_factor,
                SUM(CASE WHEN f.is_on_time_15 THEN 1 ELSE 0 END)::DOUBLE
                    / NULLIF(SUM(CASE WHEN f.flight_status <> 'Cancelled' THEN 1 ELSE 0 END), 0) AS otp15_rate,
                SUM(CASE WHEN f.is_cancelled THEN 1 ELSE 0 END)::DOUBLE
                    / NULLIF(COUNT(*), 0)                                 AS cancellation_rate,
                SUM(CASE WHEN f.has_disruption THEN 1 ELSE 0 END)::DOUBLE
                    / NULLIF(COUNT(*), 0)                                 AS disruption_rate,
                COUNT(*)                                                  AS flights_count
            FROM main_marts.fct_flights f, cutoff c
            WHERE f.flight_date >= c.latest_date - INTERVAL (? || ' months')::INTERVAL
              AND f.route_id IN (?, ?)
            GROUP BY f.route_id
        ),
        feedback_kpis AS (
            SELECT
                route_id,
                AVG(sentiment_score)                                      AS avg_sentiment_score,
                COUNT(*)                                                  AS feedback_count,
                SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_count
            FROM main_marts.fct_customer_feedback fb, cutoff c
            WHERE fb.feedback_date >= c.latest_date - INTERVAL (? || ' months')::INTERVAL
              AND fb.route_id IN (?, ?)
            GROUP BY route_id
        ),
        top_category AS (
            -- For each route, the dominant complaint category in the window
            SELECT route_id, complaint_category, cnt
            FROM (
                SELECT route_id,
                       complaint_category,
                       COUNT(*) AS cnt,
                       ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY COUNT(*) DESC) AS rk
                FROM main_marts.fct_customer_feedback fb, cutoff c
                WHERE fb.feedback_date >= c.latest_date - INTERVAL (? || ' months')::INTERVAL
                  AND fb.route_id IN (?, ?)
                GROUP BY route_id, complaint_category
            )
            WHERE rk = 1
        )
        SELECT
            r.route_id,
            r.route_type,
            r.distance_band,
            r.is_strategic,
            ROUND(fk.revenue_usd, 2)         AS revenue_usd,
            ROUND(fk.margin_pct, 4)          AS margin_pct,
            ROUND(fk.load_factor, 4)         AS load_factor,
            ROUND(fk.otp15_rate, 4)          AS otp15_rate,
            ROUND(fk.cancellation_rate, 4)   AS cancellation_rate,
            ROUND(fk.disruption_rate, 4)     AS disruption_rate,
            fk.flights_count,
            ROUND(fb.avg_sentiment_score, 4) AS avg_sentiment_score,
            fb.feedback_count,
            fb.negative_count,
            tc.complaint_category            AS top_complaint_category,
            tc.cnt                           AS top_complaint_count
        FROM main_marts.dim_route r
        LEFT JOIN flight_kpis    fk USING (route_id)
        LEFT JOIN feedback_kpis  fb USING (route_id)
        LEFT JOIN top_category   tc USING (route_id)
        WHERE r.route_id IN (?, ?)
        ORDER BY CASE WHEN r.route_id = ? THEN 0 ELSE 1 END
    """

    params = [
        period_months, route_id_a, route_id_b,   # flight_kpis
        period_months, route_id_a, route_id_b,   # feedback_kpis
        period_months, route_id_a, route_id_b,   # top_category
        route_id_a, route_id_b,                  # final filter
        route_id_a,                              # ordering: A first
    ]

    return safe_query(
        sql, params,
        description=(
            f"Side-by-side comparison of {route_id_a} vs {route_id_b} "
            f"over the trailing {period_months} months "
            f"(financial + operational + customer signals)"
        ),
    )

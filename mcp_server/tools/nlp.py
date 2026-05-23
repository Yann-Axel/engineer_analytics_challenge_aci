"""
NLP tool — the bridge from unstructured (raw_text) to the LLM.

This is the tool that satisfies the brief's explicit requirement:
"The AI interface must be able to use both structured data and at least
one unstructured source."

It exposes the raw customer feedback text alongside its NLP-derived
annotations (sentiment_score, sentiment_label, complaint_category) so
the LLM can:
  * cite verbatim what customers actually wrote
  * filter to a route or a sentiment band
  * search for a topic keyword across 3,000 feedbacks

This is what lets the agent ground its answer when the user asks
"What complaints are driving low satisfaction on route X?".
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import Field

from mcp_server.server import mcp
from mcp_server.safety import safe_query


@mcp.tool()
def search_feedback_text(
    query: Annotated[
        Optional[str],
        Field(description="Free-text keyword to match (case-insensitive) inside raw_text. Omit to skip text filtering."),
    ] = None,
    route_id: Annotated[
        Optional[str],
        Field(description="Route filter (e.g. 'R005' for ABJ-DKR)."),
    ] = None,
    sentiment_label: Annotated[
        Literal["negative", "neutral", "positive", "any"],
        Field(description="Sentiment band to restrict to ('any' = no filter)."),
    ] = "any",
    complaint_category: Annotated[
        Optional[str],
        Field(description="Complaint category filter (e.g. 'delay', 'baggage', 'crew', 'food', 'seat', 'booking_app', 'lounge', 'upgrade', 'refund', 'general'). Omit to skip."),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> dict:
    """SEARCH RAW CUSTOMER FEEDBACK TEXT enriched with NLP signals.

    Use this tool when the user asks any of:
      - "What complaints are driving low satisfaction on route X?"
      - "Show me what customers are saying about Y"
      - "Find feedback mentioning Z"
      - "Sample negative feedback on route R005"

    Returns up to `limit` feedback rows with the raw text and its
    NLP-derived annotations:
      - feedback_id, feedback_date, route_id, customer_id
      - raw_text   (the verbatim FR/EN customer feedback)
      - language   ('fr', 'en', or 'fr+en')
      - sentiment_score, sentiment_label
      - complaint_category

    Sorted by sentiment_score ASCENDING (most negative first) when
    `sentiment_label` is 'negative' or 'any', otherwise by feedback_date
    descending (most recent first).

    The LLM should quote 2-4 representative `raw_text` excerpts when
    summarising complaint themes — that's the difference between
    "structured insight" and "grounded insight".
    """
    where: list[str] = []
    params: list = []

    if query:
        where.append("LOWER(raw_text) LIKE LOWER(?)")
        params.append(f"%{query}%")
    if route_id:
        where.append("route_id = ?")
        params.append(route_id)
    if sentiment_label != "any":
        where.append("sentiment_label = ?")
        params.append(sentiment_label)
    if complaint_category:
        where.append("complaint_category = ?")
        params.append(complaint_category)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    # Sort: most negative first if the user is hunting for negatives,
    # otherwise most recent first.
    if sentiment_label == "negative" or sentiment_label == "any":
        order_sql = "ORDER BY sentiment_score ASC, feedback_date DESC"
    else:
        order_sql = "ORDER BY feedback_date DESC, sentiment_score ASC"

    params.append(limit)

    sql = f"""
        SELECT feedback_id,
               feedback_date,
               route_id,
               customer_id,
               feedback_channel,
               language,
               sentiment_score,
               sentiment_label,
               complaint_category,
               raw_text
        FROM main_marts.fct_customer_feedback
        {where_sql}
        {order_sql}
        LIMIT ?
    """

    desc_parts = ["Feedback search"]
    if query:              desc_parts.append(f"query='{query}'")
    if route_id:           desc_parts.append(f"route={route_id}")
    if sentiment_label != "any": desc_parts.append(f"sentiment={sentiment_label}")
    if complaint_category: desc_parts.append(f"category={complaint_category}")
    desc_parts.append(f"limit={limit}")

    return safe_query(sql, params, description=" | ".join(desc_parts))

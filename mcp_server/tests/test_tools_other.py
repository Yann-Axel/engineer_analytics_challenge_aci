"""Tests for the KPI, NLP and decision tools, plus the glossary resource."""
from __future__ import annotations

import asyncio

from mcp_server.server import mcp
from mcp_server.tools.decision import compare_routes
from mcp_server.tools.kpis import get_network_summary
from mcp_server.tools.nlp import search_feedback_text


def _assert_envelope(result):
    assert "error" not in result, f"Tool errored: {result.get('error')}"
    for k in ("sql", "row_count", "rows", "description"):
        assert k in result


# ─── KPI tool ───────────────────────────────────────────────────────────

def test_network_summary_network_wide():
    result = get_network_summary(period_months=12)
    _assert_envelope(result)
    assert result["row_count"] == 1
    row = result["rows"][0]
    # All 8 headline KPIs present
    for col in ("total_revenue_usd", "route_margin_pct", "load_factor",
                "otp15_rate", "cancellation_rate", "ancillary_attach_rate",
                "avg_sentiment_score", "premium_cabin_mix"):
        assert col in row
    # Sanity: load factor is a fraction in [0, 1.05]
    assert 0 <= row["load_factor"] <= 1.05


def test_network_summary_route_filtered():
    result = get_network_summary(period_months=12, route_id="R009")
    _assert_envelope(result)
    row = result["rows"][0]
    assert row["route_id_filter"] == "R009"
    # R009 (long-haul CDG) should generate substantial revenue
    assert row["total_revenue_usd"] > 10_000_000


# ─── NLP / unstructured tool ────────────────────────────────────────────

def test_search_feedback_text_negative_on_route():
    result = search_feedback_text(route_id="R005", sentiment_label="negative", limit=5)
    _assert_envelope(result)
    assert result["row_count"] > 0
    for row in result["rows"]:
        assert row["route_id"] == "R005"
        assert row["sentiment_label"] == "negative"
        assert row["sentiment_score"] < 0
        assert row["raw_text"]  # not empty


def test_search_feedback_text_keyword():
    result = search_feedback_text(query="bagage", limit=3)
    _assert_envelope(result)
    assert result["row_count"] > 0
    for row in result["rows"]:
        assert "bagage" in row["raw_text"].lower()


# ─── Decision tool ──────────────────────────────────────────────────────

def test_compare_routes_returns_two_rows():
    result = compare_routes("R009", "R005", period_months=12)
    _assert_envelope(result)
    assert result["row_count"] == 2
    route_ids = [r["route_id"] for r in result["rows"]]
    # The first row is route_a per ORDER BY in the SQL
    assert route_ids[0] == "R009"
    assert route_ids[1] == "R005"
    # Both rows carry financial + customer signals
    for row in result["rows"]:
        for col in ("revenue_usd", "margin_pct", "load_factor",
                    "avg_sentiment_score", "feedback_count",
                    "top_complaint_category"):
            assert col in row


# ─── Resource ───────────────────────────────────────────────────────────

def test_glossary_resource_is_readable():
    """The airline glossary resource must be registered and non-empty."""
    async def _read():
        resources = await mcp.list_resources()
        assert any(str(r.uri) == "glossary://airline-business" for r in resources)
        content = await mcp.read_resource("glossary://airline-business")
        text = content[0].content if hasattr(content[0], "content") else str(content)
        return text

    text = asyncio.run(_read())
    assert "Load Factor" in text
    assert "IROPS" in text
    assert "ontology" in text.lower()
    assert len(text) > 2000  # rich enough to be useful

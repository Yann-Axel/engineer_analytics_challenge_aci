"""Smoke tests for the 5 ontology tools.

Each test ensures:
  * The tool returns the safe_query envelope (no raise).
  * row_count > 0 — i.e. the ontology table is populated.
  * Expected columns are present in the first row.
"""
from __future__ import annotations

from mcp_server.tools.ontology import (
    list_high_value_at_risk_customers,
    list_irops_heavy_routes,
    list_loyal_detractors,
    list_premium_upsell_candidates,
    list_strategic_underperforming_routes,
)


def _assert_envelope(result):
    assert "error" not in result, f"Tool errored: {result.get('error')}"
    for k in ("sql", "row_count", "rows", "description"):
        assert k in result


def test_high_value_at_risk_customers():
    result = list_high_value_at_risk_customers(limit=5, sort_by="ltv")
    _assert_envelope(result)
    assert result["row_count"] > 0
    first = result["rows"][0]
    for col in ("customer_id", "recency_days", "monetary_total_usd",
                "ltv_proxy_usd", "complaint_count", "churn_risk_score"):
        assert col in first


def test_strategic_underperforming_routes():
    result = list_strategic_underperforming_routes(limit=10)
    _assert_envelope(result)
    # 2 strategic routes flagged in the demo dataset
    assert result["row_count"] >= 1
    first = result["rows"][0]
    for col in ("route_id", "margin_pct_12m", "load_factor_12m"):
        assert col in first


def test_premium_upsell_candidates_unfiltered():
    result = list_premium_upsell_candidates(segment="any", tier="any", limit=10)
    _assert_envelope(result)
    assert result["row_count"] > 0
    first = result["rows"][0]
    assert first["customer_segment"] in ("Standard", "Business")
    assert first["loyalty_tier"] in ("Silver", "Gold")


def test_premium_upsell_candidates_filtered_to_gold():
    result = list_premium_upsell_candidates(tier="Gold", limit=20)
    _assert_envelope(result)
    for row in result["rows"]:
        assert row["loyalty_tier"] == "Gold"


def test_loyal_detractors():
    result = list_loyal_detractors(min_frequency=4, limit=5)
    _assert_envelope(result)
    assert result["row_count"] > 0
    for row in result["rows"]:
        assert row["frequency_12m"] >= 4
        assert row["avg_sentiment_6m"] < -0.3  # the ontology rule


def test_irops_heavy_routes_count():
    result = list_irops_heavy_routes()
    _assert_envelope(result)
    # Calibrated to expose 5 routes after Phase 0 recalibration.
    assert result["row_count"] == 5
    route_ids = {r["route_id"] for r in result["rows"]}
    assert "R015" in route_ids  # the most fragile route in the demo dataset

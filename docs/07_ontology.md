# Part 2 — Ontology layer (5 business concepts + declarative rules)

The ontology is the **senior differentiator** explicitly called out by the brief:
> *"For senior differentiation, add an ontology-inspired layer or explicit reasoning rules that classify business concepts such as High-Value At-Risk Customer or Strategic but Underperforming Route."*

## Why a SQL + YAML hybrid (not OWL/SHACL)

| Option | Pro | Con | Verdict |
|---|---|---|---|
| OWL/Turtle/SHACL (formal RDF) | Standard, supports reasoners | Heavy stack, illegible for BI/MCP, no consumer | ❌ Overkill |
| Pure SQL `ont_*` views | Simple | Loses the declarative business rule | ⚠️ Insufficient |
| **SQL `ont_*` tables + YAML declarative rules** | Both executable and explainable | Slight maintenance overhead | ✅ **Chosen** |

The SQL **executes** the rule (and is consumed by the dashboard and MCP). The YAML **describes** the rule in business language (and is consumed by humans / audit).

## The 5 concepts

| Concept | Rule (declarative) | Rows produced | Business owner | Refresh |
|---|---|---|---|---|
| **HighValueAtRiskCustomer** | `monetary_total_percentile >= 0.60` AND `recency_percentile >= 0.60` AND (`complaint_count >= 1` OR `avg_sentiment < 0` OR `churn_risk_score >= 0.40`) | 20 | Chief Customer Officer | weekly |
| **StrategicUnderperformingRoute** | `is_strategic = true` AND `margin_percentile_among_strategic <= 0.50` AND `load_factor_12m >= 0.65` | 2 | VP Network | monthly |
| **PremiumUpsellCandidate** | `customer_segment IN ('Standard','Business')` AND `loyalty_tier IN ('Silver','Gold')` AND `acceptance_percentile >= 0.75` | 48 | Ancillary Manager | monthly |
| **LoyalDetractor** | `loyalty_tier = 'Gold'` AND `frequency_12m >= 4` AND `avg_sentiment_6m < -0.3` | 22 | Loyalty Manager | weekly |
| **IROPSHeavyRoute** | `disruption_percentile_12m >= 0.80` OR `cancellation_rate_12m > 0.05` | 5 | COO / Ops Director | weekly |

## Acceptance-question mapping

The 5 concepts directly answer 3 of the 6 suggested acceptance questions in the brief:

| Brief question | Concept answering it |
|---|---|
| "Which high-value customers are at risk of churn?" | `ont_high_value_at_risk_customer` |
| "Which routes look unprofitable because of operational issues rather than weak demand?" | `ont_irops_heavy_route` (ops) + `ont_strategic_underperforming_route` (demand-vs-margin) |
| "Which customer segments should receive premium upgrade or ancillary offers?" | `ont_premium_upsell_candidate` |

## Design choice: percentile-based thresholds

We deliberately use **relative thresholds** (percentiles, percent_rank) rather than absolute ones:

- `monetary_total_percentile >= 0.60` instead of `monetary_total_usd > 5000`
- `disruption_percentile_12m >= 0.90` instead of `disruption_rate > 0.10`

Why senior:
1. **Portable across datasets**: rules still work if the airline grows, contracts, or restates costs.
2. **Self-calibrating**: the "top 10% of disruption" is meaningful regardless of the absolute baseline.
3. **Avoids arbitrary numbers**: no need to defend "why 180 days?" — it's "the worst 25% of recency in our data".

## Singular tests on ontology

Three custom tests in `dbt/tests/`:
- `assert_at_risk_customers_have_dissatisfaction_signal.sql` — every HighValueAtRiskCustomer must carry a signal
- `assert_strategic_underperforming_routes_are_strategic.sql` — sanity-check on `is_strategic`
- `assert_loyal_detractor_is_gold.sql` — tier consistency

All passing.

## Consumption pattern

### Dashboard (Part 3)
A widget "Top 10 customers at risk" becomes:
```sql
SELECT * FROM main_ontology.ont_high_value_at_risk_customer
ORDER BY ltv_proxy_usd DESC LIMIT 10
```

### MCP / AI agent (Part 4)
The agent exposes 5 tools, one per concept:
```
list_high_value_at_risk_customers()
list_strategic_underperforming_routes()
list_premium_upsell_candidates()
list_loyal_detractors()
list_irops_heavy_routes()
```
Each tool just runs `SELECT * FROM main_ontology.<concept>`. **No business logic in the prompt.**

## Declarative rules YAML (extract)

See [docs/05_ontology_rules.yml](05_ontology_rules.yml) for the full machine-readable rules.

```yaml
concept: HighValueAtRiskCustomer
description: "A customer with substantial lifetime spend who has disengaged AND is signalling dissatisfaction."
business_owner: Chief Customer Officer
refresh_frequency: weekly
inputs:
  - source: int_customer_lifetime
  - source: fct_customer_feedback
rule:
  monetary_total_percentile: ">= 0.60"
  recency_percentile:        ">= 0.60"
  signal:                    "complaint_count >= 1 OR avg_sentiment < 0 OR churn_risk_score >= 0.40"
output: ont_high_value_at_risk_customer
```

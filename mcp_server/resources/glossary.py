"""
Airline business glossary — static MCP resource.

The LLM reads this BEFORE answering business questions, so it speaks the
right vocabulary (RASK vs Yield, LF vs OTP, IROPS, etc.) and knows which
tool to invoke for which concept.

URI: glossary://airline-business
"""
from __future__ import annotations

from mcp_server.server import mcp


GLOSSARY_MARKDOWN = """\
# Air Côte d'Ivoire analytics — business glossary

## Operational KPIs

| Term | Definition |
|---|---|
| **Load Factor (LF)** | Passengers carried / seat capacity available. Industry target 75-85%. Higher = better revenue per flight. |
| **OTP15** | On-Time Performance: share of operated flights with departure delay ≤ 15 minutes. Excludes cancelled flights. |
| **Cancellation rate** | Cancelled flights / scheduled flights. Industry alarm at > 5%. |
| **Block hours** | Time the aircraft is moving under its own power: gate departure → gate arrival. Costs are priced per block hour. |
| **IROPS** | Irregular Operations — disruptions, cancellations, diversions, lengthy delays. Carries direct costs (rebook, hotel, EU261-like compensation) AND indirect costs (customer trust). |

## Commercial KPIs

| Term | Definition |
|---|---|
| **Route Revenue** | Sum of ticket + ancillary revenue from Flown bookings on a route. |
| **Direct Operating Cost** | Fuel + crew + airport fees + maintenance allocation + IROPS penalties. |
| **Route Margin %** | (Revenue − Direct Operating Cost) / Revenue. |
| **Yield (RASK)** | Revenue per Available Seat-Kilometre. Comparable metric across short / long-haul. |
| **Ancillary Attach Rate** | Share of bookings with at least one ancillary purchase (seat selection, extra bag, lounge, upgrade…). |
| **ARPP** | Ancillary Revenue Per Passenger. |
| **Premium Mix** | Share of bookings in Business + Premium Economy cabins. |

## Customer KPIs

| Term | Definition |
|---|---|
| **RFM** | Recency (days since last booking), Frequency (bookings in 12 months), Monetary (revenue in 12 months). |
| **LTV / CLV** | (Customer) Lifetime Value — projected cumulative revenue per customer. |
| **Repeat Booking Rate** | Share of bookings by customers with ≥ 2 bookings. |
| **Churn Risk Score** | 0–1 composite of recency, frequency, sentiment. |
| **NPS / Sentiment** | Net Promoter Score / mean NLP sentiment score on customer feedback. |

## Fare structure

| Term | Definition |
|---|---|
| **Fare class** | Economy, Premium Economy, Business |
| **Fare family** | Basic (restrictive), Standard, Flex (changeable, refundable) |
| **Premium cabin** | Business + Premium Economy combined |

## Customer attributes

| Term | Definition |
|---|---|
| **Segment** | Budget, Standard, Business, Premium (assigned at customer level) |
| **Loyalty tier** | Explorer → Silver → Gold → (non-member). Earns points per km × tier multiplier. |

## Network

| Term | Definition |
|---|---|
| **Hub** | Abidjan (ABJ) — the airline's home base and connecting hub. |
| **Route type** | Domestic (Côte d'Ivoire only), Regional (West/North Africa), International (Europe, Middle East). |
| **Distance band** | Short-haul < 800 km, Medium-haul 800–3500 km, Long-haul > 3500 km. |
| **Strategic route** | Flagged `is_strategic = true` in `dim_route`. Currently: R009/R013 (ABJ-CDG pair), R014 (ABJ-CMN), R016 (ABJ-DXB candidate). |

## Ontology concepts (derived)

| Concept | Tool to invoke | When the user asks… |
|---|---|---|
| **High-Value At-Risk Customer** | `list_high_value_at_risk_customers` | "Which VIPs are slipping?", "Who to retain?" |
| **Strategic Underperforming Route** | `list_strategic_underperforming_routes` | "Which strategic routes underperform peers?" |
| **Premium Upsell Candidate** | `list_premium_upsell_candidates` | "Who is best for premium offers?" |
| **Loyal Detractor** | `list_loyal_detractors` | "Which Gold members are unhappy?" |
| **IROPS-Heavy Route** | `list_irops_heavy_routes` | "Where are our ops issues?" |

## Tool reference

| Question pattern | Tool |
|---|---|
| "How is the network/route X doing?" | `get_network_summary(period_months, route_id?)` |
| "What complaints on route X?" | `search_feedback_text(route_id='R005', sentiment_label='negative')` |
| "Compare route A and B" | `compare_routes(route_id_a, route_id_b)` |

## How the agent should chain tools (typical patterns)

* "Where should we invest budget next quarter?"
  → `get_network_summary` for context → `list_strategic_underperforming_routes` →
    `list_high_value_at_risk_customers` → `list_premium_upsell_candidates` →
    synthesise the 40/35/25 allocation.

* "What complaints drive low satisfaction on route X?"
  → `get_network_summary(route_id=X)` → `search_feedback_text(route_id=X, sentiment_label='negative')` →
    quote 2–4 verbatim feedbacks per dominant complaint category.

* "Compare route A vs B"
  → `compare_routes(A, B)` → optionally `search_feedback_text(route_id=A)` and same for B
    to back the comparison with customer voice.

## Unit conventions

All monetary values are in **USD**. Distances in **km**. Times in **minutes**.
All percentages are returned as fractions in `[0, 1]`.
"""


@mcp.resource("glossary://airline-business")
def airline_glossary() -> str:
    """Static glossary of Air Côte d'Ivoire analytics vocabulary, KPIs,
    ontology concepts, and tool-routing patterns. The LLM should consult
    this resource before answering any business question."""
    return GLOSSARY_MARKDOWN

# Part 2 — Semantic layer (entities, dimensions, measures, 24 KPIs)

The semantic layer is the **business-friendly contract** between the warehouse and the consumers (dashboard, MCP agent).

## Files

| File | Purpose |
|---|---|
| `dbt/models/semantic/_semantic_models.yml` | 5 business entities + dimensions + atomic measures |
| `dbt/models/semantic/_metrics.yml` | 24 KPIs (21 atomic `m_*` + 12 business KPIs, total 33 metric definitions) |
| `dbt/models/semantic/metricflow_time_spine.sql` + `_time_spine.yml` | Daily time spine required by MetricFlow |

## 5 semantic entities

| Entity | Source (mart) | Primary key | Foreign keys |
|---|---|---|---|
| `flight` | `fct_flights` | `flight` (`flight_sk`) | `route`, `aircraft`, `origin_airport`, `destination_airport` |
| `booking` | `fct_bookings` | `booking` (`booking_sk`) | `customer`, `flight`, `route`, `fare` |
| `feedback` | `fct_customer_feedback` | `feedback` (`feedback_sk`) | `customer`, `route` |
| `ancillary_offer` | `fct_ancillary_offers` | `offer` (`ancillary_offer_sk`) | `booking`, `customer`, `fare` |
| `loyalty_event` | `fct_loyalty_events` | `event` (`loyalty_event_sk`) | `customer`, `route` |

## 24 KPIs mapped to themes

### Theme 1 — Route Optimization & Growth (8)

| KPI metric | Type | Description |
|---|---|---|
| `route_revenue` | simple | Ticket + ancillary revenue, filtered to Flown only |
| `m_total_operating_cost` | simple | Sum of fuel + crew + airport + maintenance + IROPS |
| `m_total_margin` | simple | `route_revenue - m_total_operating_cost` |
| `route_margin_pct` | ratio | `m_total_margin / m_total_revenue` |
| `load_factor` | ratio | `m_pax_count / m_seat_capacity` |
| `yield_rask` | derived | Revenue per available seat-km |
| `otp15_rate` | ratio | On-Time ≤ 15 min over operated flights |
| `cancellation_rate` | ratio | Cancelled / scheduled |

### Theme 2 — Customer Retention (8)

| KPI metric | Type | Description |
|---|---|---|
| `m_bookings_count`, `m_unique_customers` | simple | Atomic counts |
| `repeat_booking_rate` | derived | (bookings − unique customers) / bookings |
| `avg_sentiment` | simple | Mean sentiment score (NLP output) |
| `feedback_volume` | simple | Count of feedback in the period |
| `negative_feedback_share` | ratio | Negative feedback / total feedback |
| `gold_loyalty_events` | simple | Loyalty events made under Gold tier |
| `loyalty_points_earned` | simple | Total points earned |

### Theme 3 — Upsell / Cross-sell (8)

| KPI metric | Type | Description |
|---|---|---|
| `ancillary_attach_rate` | ratio | Bookings with ancillary / bookings |
| `arpp` | derived | Ancillary revenue per passenger |
| `m_ancillary_revenue` | simple | Atomic measure |
| `offer_acceptance_rate` | ratio | Accepted / presented offers |
| `upgrade_conversion_rate` | ratio | Same, filtered to upgrade offer types |
| `avg_ticket_price` | derived | Ticket revenue / booking count |
| `m_pax_count` | simple | Atomic measure |

## How a consumer queries this

Two equivalent contracts exist on top of dbt 1.11:

1. **MetricFlow CLI / Cloud**: `mf query --metrics load_factor --group-by metric_time__month`
2. **Direct SQL**: any of the marts can be queried directly with `from main_marts.fct_flights`

The **dashboard** (Part 3) and the **MCP server** (Part 4) will consume metrics via SQL on the marts, with the metric definitions in `_metrics.yml` as the spec a human can verify against.

## Why a separate atomic layer (`m_*`)

dbt 1.11 ratio/derived metrics must compose **metrics**, not raw measures. Exposing every measure as a simple `m_*` metric:
1. Decouples ratio composition from semantic_model internals
2. Makes the metric YAML self-explanatory
3. Maps cleanly to BI tools that consume metric definitions

## Single source of truth

Every KPI is defined here **exactly once**. If a business owner wants to redefine "Route Margin", they edit `_metrics.yml` — no SQL, no dashboard rework.

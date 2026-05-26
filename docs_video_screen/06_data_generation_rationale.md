# Part 1 — Data generation rationale

> **Brief requirement (Part 1):** *"Explain which new data you created, why it matters, and how it changes the business recommendations."*

Every entry below ends with a **counterfactual** ("without this file the recommendation becomes…") so the value of each enrichment is measured by what the leadership decision would lose.

**Companion docs_video_screen:** [03_assumptions.md](03_assumptions.md) (8 modelling choices), [02_data_dictionary.md](02_data_dictionary.md) (column reference), [10_executive_recommendations.md](10_executive_recommendations.md) (the verdict whose numbers we trace back here).

---

## Overview

The starter pack ships 5 entities (`airports`, `routes`, `customers`, `flights`, `bookings`). The Part-1 pipeline produces **10 new files** plus re-enriched versions of the 5 starter ones, all in `data/enriched/`.

| Status      | File                              | Rows         | Brief example tag                                       |
| :---------- | :-------------------------------- | :----------- | :------------------------------------------------------ |
| New         | `customer_feedback.parquet`       | 3,000        | unstructured (mandatory)                                |
| New         | `flight_costs.parquet`            | ~8,750       | fuel cost / ops cost                                    |
| New         | `ancillary_offers.parquet`        | ~3.3 M       | ancillaries                                             |
| New         | `disruptions.parquet`             | ~1,800       | disruption logs                                         |
| New         | `loyalty_activity.parquet`        | ~650 K       | loyalty activity                                        |
| New         | `weather_daily.parquet`           | ~9,500       | weather proxies                                         |
| New         | `aircraft.parquet`                | 9            | aircraft / manufacturer / fleet assignment              |
| New         | `cargo_shipments.parquet`         | ~5,600       | (not in brief examples; A330 widebody business context) |
| New         | `competitors.parquet`             | ~600         | competitor context                                      |
| New         | `customers_activity_meta.parquet` | 1,000        | internal — reproducibility of long-tail                 |
| Re-enriched | `routes.parquet`                  | 12 → 16      | + `is_strategic`, + 4 candidate routes                  |
| Re-enriched | `customers.parquet`               | 300 → 1,000  | + 700 with realistic segment/tier mix                   |
| Re-enriched | `flights.parquet`                 | ~8,750       | 24-month schedule with seasonality                      |
| Re-enriched | `bookings.parquet`                | ~1.1 M       | volume aligned to load-factor targets                   |
| Re-enriched | `airports.parquet`                | 10 → 13      | + CMN, LFW, DXB for expansion routes                    |

**Brief example-list coverage: 12 of 13** (Aircraft, manufacturer, fleet assignment, fuel cost, fare family, ancillaries, loyalty activity, support tickets, disruption logs, weather proxies, competitor context, unstructured feedback). Two soft gaps are documented at the end.

---

## A. New entities — one-by-one defence

### A1. `customer_feedback.parquet` — the brief's mandatory unstructured dataset

- **What:** 3,000 free-text customer feedback rows, bilingual (FR 65 % / EN 30 % / mixed 5 %), with `feedback_channel ∈ {support_ticket, review, social_post}`. **Raw text only** — sentiment, category and tags are derived by the dbt NLP pipeline in Part 2.
- **Starter gap:** the brief requires *"at least one unstructured dataset"*; the starter has none.
- **KPIs unlocked:** `customer_sentiment`, complaint volume by category, route-level issue themes, sentiment trend.
- **Ontology concepts unlocked:** half of `HighValueAtRiskCustomer` (complaints, negative sentiment), all of `LoyalDetractor`, the complaint-theme heatmap.
- **Impact on the recommendation:** Action 2 (*"Retention campaign on 20 high-value at-risk customers"* worth **$0.7 M/yr recurring**) is entirely derived from this file — each of the 20 customers carries ≥ 1 complaint or negative sentiment.
- **Counterfactual:** no unstructured source → brief Part 1 fails its hard requirement; no `HighValueAtRisk` cohort identifiable; no MCP tool #3; the verdict 40 / 35 / **25** loses its third pillar.
- **Calibration:** feedback rate ~1.8 % per booking, bumped to 8.5 % on disrupted flights and 2.5 % on Business class. Polarity: 75 % negative when the underlying flight was disrupted, 35 % otherwise. Templates in [scripts/lib/feedback_templates.py](../scripts/lib/feedback_templates.py).

### A2. `flight_costs.parquet` — per-flight operating cost decomposition

- **What:** 1 row per flight with `fuel_cost_usd`, `crew_cost_usd`, `airport_fees_usd`, `maintenance_alloc_usd`, `irops_penalty_usd`, `total_operating_cost_usd`.
- **Starter gap:** starter has revenue (`bookings.ticket_price_usd`) but **no cost**. Without cost: no margin, no yield, no RASK/CASK, no "profitable growth" — which is literally the brief's question.
- **KPIs unlocked:** `route_margin_pct`, `flight_margin_usd`, route ranking by profitability.
- **Ontology concept unlocked:** `StrategicUnderperformingRoute` (percentile computed on `margin_pct_12m`).
- **Impact on the recommendation:** the **40 % ops stabilisation verdict** is quantified at `~$200 K/yr of cancellations avoided` on 5 IROPS-heavy routes. The dollar figure exists only because `irops_penalty_usd` exists.
- **Counterfactual:** the recommendation degrades to *"improve OTP on some routes"* — descriptive, non-prioritisable, non-budgetable.
- **Calibration:** block-hour rate per aircraft type ($3.4 K A319, $3.6 K A320, $2.9 K A320neo, $7.2 K A330), decomposed 55 / 22 / 13 / 10 %; cancelled flights use reduced ratios + `Gamma(5, 800)` IROPS penalty. Full design in [03_assumptions.md §5](03_assumptions.md).

### A3. `ancillary_offers.parquet` — every offer presented, accepted or not

- **What:** ~3.3 M rows with `presented_flag`, `accepted_flag`, `offer_type ∈ {seat_selection, extra_bag, upgrade_W, upgrade_J, lounge_access, priority_board}`. **Every presentation is logged**, not just acceptances.
- **Starter gap:** starter has `bookings.ancillary_revenue_usd` (aggregate $) but no per-offer trace — you can see total ancillary money but not who got which offer.
- **KPIs unlocked:** `ancillary_attach_rate`, acceptance rate per offer type, upgrade conversion, revenue per passenger.
- **Ontology concept unlocked:** `PremiumUpsellCandidate` (top-quartile acceptance requires presented as denominator, accepted as numerator).
- **Impact on the recommendation:** Action 3 (*"Premium upgrade offers on 48 candidates"* worth **$1.5–3 M new ancillary**) depends on `ont_premium_upsell_candidate`.
- **Counterfactual:** upsell becomes descriptive ("we collect $X in ancillary"), not targeted — recommend "push more offers", not "to whom".
- **Calibration:** per-type base acceptance (seat 45 %, bag 30 %, upgrade_W 10 %, upgrade_J 5 %, lounge 15 %, priority 20 %), multiplied 1.7× for Premium, 1.4× for Business, 1.3× for Gold. Multipliers act on segment/tier; the concept filters on percentile (avoids circular self-justification).

### A4. `disruptions.parquet` — operational failure events with free-text root cause

- **What:** ~1,800 disruption events with `disruption_type ∈ {Weather, Technical, ATC, Crew, Other}`, `severity`, `duration_min`, and a **bilingual free-text `root_cause_text`** column (a second unstructured source).
- **Starter gap:** starter has `flight_status` and `delay_min` but no *cause* — you see a delay but can't tell weather from a tech or crew issue, and those have completely different action levers.
- **KPIs unlocked:** disruption rate per route, root-cause breakdown, mean time between disruptions per tail.
- **Ontology concept unlocked:** `IROPSHeavyRoute`.
- **Impact on the recommendation:** Action 1 — *"Ops task force on R015 / R005 / R008 / R004 / R006"*. These are precisely the top-quintile disruption percentile **OR** > 5 % cancellation rate routes.
- **Counterfactual:** the 40 % ops allocation is unjustified, the 5 named routes shrink to "routes that look bad on OTP", and the COO has nothing to brief his team with on Monday.
- **Calibration:** type mix 35 / 25 / 15 / 15 / 10 with **monsoon bump** (55 % Weather in Jun–Aug at ABJ). Full design in [03_assumptions.md §6](03_assumptions.md).

### A5. `loyalty_activity.parquet` — earn and redeem events per member

- **What:** ~650 K loyalty events (1 earn per flown booking for members, ~2 % redemption rate). Includes `tier_at_event` (tier changes over time — SCD2 input).
- **Starter gap:** starter has a static `loyalty_tier` on the customer record — no history, no engagement signal.
- **KPIs unlocked:** `loyalty_engagement`, redemption rate, tier-at-booking-time for fair retention KPIs.
- **Ontology concept unlocked:** `LoyalDetractor` (needs `frequency_12m` and `tier`).
- **Impact on the recommendation:** feeds the 35 % retention pillar — the dashboard's Loyalty Engagement chart and the SCD2 snapshot on `dim_customer.loyalty_tier` both depend on this file.
- **Counterfactual:** no tier-at-booking-time → retention KPIs use "current tier" anachronistically (a customer who churned from Gold to Silver gets counted as Silver retroactively).
- **Calibration:** points-per-km multiplier per tier (Explorer 1.0, Silver 1.25, Gold 1.5); redemption sizes drawn from {2 K, 5 K, 10 K, 20 K} points with descending probability.

### A6. `weather_daily.parquet` — daily weather proxy per airport

- **What:** ~9,500 rows (13 airports × 730 days) with `precipitation_mm`, `wind_kph`, `severity_flag`. Climate profiles by region (West African monsoon, Mediterranean winter, UAE dry).
- **Starter gap:** no weather data — every cancellation looks like an internal failure.
- **KPIs unlocked:** weather-correlated disruption rate, controllable-vs-exogenous IROPS split.
- **Ontology concept unlocked:** indirectly sharpens `IROPSHeavyRoute` — a route with 80 % weather-driven disruptions is *fragile but not fixable*; one with 80 % crew-driven is fixable.
- **Impact on the recommendation:** protects the credibility of Action 1. The risk disclaimer on monsoon (Jun–Aug) is defensible only because weather data exists.
- **Counterfactual:** the COO can rightly object *"R015's bad numbers are just the rainy season"* and the recommendation has no rebuttal.
- **Calibration:** Gamma-distributed precipitation, normal-distributed wind, climate baselines per country group, rainy months hard-coded to match regional seasons.

### A7. `aircraft.parquet` — fleet reference with cabin configuration

- **What:** 9 tails (TU-TSA → TU-TSI) with `aircraft_type`, `manufacturer`, `build_year`, cabin breakdown, `fleet_status ∈ {Owned, Leased}`.
- **Starter gap:** starter has `aircraft_type` flat on the flight — no cabin mix, no ownership, no canonical capacity.
- **KPIs unlocked:** `load_factor` per flight (needs `seat_capacity`), CASK by aircraft type, fleet age analytics, owned-vs-leased margin gap.
- **Ontology concept unlocked:** `StrategicUnderperformingRoute` filters on `load_factor_12m ≥ 0.65` — capacity must be known.
- **Impact on the recommendation:** the A330-900neo deployment cited in the brief is the basis for routes R009 / R013 / R014 / R016 being flagged strategic ([03_assumptions.md §7](03_assumptions.md)).
- **Counterfactual:** no per-flight capacity → no load factor → `StrategicUnderperformingRoute` cannot filter for "demand exists".
- **Calibration:** cabin configs based on Airbus published ranges (12J/12W/98Y for A319, 12J/18W/120Y for A320 family, 28J/21W/232Y for A330-900neo).

### A8. `cargo_shipments.parquet` — widebody / long-haul cargo revenue

- **What:** ~5,600 cargo shipments on long-haul (> 2,500 km) flights only, with `weight_kg`, `revenue_usd`, `cargo_type`, `shipper_country`.
- **Starter gap:** no cargo at all. The brief's business context explicitly mentions cargo as an adjacent product.
- **KPIs unlocked:** cargo revenue per flight, long-haul total margin (passenger + cargo), strategic-route P&L.
- **Ontology concept unlocked:** indirectly tightens `StrategicUnderperformingRoute` — ignoring cargo would understate strategic-route margin by 10–15 % and put non-strategic peers ahead.
- **Impact on the recommendation:** keeps the strategic-route P&L honest — eliminates the risk that R009 (ABJ–CDG) gets falsely flagged underperforming.
- **Counterfactual:** long-haul margin understated → false positives in `StrategicUnderperformingRoute` → wrong routes proposed for re-pricing.
- **Calibration:** 1–6 shipments per long-haul flight, weight `Gamma(2.5, 200)` clipped 50–4,000 kg, rate $4.5/kg (industry-typical for Africa–Europe).

### A9. `competitors.parquet` — monthly fare and frequency per competitor per route

- **What:** ~600 monthly snapshots of competitor `avg_fare_usd` and `weekly_frequency` (12 routes × 1–3 competitors × 24 months).
- **Starter gap:** starter has zero exogenous market view.
- **KPIs unlocked:** fare gap vs market, frequency share, capacity share.
- **Ontology concept unlocked:** none currently — competitors feed dashboard pricing context but no ontology concept is built on them in this submission.
- **Impact on the recommendation:** defends thresholds in the network pillar — *"raise fare by 5 %"* becomes argued, not asserted ("our fare is X % above market mean").
- **Counterfactual:** pricing recommendations have no benchmark.
- **Calibration:** per-route competitor lists curated against the real African competitive landscape (Air France / Brussels / RAM on Paris; Asky / Air Senegal on regional; Emirates / Ethiopian on Dubai). Base fare $150–900 with 7 % monthly noise.

### A10. `customers_activity_meta.parquet` — internal activity bucket per customer

- **What:** 1,000 rows mapping each `customer_id` to its activity bucket (inactive / occasional / regular / power_user) and target booking count over 24 months.
- **Starter gap:** starter has 100 % active customers — every retention KPI becomes degenerate.
- **KPIs unlocked:** indirectly all retention KPIs (Recency, RFM, Repeat Booking Rate) — they only become discriminating because of the long-tail.
- **Ontology concept unlocked:** indirectly `HighValueAtRiskCustomer` (uniform 100 % active gives a degenerate recency percentile).
- **Impact on the recommendation:** makes Action 2 (20 at-risk customers, $13.6 M LTV) statistically meaningful — with a flat 100 % active base the at-risk cohort would either be empty or include everyone.
- **Counterfactual:** bookings quasi-uniformly distributed → recency percentile collapses → `HighValueAtRiskCustomer` produces noise.
- **Calibration:** buckets `inactive 20 % / occasional 50 % / regular 25 % / power 5 %`. Aligned with flag-carrier benchmarks. Documented in [03_assumptions.md §3](03_assumptions.md).
- **Note:** deliberately **not exposed in the semantic layer** — generation artifact, not a business entity.

---

## B. Re-enriched starter files — what changed and why

| File                | Starter    | Enriched                                          | Why the enrichment matters                                                                                                                                                                |
| :------------------ | :--------- | :------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `routes.parquet`    | 12 rows    | 16 rows + `is_strategic` + `route_status`         | The 4 added candidate routes (CDG–ABJ return, Casa, Lomé, Dubai) come from the brief's expansion paragraph. `is_strategic` anchors the ontology concept. See [03_assumptions.md §7](03_assumptions.md). |
| `customers.parquet` | 300 active | 1,000 with long-tail                              | The 700 added customers carry a realistic segment / tier / channel / country mix (Côte d'Ivoire 30 %, France 18 %, etc.). Critical for percentile-based concepts.                          |
| `flights.parquet`   | flat list  | 24-month schedule with seasonal multipliers       | Two annual seasonality cycles + monsoon bump. Needed for any 12 m / 24 m KPI window.                                                                                                       |
| `bookings.parquet`  | small set  | ~1.1 M aligned to load-factor targets             | Volume calibrated to Domestic 72 % / Regional 78 % / International 82 % LF target. Denominator for ancillary attach, RFM, repeat-booking rate.                                              |
| `airports.parquet`  | 10         | 13 (+ CMN, LFW, DXB)                              | Required to support the expansion candidate routes.                                                                                                                                        |

---

## C. Traceability — recommendation → generated data

Every line of the executive recommendation is anchored to one or more generated files. Pick any row; the third column lists the generated files that produced it. Remove any of them and the fourth column shows the regression.

| Recommendation element                  | Headline number                  | Driving generated data                                                                          | What it becomes without that data                                              |
| :-------------------------------------- | :------------------------------- | :---------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------- |
| Verdict 40 / 35 / 25 % budget split     | qualitative                      | `flight_costs` + `customer_feedback` + `ancillary_offers`                                       | No allocation justified — three buckets become equal-weighted by default       |
| Action 1 — Ops task force on 5 routes   | ~$200 K/yr saved + sentiment lift| `disruptions` + `flight_costs.irops_penalty_usd` + `weather_daily`                              | "Improve OTP somewhere" — no list, no dollar figure                            |
| Action 2 — Retain 20 at-risk customers  | $13.6 M LTV → $0.7 M/yr saved    | `customer_feedback` + `loyalty_activity` + bookings-enriched + `customers_activity_meta`        | Concept exists in name only; no shortlist; no LTV figure                       |
| Action 3 — Premium upsell on 48 cand.   | $1.5–3 M new ancillary           | `ancillary_offers` + bookings.`fare_family` + customers.`loyalty_tier` mix                      | "Push more upgrades" — no segmentation, no expected value                      |
| 90-day OTP target ≥ 72 %                | KPI                              | `flight_costs` (cost of missing it) + `disruptions` (causes) + `weather_daily` (exogenous part) | Target without baseline or cost-of-failure                                     |
| Risk disclaimer on monsoon              | qualitative                      | `weather_daily`                                                                                 | No defensible answer to *"isn't this just bad weather?"*                       |

---

## D. Gaps vs the brief

The brief lists *"Aircraft, manufacturer, fleet assignment, fuel cost, fare family, ancillaries, loyalty activity, support tickets, disruption logs, baggage events, weather proxies, crew, or competitor context"* as examples. Two soft gaps:

- **Crew as a first-class entity** — covered indirectly through `crew_cost_usd` in `flight_costs` and `disruption_type = 'Crew'` in `disruptions`, but no rotation / qualification / base table. *Trade-off:* a full crew model (duty-time rules, qualifications, base-pairing) opens no new decision lever for the 3 brief themes. Captured at the *cost* and *cause* level instead.
- **Baggage events** — covered via `bookings.bags_count` (volume) and the `baggage` category in the complaints taxonomy ([dbt/seeds/complaint_taxonomy.csv](../dbt/seeds/complaint_taxonomy.csv)), but no dedicated event log (lost / delayed / found). *Trade-off:* synthetic baggage event data has no good public benchmark — would introduce uncalibrated noise.

Both are honest gaps and easy to add in a next iteration. Neither blocks any of the 3 recommendation pillars.

---

## E. Generation pipeline — reproducibility

```bash
python scripts/run_all.py               # ~2 min, SEED = 42
python scripts/99_validate_pipeline.py  # 24 / 24 PASS
```

Per-entity NumPy RNG streams (`scripts/lib/utils.py:get_rng(stream=N)`) — touching one generator does not perturb the others. Every knob lives in [scripts/lib/config.py](../scripts/lib/config.py). See [03_assumptions.md §8](03_assumptions.md).

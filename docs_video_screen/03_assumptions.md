# Part 1 — Assumptions

Eight load-bearing choices. All values are tunable in [scripts/lib/config.py](../scripts/lib/config.py).

### 1. Starter dataset preserved as-is

The 5 starter entities (airports, routes, customers, flights, bookings) sit untouched in `data/raw/`. Everything synthetic lives in `data/enriched/` — any new value is traceable to its source. The 300 starter customers carry through with their original IDs.

### 2. Time window — 24 months (2024-01-01 → 2025-12-31)

- 12 months is too short to compute churn (the 180-day recency signal needs history *before* the window starts).
- 24 months exposes two annual seasonality cycles.
- 36 months would slow the local DuckDB demo with no analytical gain.

### 3. Customer activity distribution

The starter has 100 % active customers (unrealistic). We add 700 new customers and impose a long-tail:

| Bucket     | Share | Bookings / 24 m |
| :--------- | :---- | :-------------- |
| Inactive   | 20 %  | 0               |
| Occasional | 50 %  | 1–5             |
| Regular    | 25 %  | 6–20            |
| Power user | 5 %   | 21–60           |

Result: ~80 % active base, aligned with flag-carrier benchmarks. Critical for the **Repeat Booking Rate** and **Recency** KPIs.

### 4. Unstructured feedback — the brief's mandatory dataset

- **3,000 rows** of free-text customer feedback in `customer_feedback.parquet`.
- **Bilingual:** FR 65 % / EN 30 % / mixed 5 % (reflects Air CIV's francophone-plus-international mix).
- **Raw text only** — sentiment, category and tags are *deliberately not stored at generation time*. They are derived by the Part-2 dbt NLP pipeline. This choice turns the dataset into a real unstructured-to-structured exercise instead of a relabelled lookup.
- Polarity correlates with operational reality: a feedback row linked to a disrupted flight is 75 % negative, vs 35 % otherwise.

### 5. Cost model — block-hour rate per aircraft type, with 4-way decomposition

The starter dataset provides revenue (via `bookings.ticket_price_usd`) but **no cost**. Without a cost model there is no margin, no `StrategicUnderperformingRoute`, no quantified ops verdict. The model is synthetic but industry-aligned.

| Aircraft type | Direct cost / block-hour (USD) |
| :------------ | :----------------------------- |
| A319          | 3,400                          |
| A320          | 3,600                          |
| A320neo       | 2,900 (lower — newer engines)  |
| A330-900neo   | 7,200 (widebody long-haul)     |

The block-hour total is decomposed per flight into **55 % fuel / 22 % crew / 13 % airport fees / 10 % maintenance** (small Gaussian noise around each ratio, clipped to plausible bands). For cancelled flights: fuel drops to 5 %, crew and airport fees to 30 %, maintenance to 10 % of nominal, plus an **IROPS penalty** drawn from `Gamma(5, 800)` ≈ $4 K median (covers rebooking, hotels, EC-261-style compensation).

- **Alternatives rejected:** a single flat $/seat-km (loses the type-mix signal that drives A320neo vs A319 cannibalisation), or sourcing real airline P&L (no public per-flight breakdown exists for Air CIV).
- **Impact if the assumption slips:** every margin figure on the dashboard shifts. The 78 % network margin headline is *optimistic* for synthetic data — [10_executive_recommendations.md](10_executive_recommendations.md) flags this in §Risks. The **ranking** of routes by margin is robust because the same model applies to all routes.

### 6. Disruption model — type mix, monsoon-aware, severity derived from delay

The starter has `flight_status` and `delay_min` but no separation between *what failed* and *what got recorded as a delay*. Without a disruption layer there is no `IROPSHeavyRoute`, no split between weather-driven and controllable cancellations, no Action 1 in the recommendation.

| Disruption type | Base probability | Note                                                       |
| :-------------- | :--------------- | :--------------------------------------------------------- |
| Weather         | 35 %             | Bumped to 55 % during Jun–Aug (West African monsoon at ABJ) |
| Technical       | 25 %             |                                                            |
| ATC             | 15 %             |                                                            |
| Crew            | 15 %             |                                                            |
| Other           | 10 %             | Bird strike, security, late baggage…                       |

**Cancellation rate by route type:** Domestic 3 % / Regional 4 % / International 2.5 %. Regional is highest because shorter sectors are more sensitive to upstream rotational delays at ABJ.

**Which flights get a disruption record:** every cancelled flight, every delay > 60 min, plus 30 % of delays in the 16–60 min band (the rest are treated as recoverable noise, not disruption events). Severity is derived from `delay_min`: > 180 min = Severe, > 60 min = Major, else Minor.

- **Alternatives rejected:** a flat 5 % disruption rate across all flights (loses the seasonality that makes `IROPSHeavyRoute` interpretable), or a Markov chain on rotational delay propagation (justified for a real-time ops tool, overkill for an analytics product).
- **Impact if the assumption slips:** changes the disruption percentile distribution. The five routes named in [10_executive_recommendations.md](10_executive_recommendations.md) (R015 / R005 / R008 / R004 / R006) are stable to a ±20 % perturbation of the rate. The list would change under a different *type-mix* assumption (e.g., if all Weather became uncontrollable, regional routes would drop from Action 1).

### 7. Strategic route flag — hand-curated, traceable to the brief

The `is_strategic` flag is the peer set of `ont_strategic_underperforming_route`. Without it, "strategic but underperforming" has no anchor. Four routes are flagged, hand-curated from the brief's business-context paragraph:

| Route            | Reason                                                              |
| :--------------- | :------------------------------------------------------------------ |
| R009 (ABJ → CDG) | Long-haul flagship, A330-900neo deployment cited in the brief       |
| R013 (CDG → ABJ) | Return leg, same fleet & strategic intent                           |
| R014 (ABJ → CMN) | Casablanca expansion candidate (Morocco hub feed)                   |
| R016 (ABJ → DXB) | Middle-East expansion candidate explicitly mentioned in the brief   |

- **Alternatives rejected:** deriving "strategic" automatically from `distance_km > 3500` or `aircraft_type = 'A330-900neo'` — both would mechanically tag long-haul as strategic and lose the business intent (e.g., R016 is currently a *candidate* with `weekly_frequency = 0`; an automatic rule would exclude it). The hand-curated flag captures **strategic intent**, not current operational footprint.
- **Impact if the assumption slips:** changes the peer set of the ontology concept. The current implementation in [ont_strategic_underperforming_route.sql](../dbt/models/ontology/ont_strategic_underperforming_route.sql) computes a percentile *among strategic peers only*, so adding/removing a route renormalises the whole cohort. The flag is the **single most reviewable knob** by a VP Network — that's why it lives in plain Python config, not in SQL.

### 8. Reproducibility

- Single global `SEED = 42`.
- Independent NumPy RNG streams per entity (10, 11, 12, 13, 14, 15) — touching one generator doesn't perturb the others.
- `python scripts/run_all.py` → ~2 min. `python scripts/99_validate_pipeline.py` → 24 / 24 PASS.

# Assumptions & design choices (Part 1)

This document captures every non-trivial assumption made during synthetic data generation so a reviewer can challenge them deliberately. **All assumptions are tunable in `scripts/lib/config.py`** — no value is hard-coded across multiple files.

## 1. Anchoring to the starter dataset

| Decision | Rationale |
|---|---|
| Keep raw layer (`data/raw/`) immutable | Auditability — the starter file is preserved 1:1; all enrichment is downstream and reproducible |
| Carry the 300 starter customers into the enriched layer untouched | A reviewer can verify continuity by joining on `customer_id ≤ CUST0300` |
| Add 700 new customers with realistic distribution | The starter had 100% active customers, which is unrealistic; the enriched layer introduces a long tail |
| Use IATA codes already in the starter (ABJ, CDG, etc.) | Avoids inventing new codes for existing routes |

## 2. Time window

Window: **2024-01-01 → 2025-12-31 (24 months)**.

Why 24 months and not 12 or 36:
- Needed to compute **180-day churn** (recency) on real customers, which requires at least a year of history before the analysis window starts
- 24 months exposes seasonality across two annual cycles (high season repeatability, not a one-off)
- 36 months would have been overkill for the local DuckDB demo and slow to regenerate

## 3. Network topology

- **ABJ as hub**: all starter routes are spokes from Abidjan. We preserve this.
- **Added strategic candidates**: CMN (Casablanca), LFW (Lomé), DXB (Dubai) as growth options — explicitly tagged `route_status = candidate` so they support the "where should we open next" decision without polluting the operating book.
- **R009 (ABJ-CDG)** and **R013 (CDG-ABJ)** are operationally distinct one-way legs but together form the strategic Paris pair. They get the long-haul widebody (A330-900neo).

## 4. Fleet model

| Type | Seats (J / W / Y) | Tails | Block-hour cost (USD) |
|---|---|---|---|
| A319 | 12 / 12 / 98 (= 122) | 2 | 3,400 |
| A320 | 12 / 18 / 120 (= 150) | 2 | 3,600 |
| A320neo | 12 / 18 / 120 (= 150) | 3 | 2,900 |
| A330-900neo | 28 / 21 / 232 (= 281) | 2 | 7,200 |

- Configurations follow public Air Côte d'Ivoire schematics (J = Business, W = Premium Economy, Y = Economy).
- Block-hour costs are **synthetic but industry-aligned** (narrowbody ~3-4k USD/h, widebody ~7k USD/h). They split into ~55% fuel / 22% crew / 13% airport fees / 10% maintenance.
- Cancellations cost ~10% of normal direct cost plus an IROPS penalty (rebooking, hotels, EU261-like compensation when applicable).

## 5. Load factor & demand

- **Target load factor** per route_type: Domestic 0.72 / Regional 0.78 / International 0.82.
- Realised LF in the generated data: **mean 0.78, p10 0.66, p90 0.89** — aligned with target.
- Demand is modulated by `SEASONAL_MULTIPLIER` (Jul-Aug +25%, Dec +20%, Sep -10%).

## 6. Customer activity buckets

| Bucket | Share | Bookings over 24 months |
|---|---|---|
| Inactive | 20% | 0 |
| Occasional | 50% | 1–5 |
| Regular | 25% | 6–20 |
| Power user | 5% | 21–60 |

This produces an ~80% active customer base, which is consistent with realistic flag-carrier customer file dynamics.

## 7. Pricing

- Base price (Economy, Standard fare family) per route type: 90 / 230 / 620 USD for Domestic / Regional / International.
- Fare class multiplier: Economy 1.0, Premium Eco 1.8, Business 3.2.
- Fare family multiplier: Basic 0.85, Standard 1.0, Flex 1.25.
- Noise: log-normal scale ~12% to break perfect determinism.

## 8. Disruptions

Disruption events are generated only for:
- All cancelled flights
- All flights delayed > 60 min
- 30% of flights delayed 16–60 min

Type distribution: Weather 35% / Technical 25% / ATC 15% / Crew 15% / Other 10%, with Weather boosted during the West African rainy season (Jun-Aug, mousson). Each disruption has a free-text `root_cause_text` (FR or EN) suitable for the unstructured NLP pipeline.

## 9. Ancillary offers

Six offer types presented per booking with eligibility rules:
- Upgrade W only from Economy, Upgrade J only from Premium Eco
- Acceptance rates boosted for Premium segment (×1.7), Business segment (×1.4), Gold tier (×1.3)
- Realised attach rates match industry benchmarks: seat_selection 54%, extra_bag 36%, upgrade_W 12%, upgrade_J 6%

## 10. Loyalty mechanics

- Points = `distance_km × tier multiplier (Explorer 1.0 / Silver 1.25 / Gold 1.5)`
- ~2% of bookings produce a redemption event (2k / 5k / 10k / 20k points)
- 35% of new customers are non-members (loyalty_tier null)

## 11. Cargo

- Only on long-haul flights (distance > 2,500 km), i.e. essentially R009 and R013 today + future R014/R016
- 1–6 shipments per long-haul flight, 50–4,000 kg each
- Yield: 1.5–9 USD per kg by cargo type

## 12. Competitor benchmark

- Monthly snapshot for routes where the airline competes
- Hand-mapped competitors (Air France, Brussels, Royal Air Maroc on CDG; Asky / Air Senegal on regional; Emirates on candidate DXB)
- Fares jitter ±7% / month

## 13. Unstructured feedback

- Target volume 3,000 rows = ~0.3% of bookings (industry-typical complaint/feedback rate)
- **Free text only** — sentiment is not stored. The dbt staging NLP step (Part 2) will derive:
  - `sentiment_score` (rule-based or model-based)
  - `complaint_category` (regex/keyword over a controlled vocabulary)
  - `route_issue_theme` (cluster of themes per route)
- Language mix: FR 65% / EN 30% / mixed FR+EN 5%
- Polarity correlates with disruption: 75% negative if disrupted, 35% if clean

## 14. Reproducibility

- Single global `SEED = 42`, distinct numpy RNG streams per generator (10, 11, 12, 13, 14, 15) so changes in one entity don't perturb another
- Each script is idempotent and can be run independently after step 00
- Total generation time: ~2 minutes on a laptop CPU

## 15. Known limitations / next steps

| Limitation | Impact | Mitigation in Part 2 |
|---|---|---|
| Disruption text templates limited to ~5 per category | Some downstream NLP overfits to templates | Add lexical noise in dbt staging |
| Competitor data is hand-curated, not from a real feed | Yield benchmark is illustrative only | Document as known limitation in write-up |
| No real weather observations | Weather flags are coarse proxies | Acknowledge; can be swapped for a real API later |
| No cabin-level codeshare / partner data | Cannot model interline revenue | Out of scope for the senior challenge |

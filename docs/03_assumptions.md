# Part 1 — Assumptions

Five load-bearing choices. All values tunable in [scripts/lib/config.py](../scripts/lib/config.py).

### 1. Starter dataset preserved as-is
The 5 starter entities (airports, routes, customers, flights, bookings) sit untouched in `data/raw/`. Everything synthetic lives in `data/enriched/` — any new value is traceable to its source. The 300 starter customers carry through with their original IDs.

### 2. Time window — 24 months (2024-01-01 → 2025-12-31)
- 12 months is too short to compute churn (180-day recency signal needs history *before* the window starts).
- 24 months exposes two annual seasonality cycles.
- 36 months would slow the local DuckDB demo with no analytical gain.

### 3. Customer activity distribution
The starter had 100 % active customers (unrealistic). We add 700 new customers and impose a long-tail:

| Bucket | Share | Bookings / 24 m |
|---|---|---|
| Inactive | 20 % | 0 |
| Occasional | 50 % | 1–5 |
| Regular | 25 % | 6–20 |
| Power user | 5 % | 21–60 |

→ ~80 % active base, aligned with flag-carrier benchmarks. Critical for the **Repeat Booking Rate** and **Recency** KPIs.

### 4. Unstructured feedback — the brief's mandatory dataset
- **3,000 rows** of free-text customer feedback in `customer_feedback.parquet`.
- **Bilingual**: FR 65 % / EN 30 % / mixed 5 % (reflects Air CIV's francophone-plus-international mix).
- **Raw text only** — sentiment, category and tags are *deliberately not stored at generation*. They are derived by the Part-2 dbt NLP pipeline. That choice turns the dataset into a real unstructured-to-structured exercise instead of a relabelled lookup.
- Polarity correlates with operational reality: a feedback row linked to a disrupted flight is 75 % negative, vs 35 % otherwise.

### 5. Reproducibility
- Single global `SEED = 42`.
- Independent NumPy RNG streams per entity (10, 11, 12, 13, 14, 15) — touching one generator doesn't perturb the others.
- `python scripts/run_all.py` → ~2 min. `python scripts/99_validate_pipeline.py` → 24 / 24 PASS.

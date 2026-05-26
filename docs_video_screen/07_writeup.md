# Write-up — Air Côte d'Ivoire Analytics Challenge

**Decision question:** Where should Air Côte d'Ivoire invest first to maximise profitable growth over the next 12 months?  
**Answer:** 40 % ops stabilisation → 35 % customer retention → 25 % premium upsell.

---

## Assumptions

**Time window — 24 months (2024–2025).** A 12-month window is too short to compute churn: the RFM recency signal needs history before the observation period starts. Two full calendar years also expose both annual seasonality cycles, which is the minimum to distinguish structural underperformance from a temporary dip.

**Synthetic cost model.** The starter dataset provides revenue but no cost. A block-hour rate was assigned per aircraft type (A319 $3 400 / A320 $3 600 / A320neo $2 900 / A330-900neo $7 200) and split into fuel 55 %, crew 22 %, airport fees 13 %, maintenance 10 %. Cancelled flights receive an IROPS penalty drawn from Gamma(5, 800) ≈ $4 K median. Without this model there is no route margin, no strategic underperformance concept, and no quantified case for the ops recommendation.

**Disruption type mix.** The starter records delays and cancellations but not their cause. A disruption table was generated with a realistic type mix (weather 35 %, technical 25 %, ATC 15 %, crew 15 %, other 10 %) and a monsoon bump for Jun–Aug at ABJ. This split is what makes it possible to separate controllable failures (crew, technical) from exogenous ones (weather) in the recommendation.

**Strategic route flag.** Four routes are hand-curated as strategic (ABJ–CDG, CDG–ABJ, ABJ–CMN, ABJ–DXB) based on the brief's business-context paragraph. An automatic rule derived from distance or aircraft type would exclude ABJ–DXB, which currently has zero weekly frequency but is an explicit expansion candidate. The flag captures strategic intent, not current footprint.

**Unstructured feedback — raw text only.** 3 000 bilingual (FR/EN) feedback rows were generated without pre-assigned labels. Sentiment score, complaint category, and semantic tags are derived entirely by the Part-2 dbt NLP pipeline. This design turns the dataset into a genuine unstructured-to-structured exercise rather than a relabelled lookup.

---

## Architecture

The project is organised in four independent, composable layers.

**Part 1 — Data generation.** A Python pipeline (SEED = 42, independent RNG streams per entity) extends the five starter files with ten enriched datasets: flight costs, disruptions, ancillary offers, loyalty activity, customer feedback, weather, cargo, competitors, aircraft, and a customer activity scaffold. Every new file is traceable to a specific KPI or ontology concept it unlocks.

**Part 2 — dbt on DuckDB (Kimball star schema).** The warehouse follows a fact constellation: five fact tables at different grains (flight, booking, feedback, loyalty event, ancillary offer) sharing six conformed dimensions (date, route, customer, aircraft, fare, airport). A targeted SCD2 snapshot on `dim_customer.loyalty_tier` preserves the loyalty tier at the time of each booking — required for fair retention KPIs. A lexicon-based NLP pipeline (145-word bilingual sentiment lexicon, 62-entry complaint taxonomy) runs entirely inside dbt, keeping every score auditable at row level. Five ontology concepts (two required by the brief, three derived) classify customers, routes, and offers as actionable business segments. A semantic layer declares 10 KPIs as MetricFlow-compatible metrics. All 160 dbt tests pass.

**Part 3 — Superset dashboards.** Four dashboards (network profitability, customer retention, upsell / cross-sell, decision layer) are provisioned via the Superset REST API — no drag-and-drop, fully version-controlled. The decision layer surfaces the five ontology concepts directly as actionable tables (Grow, Defend, Retain, Prioritise).

**Part 4 — MCP server.** A FastMCP server (stdio) exposes three tools to Claude Desktop and Claude Code: `list_routes_with_kpis`, `list_high_value_at_risk_customers`, and `search_feedback_text` (the unstructured source). Every call returns an audit envelope with the exact SQL executed. The DuckDB connection is read-only; queries are parameterised to prevent injection.

---

## Limitations

- **Synthetic margins are optimistic.** The 78 % network margin reflects direct operating costs only — no overheads, depreciation, MRO contracts, or slot fees. Real EBIT for a West African flag carrier is typically 5–12 %. Route ranking is robust (same model applied uniformly); absolute figures should not be cited without Finance re-calibration.
- **NLP coverage is limited.** A 145-word lexicon cannot handle sarcasm, intensifiers, or uncommon domain vocabulary. The fixed 2-token negation window misclassifies long-distance negation constructions. A fine-tuned multilingual model (xlm-roberta-base) would substantially improve recall without changing the downstream interface.
- **Ontology thresholds are percentile-based, not business-validated.** Adding customers next quarter will silently renormalise every P60 cut-point. Thresholds need sign-off from CCO and VP Loyalty to be production-grade.
- **DuckDB is single-user.** Suitable for a local demo and single-analyst workloads; not designed for concurrent multi-user dashboard access at scale.

---

## Next Steps

1. **Connect real P&L data.** Replace the synthetic cost model with Finance extracts (even a monthly route-level file). This is the single change with the highest impact on recommendation credibility.
2. **Validate and anchor ontology thresholds.** Walk each concept owner (CCO, VP Network, VP Loyalty, COO) through their rule and replace percentile cut-points with business-agreed absolute values.
3. **Upgrade the NLP pipeline.** Swap the sentiment lexicon for a fine-tuned `xlm-roberta-base` inference step. The output columns stay identical — only `int_feedback_sentiment.sql` changes.
4. **Make `is_strategic` a governed reference table.** Move the flag from `scripts/lib/config.py` into a versioned seed with an effective-date column and a named owner.
5. **Scale the stack for production.** Replace DuckDB with a multi-user OLAP engine (ClickHouse, BigQuery, or Snowflake). The dbt models and semantic layer SQL are engine-agnostic — only `profiles.yml` and the MCP connection string change.

# Air Côte d'Ivoire — Analytics Engineer Challenge (Senior submission)

Growth-allocation analytics product for Air Côte d'Ivoire. The artefact answers:
**Where should the airline invest first to maximise profitable growth over the next 12 months — route expansion, customer retention, or upsell / cross-sell?**

## Repository layout

```
/data
  /raw/             Immutable 1:1 copy of the starter Excel (Parquet)
  /enriched/        Synthetic + scaled data ready for dbt staging
/scripts            Python generation pipeline (numbered, idempotent)
/dbt                dbt project (Part 2 — staging, marts, semantic layer)
/notebooks          Exploratory / NLP / validation notebooks
/dashboard          Apache Superset assets (Part 3)
/mcp                MCP server exposing the semantic layer (Part 4)
/docs               Documentation: business framing, data dictionary, assumptions
```

## Part 1 — Status: ✅ complete

Deliverables produced:

| Artefact | Path |
|---|---|
| Business framing & KPI catalogue | `docs/01_business_framing.md` |
| Data dictionary (enriched layer) | `docs/02_data_dictionary.md` |
| Assumptions & design choices | `docs/03_assumptions.md` |
| Raw layer (immutable) | `data/raw/*.parquet` |
| Enriched layer (12 entities) | `data/enriched/*.parquet` |
| Generation pipeline (idempotent) | `scripts/00_*` … `scripts/15_*` |
| End-to-end orchestrator | `scripts/run_all.py` |
| Validation suite | `scripts/99_validate_pipeline.py` |

### How to (re)generate

```bash
python scripts/run_all.py
python scripts/99_validate_pipeline.py
```

Total runtime: ~2 minutes on a laptop. Single global seed (`SEED=42` in `scripts/lib/config.py`) per generator stream guarantees reproducibility.

### Enriched layer at a glance

| Entity | Rows | Purpose |
|---|---|---|
| airports | 13 | 10 starter + 3 candidates (CMN, LFW, DXB) |
| routes | 16 | 12 starter + 4 candidates (incl. ABJ-CDG return, ABJ-CMN, ABJ-LFW, ABJ-DXB) |
| aircraft | 9 | Synthetic fleet (A319 / A320 / A320neo / A330-900neo) |
| customers | 1,000 | 300 starter + 700 new with realistic activity buckets |
| flights | 8,747 | 24-month schedule, seasonality, aircraft assignment |
| bookings | 1,113,396 | Realised load factor 78%, 80% active customers |
| flight_costs | 8,747 | Decomposed fuel / crew / fees / maintenance / IROPS |
| disruptions | 1,760 | Type / severity / FR-EN root cause text |
| weather_daily | 9,503 | Airport × day proxy (precipitation, wind) |
| loyalty_activity | 650,540 | Earn + redeem events |
| ancillary_offers | 3,324,789 | Presentation + acceptance per booking |
| cargo_shipments | 5,604 | Long-haul only |
| competitors | 600 | Monthly route × competitor snapshot |
| **customer_feedback** | 3,000 | **Unstructured FR/EN free text — sentiment to be scored in Part 2** |

### Realism validation (current run)

| Check | Target | Actual |
|---|---|---|
| Mean load factor | 0.70 – 0.85 | **0.78** |
| Cancellation rate | 1% – 7% | **3.6%** |
| On-Time Performance (≤15 min) | 55% – 80% | **66.5%** |
| Ancillary attach rate | 70% – 90% | **80.2%** |
| Active customer share | 70% – 90% | **80.0%** |
| Feedback FR share | 55% – 75% | **64.9%** |
| Referential integrity (all FKs) | 100% | **100%** |

## Parts 2-4 — Status: ⏳ pending

- Part 2: dbt modelling (star schema), semantic layer, ontology, NLP integration
- Part 3: Executive Growth Allocation Dashboard (Apache Superset)
- Part 4: MCP server exposing structured + unstructured data to AI assistants

## Decisions log

See `docs/03_assumptions.md` for every business and statistical assumption. Each is tunable via a single config file (`scripts/lib/config.py`).

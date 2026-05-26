# Air Côte d'Ivoire — Analytics Engineer Challenge

**Decision question (per brief):** *Where should Air Côte d'Ivoire invest first to maximise profitable growth over the next 12 months — route expansion, customer retention, or upsell / cross-sell?*

**Answer (one line):** **40 % ops stabilisation → 35 % retention → 25 % premium upsell.** Recover margin first, protect revenue second, grow it third. Full reasoning in [docs_video_screen/10_executive_recommendations.md](docs_video_screen/10_executive_recommendations.md).

---

## Repository layout

```
/data            raw/ (immutable starter) → enriched/ (synthetic, regenerable)
/scripts         Python data-generation pipeline (Part 1)
/dbt             dbt project: staging → marts → semantic → ontology (Part 2)
/dashboard       Apache Superset assets (Part 3)
/mcp_server      MCP server exposing marts + feedback to AI assistants (Part 4)
/docs_video_screen  Business framing, modelling, dashboard, MCP docs
/notebooks       Exploratory / validation notebooks
```

## Run end-to-end

### Option A — Docker (recommended, zero local setup)

A single `docker-compose.yml` orchestrates everything: a one-shot **pipeline** service (Parts 1+2), **Superset** with auto-provisioning (Part 3), and the **MCP server** on demand (Part 4).

```bash
# Build images, run the pipeline, bring up Superset + auto-provision
docker compose up --build -d pipeline superset superset-provisioner

# Follow progress (Ctrl-C just detaches)
docker compose logs -f pipeline superset-provisioner

# MCP server (ad-hoc, stdio) — used by Claude Desktop / Claude Code
docker compose run --rm mcp
```

Superset is served at <http://localhost:8088> (`admin` / `admin`). Artefacts (`data/enriched/`, `dbt/airline.duckdb`, `dbt/target/`) are bind-mounted, so `dbt docs serve` and local inspection work as usual.

To wire the dockerised MCP into Claude Desktop, paste this block into `claude_desktop_config.json`:

```json
"air-cote-divoire": {
  "command": "docker",
  "args": ["compose", "-f", "<PROJECT_ROOT>/docker-compose.yml",
           "run", "--rm", "-T", "mcp"]
}
```

### Option B — Local Python

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt

# Part 1 — regenerate synthetic data (~2 min, seed=42, reproducible)
.venv/Scripts/python scripts/run_all.py
.venv/Scripts/python scripts/99_validate_pipeline.py

# Part 2 — dbt
cd dbt
DBT_PROFILES_DIR=. ../.venv/Scripts/dbt deps
DBT_PROFILES_DIR=. ../.venv/Scripts/dbt seed
DBT_PROFILES_DIR=. ../.venv/Scripts/dbt snapshot
DBT_PROFILES_DIR=. ../.venv/Scripts/dbt build         # run + test together
DBT_PROFILES_DIR=. ../.venv/Scripts/dbt docs generate
DBT_PROFILES_DIR=. ../.venv/Scripts/dbt docs serve
```

---

## How each brief requirement is met

### Part 1 — Business understanding & synthetic data

| Brief requirement                                | Deliverable                                                                                                                |
| :----------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| Describe the 5 airline business domains          | [docs_video_screen/01_business_framing.md §1](docs_video_screen/01_business_framing.md)                                                              |
| List KPIs guiding decisions                      | [docs_video_screen/01_business_framing.md §2](docs_video_screen/01_business_framing.md) — 10 KPIs covering the 9 brief examples                      |
| Generate realistic data with ≥ 1 unstructured    | `data/enriched/*.parquet`, incl. `customer_feedback.parquet` (3,000 FR/EN free-text rows)                                  |
| Document assumptions                             | [docs_video_screen/03_assumptions.md](docs_video_screen/03_assumptions.md) — 8 load-bearing assumptions                                              |
| *Which new data, why, how it changes the reco*   | [docs_video_screen/06_data_generation_rationale.md](docs_video_screen/06_data_generation_rationale.md) — per-file defence + recommendation traceability |

> The unstructured dataset is **raw text only**. Sentiment, complaint category and tags are derived downstream by the Part-2 dbt NLP pipeline — a genuine unstructured-to-structured exercise.

### Part 2 — Modelling, semantic layer, ontology

| Brief requirement                              | Deliverable                                                                                                                                       |
| :--------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| Model supporting the 3 themes                  | Star schema (Kimball dimensional) in `dbt/models/marts/`, implemented as a fact constellation — 5 facts × 6 conformed dimensions. Visual ER diagram: [docs_video_screen/screenshots/modeling_diagram.png](docs_video_screen/screenshots/modeling_diagram.png) |
| Justify Star / Data Vault / Hybrid             | [docs_video_screen/04_modeling_choices.md §1](docs_video_screen/04_modeling_choices.md) — trade-off table                                                                   |
| Semantic layer (entities, KPIs, joins, naming) | `_semantic_models.yml` + `_metrics.yml` (10 KPIs) + naming conventions in [docs_video_screen/04_modeling_choices.md §6](docs_video_screen/04_modeling_choices.md)           |
| Ontology with reasoning rules                  | 2 brief-named concepts (`ont_high_value_at_risk_customer`, `ont_strategic_underperforming_route`) — SQL + YAML rules in `docs_video_screen/05_ontology_rules.yml` |
| Unstructured integration                       | Lexicon-based sentiment → `fct_customer_feedback`. Pipeline in [docs_video_screen/04_modeling_choices.md §5](docs_video_screen/04_modeling_choices.md)                       |

Run: `cd dbt && dbt build` → **160 / 160 tests pass in ~12 s**.

### Part 3 — Executive Growth Allocation Dashboard

| Brief requirement                              | Deliverable                                                                                                                                                |
| :--------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Executive Growth Allocation Dashboard          | Apache Superset 4.1.2 in Docker, reading `dbt/airline.duckdb`                                                                                              |
| Network & profitability                        | [`network-profitability`](docs_video_screen/screenshots/01_network_profitability.png) — revenue, opportunity matrix, OTP/cancel trends, RASK, disruptions               |
| Customer & retention                           | [`customer-retention`](docs_video_screen/screenshots/02_customer_retention.png) — segments, at-risk, complaint heatmap, sentiment trend, repeat rate                    |
| Upsell & cross-sell                            | [`upsell-crosssell`](docs_video_screen/screenshots/03_upsell_crosssell.png) — upgrade conversion, attach, revenue per pax, premium candidates                           |
| Decision layer                                 | [`decision-layer`](docs_video_screen/screenshots/04_decision_layer.png) — Grow / Defend / Retain / Prioritise (ontology-driven)                                         |
| Screenshots                                    | [docs_video_screen/screenshots/](docs_video_screen/screenshots/) — 1 PNG per area                                                                                                    |
| One-page executive recommendations             | [docs_video_screen/10_executive_recommendations.md](docs_video_screen/10_executive_recommendations.md) (also as printable [PDF](docs_video_screen/10_executive_recommendations.pdf)) — verdict + 3 actions + 90-day KPI targets |

Design rationale: [docs_video_screen/09_dashboard_design.md](docs_video_screen/09_dashboard_design.md). All charts provisioned via the Superset REST API by versioned Python scripts — no drag-and-drop.

### Part 4 — Agentic AI / MCP server

| Brief requirement                              | Deliverable                                                                                                                                  |
| :--------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------- |
| Small MCP server                               | [`mcp_server/`](mcp_server/) — Python FastMCP, stdio, 3 tools                                                                                |
| AI assistant integration                       | [`mcp_server/claude_desktop_config.json`](mcp_server/claude_desktop_config.json)                                                             |
| Structured + ≥ 1 unstructured source           | 2 structured tools (`list_routes_with_kpis`, `list_high_value_at_risk_customers`) + 1 unstructured (`search_feedback_text`)                  |
| Q1 — *"Which routes deserve more budget?"*     | `list_routes_with_kpis`                                                                                                                      |
| Q2 — *"Which high-value customers are at risk?"* | `list_high_value_at_risk_customers`                                                                                                          |
| Q3 — *"Complaints on route X?"*                | `search_feedback_text` (the unstructured-source tool)                                                                                        |
| Video + brief architecture                     | Script + architecture in [docs_video_screen/11_mcp_architecture.md](docs_video_screen/11_mcp_architecture.md)                                                          |

Smoke test: `python -m mcp_server.smoke_test` answers the three brief questions end-to-end through the real MCP protocol.

---

## Senior-level differentiators (per brief)

| Brief criterion                | Where to find it                                                                                                            |
| :----------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| Deliberate modelling trade-offs | Star + targeted SCD2 justified; Superset over Streamlit; specialised tools over `run_sql` — [docs_video_screen/04_modeling_choices.md](docs_video_screen/04_modeling_choices.md) |
| Reusable semantic layer        | 10 KPIs in `_metrics.yml` + 5 entities in `_semantic_models.yml`                                                            |
| Ontology-inspired inference    | 2 brief-named concepts as SQL + declarative YAML rules                                                                       |
| Robust AI tooling              | 3 specialised tools, Pydantic validation, read-only DB, audit envelope, end-to-end smoke test                                |
| Strong documentation           | 8 docs in `/docs_video_screen` + screenshots                                                                                              |

## Documentation index

- [docs_video_screen/01_business_framing.md](docs_video_screen/01_business_framing.md) — 5 domains + 10 KPIs (Part 1)
- [docs_video_screen/02_data_dictionary.md](docs_video_screen/02_data_dictionary.md) — column-level reference
- [docs_video_screen/03_assumptions.md](docs_video_screen/03_assumptions.md) — 8 load-bearing assumptions (Part 1)
- [docs_video_screen/04_modeling_choices.md](docs_video_screen/04_modeling_choices.md) — modelling, semantic layer, ontology, unstructured integration (Part 2)
- [docs_video_screen/05_ontology_rules.yml](docs_video_screen/05_ontology_rules.yml) — machine-readable ontology rules
- [docs_video_screen/06_data_generation_rationale.md](docs_video_screen/06_data_generation_rationale.md) — per-file defence + recommendation traceability (Part 1)
- [docs_video_screen/07_writeup.md](docs_video_screen/07_writeup.md) — assumptions, architecture, limitations & next steps (cross-cutting)
- [docs_video_screen/09_dashboard_design.md](docs_video_screen/09_dashboard_design.md) — Superset stack + chart mapping (Part 3)
- [docs_video_screen/10_executive_recommendations.md](docs_video_screen/10_executive_recommendations.md) — one-page CEO-printable verdict (Part 3)
- [docs_video_screen/11_mcp_architecture.md](docs_video_screen/11_mcp_architecture.md) — MCP architecture + video script (Part 4)

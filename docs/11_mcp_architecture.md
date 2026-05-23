# Part 4 — MCP server architecture

> **Brief**: *"Expose your modeled data through a small MCP server or an equivalent tool layer that an AI assistant can use. The AI interface must be able to use both structured data and at least one unstructured source."*

## 1. Vision

Most "AI on top of analytics" projects end with a single `run_sql(query)` tool that hands the LLM a shotgun pointed at the warehouse. The agent invents SQL, the SQL goes wrong silently, and nobody can audit what was actually asked.

**This MCP server takes the opposite stance**: the LLM never writes SQL. It picks among **8 specialised, contract-bound tools**, each backed by a single SQL statement we wrote, tested, and committed. The tradeoff is more code on our side; the payoff is **explainability, auditability and safety by construction**.

## 2. Architecture

```
   ┌────────────────────────────────────────────────────────────────┐
   │                       Claude Desktop                            │
   │              (MCP client over stdio)                            │
   └─────────────────────────────┬──────────────────────────────────┘
                                 │  JSON-RPC
                                 ▼
   ┌────────────────────────────────────────────────────────────────┐
   │              mcp_server (Python, FastMCP)                       │
   │                                                                 │
   │   ┌──────────────────────┐    ┌────────────────────────────┐  │
   │   │  8 Tools             │    │  1 Resource                 │  │
   │   │  • 5 ontology        │    │  • airline glossary         │  │
   │   │  • 1 network summary │    │    (LF, RASK, IROPS, …)     │  │
   │   │  • 1 feedback search │    └────────────────────────────┘  │
   │   │  • 1 compare_routes  │                                     │
   │   └──────────┬───────────┘                                     │
   │              │                                                 │
   │   ┌──────────▼───────────────────────────┐                    │
   │   │  safety.py — read-only enforcement,  │                    │
   │   │  row limit (1000), audit envelope    │                    │
   │   └──────────┬───────────────────────────┘                    │
   └──────────────┼─────────────────────────────────────────────────┘
                  │
                  ▼
   ┌────────────────────────────────────────────────────────────────┐
   │              dbt/airline.duckdb (read-only)                     │
   │  ├── main_marts        ← structured KPIs, dimensions, facts    │
   │  ├── main_intermediate ← NLP-enriched, route monthly perf      │
   │  └── main_ontology     ← 5 inferred concepts (Part 2)          │
   └────────────────────────────────────────────────────────────────┘
```

## 3. Tools catalogue (8)

### Ontology tools — 5 (the senior differentiator)

Each tool maps 1:1 to an ontology concept built in Part 2. The LLM **doesn't classify** — Part 2 already did.

| # | Tool | Concept | Sample LLM usage |
|---|---|---|---|
| 1 | `list_high_value_at_risk_customers(limit, sort_by)` | `ont_high_value_at_risk_customer` | *"Who do we retain this quarter?"* |
| 2 | `list_strategic_underperforming_routes(limit)` | `ont_strategic_underperforming_route` | *"Strategic routes losing margin?"* |
| 3 | `list_premium_upsell_candidates(segment, tier, limit)` | `ont_premium_upsell_candidate` | *"Best targets for premium offers?"* |
| 4 | `list_loyal_detractors(min_frequency, limit)` | `ont_loyal_detractor` | *"Gold members slipping?"* |
| 5 | `list_irops_heavy_routes()` | `ont_irops_heavy_route` | *"Where are our ops issues?"* |

### KPI tool — 1 (consolidated headline summary)

| # | Tool | Returns |
|---|---|---|
| 6 | `get_network_summary(period_months, route_id?)` | Single row with 8 headline KPIs: revenue, margin %, LF, OTP15, cancel rate, attach rate, sentiment, premium mix |

> **Why one tool, not eight**: the 8 KPIs are always read together in an exec context — splitting them would only add LLM round-trips.

### NLP / unstructured tool — 1

| # | Tool | Returns |
|---|---|---|
| 7 | `search_feedback_text(query, route_id, sentiment_label, complaint_category, limit)` | Up to 50 feedback rows with **raw_text** (FR/EN) + NLP-derived sentiment/category |

> **This is the tool that satisfies the brief's "at least one unstructured source" requirement.** When the user asks *"What complaints drive low satisfaction on route X?"*, the agent calls this and quotes verbatim.

### Decision tool — 1

| # | Tool | Returns |
|---|---|---|
| 8 | `compare_routes(route_id_a, route_id_b, period_months)` | 2 rows, one per route, with financial + operational + customer signals side-by-side |

## 4. Resources catalogue (1)

| URI | Content | Why it's there |
|---|---|---|
| `glossary://airline-business` | Markdown glossary: KPIs, ontology, tool-routing patterns, unit conventions | LLM reads it **before** answering, to speak the right vocabulary and pick the right tool |

## 5. Safety layer

Every tool flows through `safety.safe_query(sql, params, description)` which guarantees:

| Guarantee | How |
|---|---|
| **Read-only** | DuckDB opened with `read_only=True` — any DDL/DML rejected by the engine, not by us |
| **Audit trail** | Every response includes the SQL + params executed. An exec can re-run the same query manually |
| **Row limit** | Hard cap at `MAX_ROWS = 1000` — protects LLM context |
| **No SQL injection** | Parameters are bound (`?`), never f-stringed |
| **Errors are data** | Exceptions become `{"error": "...", "sql": "..."}` payloads — the agent reads, the user never sees a 500 |

Validated by 5 `pytest` tests in `mcp_server/tests/test_safety.py`.

## 6. Senior trade-offs (the explainability argument)

| Trade-off | Choice | Junior alternative | Why this is senior |
|---|---|---|---|
| **Tool granularity** | 8 specialised tools | 1 generic `run_sql(query)` | Audit, safety, contract — the LLM can't invent broken SQL |
| **Transport** | stdio | HTTP/SSE | Brief says "small MCP server"; stdio = zero infra |
| **Statefulness** | None | Sessions | Simpler, no leak risk, fits a single-user demo |
| **Audit trail** | Echo SQL + params in every response | Discard | A row of evidence per request |
| **Validation** | Pydantic `Field(ge=…, le=…)` at the boundary | Trust user input | Schema enforced at the LLM/server interface |
| **Resource for glossary** | Static Markdown via `@mcp.resource` | None | LLM speaks the right vocabulary without an extra tool call |

## 7. Reproducibility

The whole MCP layer is reproducible in **≤4 commands** from a clean clone:

```bash
.venv/Scripts/pip install -r requirements.txt
# (assumes dbt/airline.duckdb already exists — see Part 2)
.venv/Scripts/python -m mcp_server.smoke_test        # 5/5 questions PASS
.venv/Scripts/python -m pytest mcp_server/tests/     # 17/17 tests PASS
# wire Claude Desktop with mcp_server/claude_desktop_config.json
```

## 8. Tests

| File | Tests | What's verified |
|---|---|---|
| `test_safety.py` | 5 | envelope contract, row truncation, params binding, read-only enforcement, errors-are-data |
| `test_tools_ontology.py` | 6 | one per ontology tool + a filter combo |
| `test_tools_other.py` | 6 | network summary, feedback search, compare_routes, glossary resource |
| **smoke_test.py** | end-to-end | spawns the server over stdio and answers 5 grounded questions |

## 9. Brief acceptance — coverage matrix

| Brief requirement | Where covered |
|---|---|
| *"Expose your modeled data through a small MCP server"* | `mcp_server/server.py` + 8 tools |
| *"Equivalent tool layer that an AI assistant can use"* | Claude Desktop via `claude_desktop_config.json` |
| *"Both structured data and at least one unstructured source"* | Structured: tools 1-6, 8 \| Unstructured: tool 7 (`search_feedback_text`) |
| *"Demonstrate grounded questions: routes deserving budget"* | Q1 in `smoke_test.py` |
| *"…high-value customers at risk"* | Q2 in `smoke_test.py` |
| *"…complaints on route X"* | Q3 in `smoke_test.py` |
| *"Video showing the interaction"* | Script in `docs/12_video_walkthrough.md`, recording instructions for the user |
| *"Explain the architecture briefly"* | This document + 15-second slide in the video |
| *Senior: "robust AI tooling"* | 8 specialised tools + Pydantic validation + safety layer + 17 tests + smoke E2E |

## 10. Limitations explicitly accepted

| Limitation | Why we accept it |
|---|---|
| Single user, no auth | Brief asks for a "small" local MCP server |
| No streaming responses | DuckDB queries return in < 100 ms — streaming adds complexity for no gain |
| No caching | Same reason |
| No write tools (RAG store, etc.) | Read-only by design — the database is the analytical store, not the agent's memory |
| Lexicon-based NLP, not transformer | Part-2 trade-off; explainability prized over marginal precision |

## 11. What changes if we industrialise

| Today (demo) | Tomorrow (prod) |
|---|---|
| stdio transport | SSE/HTTP behind an API gateway |
| SQLite-free, no Celery | Postgres metastore, Redis cache |
| Admin password `admin/admin` | OAuth2 + per-user role-based tool access |
| Single DuckDB file | Cloud warehouse (Snowflake/BigQuery) with the same `safe_query` envelope |
| Per-request audit echoed to LLM | Audit shipped to a SIEM in addition |

The 8 tool contracts themselves are warehouse-agnostic — the swap point is `db.py`.

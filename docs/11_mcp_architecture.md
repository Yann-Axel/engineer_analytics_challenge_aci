# Part 4 — MCP server architecture & video script

The brief asks for a small MCP server exposing structured + unstructured data to an AI assistant, with grounded questions, a video, and a brief architecture explanation.

## Architecture

```mermaid
flowchart LR
    CD[Claude Desktop] -->|stdio / MCP| SRV[mcp_server<br/>FastMCP, Python]
    SRV --> T1[[list_routes_with_kpis]]
    SRV --> T2[[list_high_value_at_risk_customers]]
    SRV --> T3[[search_feedback_text]]
    T1 -->|read-only<br/>parametrised SQL| DB[(dbt/airline.duckdb)]
    T2 -->|read-only| DB
    T3 -->|read-only| DB
    DB --> M[marts dim_* / fct_*]
    DB --> O[ontology ont_*]
    DB --> F[fct_customer_feedback<br/>FR/EN text]
    T1 -.-> M
    T2 -.-> O
    T3 -.-> F

    classDef tool fill:#dbeafe,stroke:#1e3a8a,color:#1e3a8a
    classDef unstr fill:#fef3c7,stroke:#92400e,color:#92400e
    class T1,T2,T3 tool
    class F unstr
```

## Three tools, three brief questions

| Tool | Answers |
|---|---|
| `list_routes_with_kpis(period_months, limit)` | *Which routes deserve more budget next quarter?* |
| `list_high_value_at_risk_customers(limit)` | *Which high-value customers are at risk?* |
| `search_feedback_text(route_id, sentiment_label, limit)` | *What complaints drive low satisfaction on route X?* — **unstructured source** |

Every tool returns an **audit envelope** (`sql`, `params`, `row_count`, `rows`) so an exec can verify what was queried. DuckDB opens read-only, parameters are bound, results capped at 1,000 rows.

## Run

```bash
python -m mcp_server               # boot stdio server
python -m mcp_server.smoke_test    # answer the 3 questions end-to-end
```

To wire Claude Desktop: paste the block from [`mcp_server/claude_desktop_config.json`](../mcp_server/claude_desktop_config.json) into `%APPDATA%/Claude/claude_desktop_config.json`, replace `<PROJECT_ROOT>`, restart.

## Video — 2-minute script

| Time | On screen | Voice-over |
|---|---|---|
| 0:00–0:20 | Claude Desktop with 3 MCP tools listed | *"Three tools, exposed via MCP, answer the brief's three growth-allocation questions."* |
| 0:20–0:35 | This architecture diagram | *"FastMCP, stdio, read-only DuckDB, audit envelope on every call."* |
| 0:35–0:55 | Type: *Which routes deserve more budget next quarter?* | *"Tool 1 returns each route with margin, load factor, OTP, cancellation."* |
| 0:55–1:15 | Type: *List top 5 high-value customers at risk.* | *"Tool 2 — the ontology has already flagged 20 customers with dissatisfaction signals."* |
| 1:15–1:50 | Type: *What complaints drive low satisfaction on R005? Quote a few customers verbatim.* | *"Tool 3 — search_feedback_text returns raw FR/EN feedback. The unstructured source."* |
| 1:50–2:00 | GitHub URL | *"Full code in mcp_server/."* |

Recording: ShareX or OBS, MP4 720p, save to `docs/mcp_walkthrough.mp4`.

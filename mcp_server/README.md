# Air Côte d'Ivoire MCP Server

Tool layer that exposes the dbt marts + ontology to any MCP-compatible AI assistant (Claude Desktop, Claude Code, third-party clients). Standard MCP, stdio transport, read-only by design.

> **Full architecture & design rationale**: see [`docs/11_mcp_architecture.md`](../docs/11_mcp_architecture.md).
> **Video walkthrough script**: see [`docs/12_video_walkthrough.md`](../docs/12_video_walkthrough.md).

## Surface

| | Count | What |
|---|---|---|
| Tools | 8 | 5 ontology + 1 KPI summary + 1 NLP search + 1 compare |
| Resources | 1 | `glossary://airline-business` |
| Tests | 17 | safety (5), ontology tools (6), other tools (6) |

## Prereqs

- Python 3.12 in `.venv` (project-wide)
- `dbt/airline.duckdb` materialised (`cd dbt && dbt build` once)

## Install

```bash
# from the project root
.venv/Scripts/pip install -r requirements.txt
```

## Run the smoke test (end-to-end protocol check)

This spawns the server on stdio and answers the 5 grounded questions of the brief — exactly what Claude Desktop will do.

```bash
.venv/Scripts/python -m mcp_server.smoke_test
```

Expected outcome: `=== 5/5 questions answered via the MCP protocol ===`.

## Run the test suite

```bash
.venv/Scripts/python -m pytest mcp_server/tests/ -v
```

Expected: **17 passed in ~1s**.

## Wire Claude Desktop

1. Open `mcp_server/claude_desktop_config.json` and replace `<PROJECT_ROOT>` with the absolute path to this repository.
2. Paste the `mcpServers.air-cote-divoire` block into:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
3. Fully restart Claude Desktop (quit from system tray, not just close).
4. Open a new conversation → click the small MCP-icon in the bottom right → you should see **`air-cote-divoire`** with 8 tools and 1 resource.

## Demo questions to type into Claude Desktop

The agent is grounded — it picks the right tool from each question automatically. Try, in order:

> **"Which strategic routes are underperforming, and which have operational issues?"**
> → uses `list_strategic_underperforming_routes` + `list_irops_heavy_routes`

> **"List the 5 most at-risk high-value customers."**
> → uses `list_high_value_at_risk_customers`

> **"What complaints drive low satisfaction on route R005? Quote a few customers verbatim."**
> → uses `get_network_summary(route_id='R005')` + `search_feedback_text` (the unstructured-source tool)

> **"Compare routes R009 and R008 on financial AND satisfaction signals."**
> → uses `compare_routes`

> **"Which customers should I push premium offers to?"**
> → uses `list_premium_upsell_candidates`

## Folder layout

```
mcp_server/
├── __init__.py
├── __main__.py            ← `python -m mcp_server` entrypoint (Claude Desktop)
├── server.py              ← FastMCP instance + tool/resource registration
├── db.py                  ← Read-only DuckDB connection, cached
├── safety.py              ← safe_query() + envelope + row-limit + audit trail
├── smoke_test.py          ← End-to-end protocol check (5 grounded questions)
├── claude_desktop_config.json  ← Template config to paste
│
├── tools/
│   ├── ontology.py        ← 5 ontology tools
│   ├── kpis.py            ← 1 network-summary tool
│   ├── nlp.py             ← 1 feedback search tool (unstructured)
│   └── decision.py        ← 1 compare_routes tool
│
├── resources/
│   └── glossary.py        ← `glossary://airline-business`
│
└── tests/
    ├── test_safety.py
    ├── test_tools_ontology.py
    └── test_tools_other.py
```

## Why the folder is named `mcp_server` (not `mcp`)

The SDK we depend on is literally named `mcp`. A local package with the same name would shadow `from mcp.server.fastmcp import FastMCP` and break every import. The compromise was either a longer folder name or a Python-path trick — we chose clarity.

## How to extend

| Add a new… | Where | Pattern |
|---|---|---|
| Tool | `tools/<new>.py` | Use `@mcp.tool()`, Pydantic `Annotated[..., Field(...)]`, call `safe_query()` |
| Resource | `resources/<new>.py` | Use `@mcp.resource("scheme://name")` and return a string |
| Ontology concept | `dbt/models/ontology/ont_X.sql` first, then a tool in `tools/ontology.py` | Single SQL + a thin tool — same pattern as the existing 5 |

## Troubleshooting

| Symptom | Fix |
|---|---|
| Claude Desktop shows 0 tools | Check absolute path in the config; restart fully (quit from tray) |
| "Database file not found" | Run `dbt build` in `dbt/` first |
| `from mcp_server.server import mcp` fails | You're probably inside the SDK's `mcp` package — make sure you're running from the project root |
| `python -m mcp_server.server` shows 0 tools but pytest is green | Use `python -m mcp_server` (the `__main__.py` entrypoint). Calling `-m mcp_server.server` double-loads the module |

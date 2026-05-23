# Air Côte d'Ivoire MCP Server

Three tools that expose dbt marts + the unstructured feedback table to any
MCP-capable AI assistant (Claude Desktop, Claude Code, etc.).

Architecture and video script: [`docs/11_mcp_architecture.md`](../docs/11_mcp_architecture.md).

## Prereqs

- Python 3.12 in `.venv`
- `dbt/airline.duckdb` materialised (run `dbt build` in `dbt/` once)

## Smoke test (end-to-end protocol check)

```bash
.venv/Scripts/python -m mcp_server.smoke_test
```

Expected: the three brief questions answered, each via a tool call.

## Wire Claude Desktop

1. Open `mcp_server/claude_desktop_config.json` and replace `<PROJECT_ROOT>` with the absolute path.
2. Paste into:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
3. Restart Claude Desktop fully.
4. In a new conversation, three tools should appear under `air-cote-divoire`.

## Folder

```
mcp_server/
├── __main__.py             python -m mcp_server  → mcp.run("stdio")
├── server.py               FastMCP instance + the 3 tools inline
├── db.py                   read-only DuckDB connection
├── safety.py               safe_query() with audit envelope + row cap
├── smoke_test.py           end-to-end check via the real MCP protocol
└── claude_desktop_config.json
```

## Why `mcp_server` and not `mcp`

The SDK we depend on is named `mcp`. A local package with the same name would shadow `from mcp.server.fastmcp import FastMCP` and break every import.

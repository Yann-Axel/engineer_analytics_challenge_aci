"""
Air Côte d'Ivoire MCP Server — entrypoint.

Exposes the dbt marts + ontology to any MCP-capable AI assistant
(Claude Desktop, Claude Code, third-party clients).

Transport: stdio (default for local single-user demos).

Run locally:
    python -m mcp_server.server

Wire into Claude Desktop: see mcp_server/claude_desktop_config.json
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

# Single FastMCP instance shared by all tool/resource modules.
mcp = FastMCP(
    name="Air Côte d'Ivoire Analytics",
    instructions=(
        "You expose Air Côte d'Ivoire's growth-allocation analytics: "
        "the dbt marts (structured), the customer feedback text (unstructured), "
        "and five inferred ontology concepts (High-Value At-Risk Customer, "
        "Strategic Underperforming Route, Premium Upsell Candidate, Loyal "
        "Detractor, IROPS-Heavy Route). When answering a business question, "
        "prefer calling an ontology tool first if one matches, then complement "
        "with a KPI or feedback search."
    ),
)


# ─── Register tools (deferred import to keep startup lean) ──────────────
# Each module attaches its tools to the shared `mcp` instance.
from mcp_server.tools import ontology, kpis, nlp, decision   # noqa: E402,F401
from mcp_server.resources import glossary                     # noqa: E402,F401

# NOTE: do not add `if __name__ == "__main__": mcp.run(...)` here. Running
# `python -m mcp_server.server` would load this module TWICE (once as
# mcp_server.server during the tool imports, once as __main__), producing
# two distinct FastMCP instances — the tools register on the first, but
# mcp.run() would be called on the second (empty) one. Use the
# `__main__.py` entrypoint instead: `python -m mcp_server`.

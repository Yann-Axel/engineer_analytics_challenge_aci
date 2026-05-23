"""
End-to-end smoke test of the MCP server over stdio.

Simulates exactly what Claude Desktop does: spawn the server as a
subprocess on stdio, initialise the protocol, list tools, and answer
the 5 grounded questions of the brief by invoking the right tools.

Run it AFTER setting up the venv and running `dbt build`:

    .venv/Scripts/python -m mcp_server.smoke_test

If this script prints "5/5 questions answered" the server is ready
for Claude Desktop.
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _format_rows(result: Any, max_rows: int = 3, max_chars_per_field: int = 80) -> str:
    """Pretty-print a few rows of a tool result for the console."""
    try:
        payload = json.loads(result.content[0].text)
    except Exception:
        return str(result)[:500]

    if "error" in payload:
        return f"  ERROR: {payload['error']}"

    rows = payload.get("rows", [])
    if not rows:
        return "  (no rows)"

    out = [f"  description: {payload.get('description', '?')}"]
    out.append(f"  row_count: {payload.get('row_count')}  (truncated={payload.get('truncated')})")
    for r in rows[:max_rows]:
        parts = []
        for k, v in r.items():
            s = str(v)
            if len(s) > max_chars_per_field:
                s = s[:max_chars_per_field] + "…"
            parts.append(f"{k}={s}")
        out.append("    • " + " | ".join(parts))
    if len(rows) > max_rows:
        out.append(f"    … +{len(rows) - max_rows} more")
    return "\n".join(out)


async def run_smoke_test() -> int:
    """Boot the MCP server and exercise the 5 grounded questions."""

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server"],   # __main__.py — single FastMCP instance
    )

    print(">>> Spawning MCP server on stdio…")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("  ✓ Server initialised")

            # Inventory
            tools_result = await session.list_tools()
            resources_result = await session.list_resources()
            print(f"  ✓ Tools     : {len(tools_result.tools)}")
            print(f"  ✓ Resources : {len(resources_result.resources)}")

            answered = 0
            print()

            # ─── Q1 from brief ─────────────────────────────────────────
            print("━" * 70)
            print("Q1 — Which routes deserve more budget next quarter?")
            print("━" * 70)
            print(">>> Calling list_strategic_underperforming_routes()")
            r = await session.call_tool("list_strategic_underperforming_routes", {"limit": 5})
            print(_format_rows(r))
            print()
            print(">>> Calling list_irops_heavy_routes()")
            r = await session.call_tool("list_irops_heavy_routes", {})
            print(_format_rows(r))
            answered += 1
            print()

            # ─── Q2 from brief ─────────────────────────────────────────
            print("━" * 70)
            print("Q2 — Which high-value customers are at risk?")
            print("━" * 70)
            print(">>> Calling list_high_value_at_risk_customers(limit=5, sort_by='ltv')")
            r = await session.call_tool(
                "list_high_value_at_risk_customers",
                {"limit": 5, "sort_by": "ltv"},
            )
            print(_format_rows(r))
            answered += 1
            print()

            # ─── Q3 from brief ─────────────────────────────────────────
            print("━" * 70)
            print("Q3 — What complaints are driving low satisfaction on route R005?")
            print("━" * 70)
            print(">>> Calling get_network_summary(period_months=12, route_id='R005')")
            r = await session.call_tool(
                "get_network_summary",
                {"period_months": 12, "route_id": "R005"},
            )
            print(_format_rows(r))
            print()
            print(">>> Calling search_feedback_text(route_id='R005', sentiment_label='negative', limit=4)")
            r = await session.call_tool(
                "search_feedback_text",
                {"route_id": "R005", "sentiment_label": "negative", "limit": 4},
            )
            print(_format_rows(r, max_chars_per_field=150))
            answered += 1
            print()

            # ─── Q4 (acceptance bonus) ─────────────────────────────────
            print("━" * 70)
            print("Q4 — Compare R009 (ABJ-CDG) and R008 (ABJ-OUA) on financial + satisfaction")
            print("━" * 70)
            print(">>> Calling compare_routes('R009', 'R008')")
            r = await session.call_tool(
                "compare_routes",
                {"route_id_a": "R009", "route_id_b": "R008"},
            )
            print(_format_rows(r))
            answered += 1
            print()

            # ─── Q5 (acceptance bonus) ─────────────────────────────────
            print("━" * 70)
            print("Q5 — Which customers should receive premium offers?")
            print("━" * 70)
            print(">>> Calling list_premium_upsell_candidates(tier='Gold', limit=5)")
            r = await session.call_tool(
                "list_premium_upsell_candidates",
                {"tier": "Gold", "limit": 5},
            )
            print(_format_rows(r))
            answered += 1
            print()

            # ─── Resource sanity ───────────────────────────────────────
            print("━" * 70)
            print("Resource — glossary://airline-business")
            print("━" * 70)
            content = await session.read_resource("glossary://airline-business")
            text = content.contents[0].text if content.contents else ""
            print(f"  {len(text)} chars, starts with: {text[:80]!r}")
            print()

            print(f"=== {answered}/5 questions answered via the MCP protocol ===")
            return 0 if answered == 5 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_smoke_test()))

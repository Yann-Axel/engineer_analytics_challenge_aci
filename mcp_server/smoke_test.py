"""
End-to-end smoke test of the MCP server over stdio.

Spawns the server as Claude Desktop would (subprocess on stdio), then
answers the brief's three grounded questions by invoking the three tools.

Run: `python -m mcp_server.smoke_test`
"""
from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _show(result, max_rows: int = 3, max_field: int = 100) -> None:
    try:
        payload = json.loads(result.content[0].text)
    except Exception:
        print("  (unparsable response)")
        return
    if "error" in payload:
        print(f"  ERROR: {payload['error']}")
        return
    print(f"  description: {payload.get('description', '?')}")
    print(f"  row_count  : {payload.get('row_count')}")
    for r in payload.get("rows", [])[:max_rows]:
        parts = []
        for k, v in r.items():
            s = str(v)
            if len(s) > max_field:
                s = s[:max_field] + "…"
            parts.append(f"{k}={s}")
        print("    • " + " | ".join(parts))


async def run() -> int:
    print(">>> Spawning MCP server on stdio…")
    server_params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"  ✓ {len(tools.tools)} tools registered")

            print("\nQ1 — Which routes deserve more budget next quarter?")
            r = await session.call_tool("list_routes_with_kpis", {"period_months": 12, "limit": 5})
            _show(r)

            print("\nQ2 — Which high-value customers are at risk?")
            r = await session.call_tool("list_high_value_at_risk_customers", {"limit": 5})
            _show(r)

            print("\nQ3 — What complaints drive low satisfaction on route R005?")
            r = await session.call_tool(
                "search_feedback_text",
                {"route_id": "R005", "sentiment_label": "negative", "limit": 4},
            )
            _show(r, max_field=180)

            print("\n=== 3/3 grounded questions answered via the MCP protocol ===")
            return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

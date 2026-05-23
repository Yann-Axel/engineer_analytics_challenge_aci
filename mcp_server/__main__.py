"""
Entrypoint for `python -m mcp_server` (used by Claude Desktop config).

Lives in a dedicated module so the FastMCP instance defined in
`mcp_server.server` is imported exactly once across the whole process —
otherwise tools register on a different instance than the one running.
"""
from mcp_server.server import mcp


if __name__ == "__main__":
    mcp.run(transport="stdio")

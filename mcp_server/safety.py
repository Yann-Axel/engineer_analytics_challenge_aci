"""
Safety + audit layer for the MCP server.

Every tool calls `safe_query()` instead of running DuckDB directly. This:
  1. Caps results at MAX_ROWS to avoid blowing the LLM context.
  2. Captures the SQL + params in the response so an exec can audit
     exactly what was asked.
  3. Forces parameterised queries — tools never f-string user input
     into SQL.
  4. Wraps any DB exception into a structured error payload.
"""
from __future__ import annotations

import datetime as dt
import decimal
from typing import Any

from .db import get_connection

MAX_ROWS = 1_000


def _jsonify(value: Any) -> Any:
    """Convert DuckDB values to JSON-serialisable Python primitives."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    return str(value)


def safe_query(
    sql: str,
    params: list | tuple | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Execute a parameterised SQL query against the read-only DuckDB and
    return a JSON-friendly envelope.

    The response shape is uniform across all tools so the LLM gets a
    predictable contract:
        {
          "description": "...",   # human-readable purpose of this query
          "sql":         "...",   # the actual SQL executed (audit trail)
          "params":      [...],   # bound parameters
          "row_count":   N,
          "truncated":   bool,    # true if hit MAX_ROWS
          "rows":        [{...}, ...]
        }

    Errors return:
        {"error": "...", "sql": "...", "params": [...]}
    """
    con = get_connection()
    try:
        result = con.execute(sql, list(params) if params else [])
        cols = [d[0] for d in result.description] if result.description else []
        rows = result.fetchmany(MAX_ROWS)
        return {
            "description": description or "Query result",
            "sql": sql,
            "params": list(params) if params else [],
            "row_count": len(rows),
            "truncated": len(rows) == MAX_ROWS,
            "rows": [{c: _jsonify(v) for c, v in zip(cols, r)} for r in rows],
        }
    except Exception as e:
        return {
            "error": str(e),
            "sql": sql,
            "params": list(params) if params else [],
        }

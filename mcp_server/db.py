"""
Shared DuckDB read-only connection for the MCP server.

The connection is opened lazily (first call) and cached for the lifetime of
the server process. Read-only mode is enforced at the DuckDB level — no
write of any kind is possible, regardless of the SQL sent.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DUCKDB_PATH = PROJECT_ROOT / "dbt" / "airline.duckdb"

_CONN: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return the shared read-only DuckDB connection (lazy + cached)."""
    global _CONN
    if _CONN is None:
        if not DUCKDB_PATH.exists():
            raise FileNotFoundError(
                f"Expected DuckDB file at {DUCKDB_PATH}. "
                f"Run `dbt build` in dbt/ first to materialise the marts."
            )
        _CONN = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    return _CONN


def close_connection() -> None:
    """Tear down the shared connection — used in tests."""
    global _CONN
    if _CONN is not None:
        _CONN.close()
        _CONN = None

"""
Safety + envelope contract tests.

These guarantee:
  * Every tool result carries the audit envelope (sql, params, row_count, rows).
  * MAX_ROWS is enforced.
  * Errors are returned as structured payloads, never as raised exceptions.
  * DuckDB is opened read-only (write attempts are rejected by the engine).
"""
from __future__ import annotations

from mcp_server.safety import MAX_ROWS, safe_query


def test_envelope_contract_on_success():
    """safe_query must always return the full envelope on a successful query."""
    result = safe_query("SELECT 1 AS x", description="trivial")
    assert "error" not in result
    for key in ("description", "sql", "params", "row_count", "truncated", "rows"):
        assert key in result, f"Missing key: {key}"
    assert result["rows"] == [{"x": 1}]
    assert result["row_count"] == 1
    assert result["truncated"] is False


def test_envelope_contract_on_failure():
    """A failing query returns a structured error, not an exception."""
    result = safe_query("SELECT * FROM table_that_does_not_exist")
    assert "error" in result
    assert "sql" in result
    # The error must be a string, not an exception object
    assert isinstance(result["error"], str)


def test_row_limit_truncates_at_max_rows():
    """Queries that would return > MAX_ROWS rows must be truncated."""
    # generate_series gives us a predictable many-rows source
    result = safe_query(f"SELECT i FROM generate_series(1, {MAX_ROWS + 100}) AS t(i)")
    assert result["row_count"] == MAX_ROWS
    assert result["truncated"] is True


def test_parameterised_sql_binds_safely():
    """Parameters must be bound, not f-stringed."""
    result = safe_query("SELECT ? AS v", ["o'malley"])  # apostrophe = SQL injection canary
    assert "error" not in result
    assert result["rows"] == [{"v": "o'malley"}]


def test_write_attempt_is_rejected_by_readonly_engine():
    """The DuckDB connection is opened read-only — any DDL/DML must fail."""
    result = safe_query("CREATE TABLE wont_work (x INT)")
    assert "error" in result, "Write should have been rejected"
    assert "read" in result["error"].lower() or "readonly" in result["error"].lower()

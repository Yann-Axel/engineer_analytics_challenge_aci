"""
Configure the default datetime column (`main_dttm_col`) on each dataset that
has a time-based chart. Without this, Superset's time-grain charts fail with
"Datetime column not provided as part table configuration".

We write directly to the Superset metastore because:
- Superset 4.1.2's REST endpoints don't expose `main_dttm_col` cleanly.
- This is an idempotent one-shot fix tied to our dataset schema.

Two execution modes:
- If env var `SUPERSET_DB_PATH` is set (e.g. inside the provisioner container
  that mounts the `superset_home` volume), open the SQLite file directly.
- Otherwise (host mode), shell out to `docker exec airline-superset ...`.
"""
from __future__ import annotations

import os
import subprocess
import sys

DTTM_BY_TABLE = {
    "fct_flights":               "flight_date",
    "fct_bookings":              "booking_date",
    "fct_customer_feedback":     "feedback_date",
    "fct_ancillary_offers":      "offer_date",
    "fct_loyalty_events":        "event_date",
    "int_route_monthly_perf":    "period_month",
    "int_route_complaint_themes":"period_month",
    "dim_date":                  "date_day",
}

SUPERSET_DB_PATH = os.environ.get("SUPERSET_DB_PATH")


def _apply(db_path: str) -> None:
    import sqlite3
    con = sqlite3.connect(db_path)
    for table_name, dttm_col in DTTM_BY_TABLE.items():
        con.execute(
            "UPDATE tables SET main_dttm_col = ? WHERE table_name = ?",
            (dttm_col, table_name),
        )
        con.execute(
            """UPDATE table_columns
               SET is_dttm = 1
               WHERE column_name = ?
                 AND table_id = (SELECT id FROM tables WHERE table_name = ?)""",
            (dttm_col, table_name),
        )
    con.commit()
    print("Configured", len(DTTM_BY_TABLE), "datasets")
    for r in con.execute(
        "SELECT table_name, main_dttm_col FROM tables WHERE main_dttm_col IS NOT NULL"
    ):
        print(" ", r)
    con.close()


def main() -> int:
    print(">>> Configuring main_dttm_col on time-series datasets")
    if SUPERSET_DB_PATH:
        _apply(SUPERSET_DB_PATH)
        return 0
    # Host mode: drive sqlite via docker exec inside airline-superset
    script = (
        "import sqlite3\n"
        "mapping = " + repr(DTTM_BY_TABLE) + "\n"
        "con = sqlite3.connect('/app/superset_home/superset.db')\n"
        "for table_name, dttm_col in mapping.items():\n"
        "    con.execute('UPDATE tables SET main_dttm_col = ? WHERE table_name = ?', (dttm_col, table_name))\n"
        "    con.execute('''UPDATE table_columns SET is_dttm = 1 WHERE column_name = ? AND table_id = (SELECT id FROM tables WHERE table_name = ?)''', (dttm_col, table_name))\n"
        "con.commit()\n"
        "print('Configured', len(mapping), 'datasets')\n"
        "for r in con.execute('SELECT table_name, main_dttm_col FROM tables WHERE main_dttm_col IS NOT NULL'):\n"
        "    print(' ', r)\n"
    )
    result = subprocess.run(
        ["docker", "exec", "airline-superset", "python", "-c", script],
        capture_output=True, text=True, timeout=60,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

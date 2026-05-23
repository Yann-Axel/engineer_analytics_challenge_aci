"""
Configure the default datetime column (`main_dttm_col`) on each dataset that
has a time-based chart. Without this, Superset's time-grain charts fail with
"Datetime column not provided as part table configuration".

We write directly to the Superset metastore via `docker exec`, because:
- Superset 4.1.2's REST endpoints don't expose `main_dttm_col` cleanly.
- This is an idempotent one-shot fix tied to our dataset schema.
"""
from __future__ import annotations

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


def main() -> int:
    print(">>> Configuring main_dttm_col on time-series datasets")
    script = """
import sqlite3
con = sqlite3.connect('/app/superset_home/superset.db')
mapping = """ + repr(DTTM_BY_TABLE) + """
for table_name, dttm_col in mapping.items():
    # 1) Set main_dttm_col on the table
    con.execute(
        'UPDATE tables SET main_dttm_col = ? WHERE table_name = ?',
        (dttm_col, table_name),
    )
    # 2) Mark the column as a datetime column (is_dttm = 1)
    con.execute(
        '''UPDATE table_columns
           SET is_dttm = 1
           WHERE column_name = ?
             AND table_id = (SELECT id FROM tables WHERE table_name = ?)''',
        (dttm_col, table_name),
    )
con.commit()
print('Configured', len(mapping), 'datasets')
for r in con.execute('SELECT table_name, main_dttm_col FROM tables WHERE main_dttm_col IS NOT NULL'):
    print(' ', r)
"""
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

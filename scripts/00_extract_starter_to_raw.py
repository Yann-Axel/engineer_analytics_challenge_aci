"""
Extracts the starter Excel workbook into individual Parquet files in data/raw/.
Raw layer is immutable: a faithful 1:1 copy of the source. No transformation here.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STARTER_XLSX = PROJECT_ROOT / "air_cote_divoire_starter_dataset.xlsx"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SHEETS = ["Airports", "Routes", "Customers", "Flights", "Bookings"]


def main() -> None:
    xl = pd.ExcelFile(STARTER_XLSX)
    print(f"Source: {STARTER_XLSX.name}")
    print(f"Target: {RAW_DIR}")
    for sheet in SHEETS:
        df = pd.read_excel(xl, sheet_name=sheet)
        out_path = RAW_DIR / f"{sheet.lower()}.parquet"
        df.to_parquet(out_path, index=False)
        print(f"  - {sheet:10s} -> {out_path.name:25s} ({len(df):>6,} rows, {df.shape[1]} cols)")
    print("Raw layer ready.")


if __name__ == "__main__":
    main()

"""
Step 11 - Generate the Flights fact (24 months, 2024-01-01 -> 2025-12-31).

Logic:
  - Iterate over routes with a weekly frequency target (mean), modulated by seasonality.
  - Distribute weekly flights across days-of-week with a smoothing pattern.
  - Assign an aircraft tail (from the fleet) compatible with the route type.
  - Compute scheduled times from canonical "departure waves" per route_type.
  - Apply realistic on-time / delay / cancellation distribution per route_type & season.

Output: data/enriched/flights.parquet
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from lib.config import (
    AIRCRAFT_TYPE_CAPACITY,
    CANCELLATION_RATE,
    END_DATE,
    ENRICHED_DIR,
    ROUTE_TYPE_AIRCRAFT,
    ROUTE_WEEKLY_FREQUENCY,
    SEASONAL_MULTIPLIER,
    START_DATE,
)
from lib.utils import daterange, get_rng, write_parquet


# Canonical departure waves (local time, simplified)
DEPARTURE_WAVES = {
    "Domestic":      [time(7, 30), time(11, 0), time(15, 30), time(18, 45)],
    "Regional":      [time(6, 45), time(9, 30), time(13, 15), time(17, 30), time(20, 0)],
    "International": [time(9, 0), time(22, 30)],  # mostly red-eye / morning
}


def pick_aircraft(route_type: str, distance_km: int, fleet: pd.DataFrame, rng: np.random.Generator) -> str:
    """Pick a tail_number from the fleet for the given route type."""
    compatible_types = ROUTE_TYPE_AIRCRAFT[route_type]
    if route_type == "International" and distance_km > 3500:
        compatible_types = ["A330-900neo"]
    compatible = fleet[fleet["aircraft_type"].isin(compatible_types)]
    if compatible.empty:
        compatible = fleet
    return str(rng.choice(compatible["tail_number"].values))


def main() -> None:
    print("=== Step 11: Flights (24 months) ===")
    rng = get_rng(stream=11)

    routes = pd.read_parquet(ENRICHED_DIR / "routes.parquet")
    fleet  = pd.read_parquet(ENRICHED_DIR / "aircraft.parquet")

    records = []
    flight_counter = 1

    for _, route in routes.iterrows():
        route_id = route["route_id"]
        route_type = route["route_type"]
        distance_km = int(route["distance_km"])
        block_min = int(route["block_time_min"])
        weekly_freq = ROUTE_WEEKLY_FREQUENCY.get(route_id, 0)
        if weekly_freq == 0:
            continue  # candidate route, no operated flights

        waves = DEPARTURE_WAVES[route_type]

        for day in daterange(START_DATE, END_DATE):
            seasonal = SEASONAL_MULTIPLIER[day.month]
            # Daily frequency = weekly / 7 * seasonal, with Poisson jitter
            daily_lambda = (weekly_freq / 7.0) * seasonal
            n_flights = rng.poisson(daily_lambda)

            for k in range(int(n_flights)):
                wave_choice = waves[k % len(waves)]
                # Add minor noise around the wave time
                noise_min = int(rng.integers(-15, 16))
                scheduled_dep_dt = datetime.combine(day, wave_choice) + timedelta(minutes=noise_min)
                scheduled_arr_dt = scheduled_dep_dt + timedelta(minutes=block_min)

                # Pick aircraft (and resolve seat capacity)
                tail = pick_aircraft(route_type, distance_km, fleet, rng)
                aircraft_type = str(fleet.loc[fleet["tail_number"] == tail, "aircraft_type"].iloc[0])
                capacity = AIRCRAFT_TYPE_CAPACITY[aircraft_type]

                # Status: cancellation first, then delay distribution
                base_cancel_prob = CANCELLATION_RATE[route_type]
                # Boost cancellation during rainy season for ABJ (Jun-Aug)
                if route_type in ("Domestic", "Regional") and day.month in (6, 7, 8):
                    base_cancel_prob *= 1.5
                if rng.random() < base_cancel_prob:
                    status = "Cancelled"
                    delay_min = np.nan
                    actual_dep = pd.NaT
                    actual_arr = pd.NaT
                else:
                    # Delay distribution: most on-time, long-tail
                    # 65% on-time (<=15min), 25% mild (15-60), 8% moderate (60-180), 2% severe (>180)
                    r = rng.random()
                    if r < 0.65:
                        delay_min = int(rng.integers(0, 16))
                        status = "On Time"
                    elif r < 0.90:
                        delay_min = int(rng.integers(16, 61))
                        status = "Delayed"
                    elif r < 0.98:
                        delay_min = int(rng.integers(61, 181))
                        status = "Delayed"
                    else:
                        delay_min = int(rng.integers(181, 360))
                        status = "Delayed"
                    actual_dep = scheduled_dep_dt + timedelta(minutes=int(delay_min))
                    actual_arr = scheduled_arr_dt + timedelta(minutes=int(delay_min))

                flight_id = f"FLT{flight_counter:06d}"
                flight_number = f"HF{100 + (hash(route_id) % 900)}"
                records.append({
                    "flight_id": flight_id,
                    "flight_number": flight_number,
                    "route_id": route_id,
                    "tail_number": tail,
                    "flight_date": pd.Timestamp(day),
                    "scheduled_departure": pd.Timestamp(scheduled_dep_dt),
                    "actual_departure": actual_dep,
                    "scheduled_arrival": pd.Timestamp(scheduled_arr_dt),
                    "actual_arrival": actual_arr,
                    "aircraft_type": aircraft_type,
                    "seat_capacity": capacity,
                    "flight_status": status,
                    "delay_min": delay_min,
                })
                flight_counter += 1

    df = pd.DataFrame.from_records(records)
    df = df.sort_values(["flight_date", "scheduled_departure"]).reset_index(drop=True)
    write_parquet(df, ENRICHED_DIR / "flights.parquet")

    # Quick sanity report
    print("\nSummary:")
    print(f"  Total flights      : {len(df):,}")
    print(f"  Date span          : {df['flight_date'].min().date()} -> {df['flight_date'].max().date()}")
    print(f"  Status mix         : {df['flight_status'].value_counts(normalize=True).round(3).to_dict()}")
    print(f"  Aircraft type mix  : {df['aircraft_type'].value_counts(normalize=True).round(3).to_dict()}")
    print(f"  Flights per route  :")
    for rid, n in df["route_id"].value_counts().sort_index().items():
        print(f"     {rid}: {n:>5}")


if __name__ == "__main__":
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    main()

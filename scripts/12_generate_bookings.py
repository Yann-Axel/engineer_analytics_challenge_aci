"""
Step 12 - Generate the Bookings fact, calibrated to realistic load factor (~70%) and a long-tail customer activity distribution.

Approach (vectorised):
  1. For each operated flight, draw a target load factor from a route-type-specific
     distribution (Beta), modulated by seasonality.
  2. Round to integer passenger count, cap at seat_capacity.
  3. Allocate passenger seats to customers drawn from the activity-bucket pool.
     Power users and regulars are picked proportionally more often.
  4. Sample fare_class, fare_family, channel, price, ancillary_revenue per booking.

Output: data/enriched/bookings.parquet
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from lib.config import (
    BASE_PRICE_USD,
    BOOKING_CHANNEL_MIX,
    CUSTOMER_ACTIVITY_BUCKETS,
    ENRICHED_DIR,
    FARE_CLASS_MIX,
    FARE_CLASS_PRICE_MULT,
    FARE_FAMILY_MIX,
    FARE_FAMILY_PRICE_MULT,
    LOAD_FACTOR_TARGET,
    SEASONAL_MULTIPLIER,
)
from lib.utils import get_rng, write_parquet


def assign_activity_buckets(customers: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Tag each customer with an activity bucket + target booking count."""
    n = len(customers)
    bucket_names  = [b[0] for b in CUSTOMER_ACTIVITY_BUCKETS]
    bucket_probs  = [b[1] for b in CUSTOMER_ACTIVITY_BUCKETS]
    bucket_ranges = {b[0]: b[2] for b in CUSTOMER_ACTIVITY_BUCKETS}

    buckets = rng.choice(bucket_names, size=n, p=bucket_probs)
    target_bookings = np.zeros(n, dtype=int)
    for name, (lo, hi) in bucket_ranges.items():
        mask = buckets == name
        if lo == hi:
            target_bookings[mask] = lo
        else:
            target_bookings[mask] = rng.integers(lo, hi + 1, size=int(mask.sum()))

    customers = customers.copy()
    customers["activity_bucket"] = buckets
    customers["target_bookings"] = target_bookings
    return customers


def sample_passengers_for_flight(seat_capacity: int, route_type: str, month: int, rng: np.random.Generator) -> int:
    """Draw a realistic number of passengers on a given flight."""
    target_lf = LOAD_FACTOR_TARGET[route_type]
    # Beta distribution centred on target_lf, with seasonality bumping the mean.
    seasonal = SEASONAL_MULTIPLIER[month]
    mean_lf = min(0.95, target_lf * (0.85 + 0.15 * seasonal))
    # Beta(a,b) with mean = a / (a+b) ; pick a moderate concentration.
    concentration = 25.0
    a = mean_lf * concentration
    b = (1 - mean_lf) * concentration
    lf = rng.beta(a, b)
    return int(round(lf * seat_capacity))


def main() -> None:
    print("=== Step 12: Bookings ===")
    rng = get_rng(stream=12)

    flights = pd.read_parquet(ENRICHED_DIR / "flights.parquet")
    routes  = pd.read_parquet(ENRICHED_DIR / "routes.parquet").set_index("route_id")
    customers = pd.read_parquet(ENRICHED_DIR / "customers.parquet")

    customers = assign_activity_buckets(customers, rng)
    # Pool of customer_ids with weights for sampling.
    eligible = customers[customers["target_bookings"] > 0].copy()
    weights = eligible["target_bookings"].astype(float).values
    weights /= weights.sum()
    cust_ids = eligible["customer_id"].values

    # Annotate flights with route_type for vectorisation
    flights = flights.merge(routes[["route_type"]], on="route_id", how="left")

    # We only generate bookings for flights that are not yet cancelled.
    operated = flights[flights["flight_status"] != "Cancelled"].copy()
    operated["month"] = operated["flight_date"].dt.month

    # Compute passenger count per flight
    print("  Drawing passenger counts per flight...")
    pax_counts = np.array([
        sample_passengers_for_flight(int(r.seat_capacity), r.route_type, int(r.month), rng)
        for r in operated.itertuples()
    ])
    operated["pax_count"] = pax_counts

    total_bookings = int(operated["pax_count"].sum())
    print(f"  Target booking count: {total_bookings:,}")

    # ---- Vectorised booking creation ----
    # Repeat each flight row by its pax_count
    repeats = operated["pax_count"].values
    flight_ids   = np.repeat(operated["flight_id"].values, repeats)
    flight_dates = np.repeat(operated["flight_date"].values, repeats)
    route_types  = np.repeat(operated["route_type"].values, repeats)

    n = len(flight_ids)

    # Sample customers (with replacement, weighted)
    cust_assign = rng.choice(cust_ids, size=n, p=weights)

    # Sample booking attributes
    fare_class = rng.choice(
        list(FARE_CLASS_MIX.keys()), size=n, p=list(FARE_CLASS_MIX.values())
    )
    fare_family = rng.choice(
        list(FARE_FAMILY_MIX.keys()), size=n, p=list(FARE_FAMILY_MIX.values())
    )
    channel = rng.choice(
        list(BOOKING_CHANNEL_MIX.keys()), size=n, p=list(BOOKING_CHANNEL_MIX.values())
    )

    # Pricing
    base_price = np.array([BASE_PRICE_USD[rt] for rt in route_types])
    fc_mult = np.array([FARE_CLASS_PRICE_MULT[fc] for fc in fare_class])
    ff_mult = np.array([FARE_FAMILY_PRICE_MULT[ff] for ff in fare_family])
    noise   = rng.normal(1.0, 0.12, size=n).clip(0.65, 1.6)
    ticket_price = (base_price * fc_mult * ff_mult * noise).round(2)

    # Ancillary: ~80% attach rate, value depends on fare_class/family
    attach = rng.random(n) < np.where(fare_class == "Business", 0.92,
                                np.where(fare_class == "Premium Economy", 0.85, 0.78))
    ancillary = np.where(attach, rng.gamma(2.2, 11, size=n), 0).round(2)
    bags_count = np.where(rng.random(n) < 0.70, rng.integers(1, 3, size=n), 0)
    seat_selection = (rng.random(n) < 0.55).astype(int)

    # Booking date: between (-90 days) and (-1 day) from flight_date, weighted toward closer to flight
    days_ahead = rng.gamma(2.0, 10, size=n).clip(1, 200).astype(int)
    booking_dates = pd.to_datetime(flight_dates) - pd.to_timedelta(days_ahead, unit="D")

    # Booking status: depends on whether flight has occurred (flight_date < today)
    # For simplicity: 92% Flown / 4% Confirmed (future) / 3% No Show / 1% Changed
    today = pd.Timestamp("2026-01-01")
    is_past = pd.to_datetime(flight_dates) < today
    status = np.where(
        is_past,
        rng.choice(["Flown", "No Show", "Changed"], size=n, p=[0.94, 0.04, 0.02]),
        "Confirmed",
    )

    # Build the dataframe
    bookings = pd.DataFrame({
        "booking_id": [f"BKG{i+1:07d}" for i in range(n)],
        "booking_date": booking_dates,
        "customer_id": cust_assign,
        "flight_id": flight_ids,
        "booking_channel": channel,
        "fare_class": fare_class,
        "fare_family": fare_family,
        "ticket_price_usd": ticket_price,
        "ancillary_revenue_usd": ancillary,
        "bags_count": bags_count,
        "seat_selection_flag": seat_selection,
        "booking_status": status,
    })

    write_parquet(bookings, ENRICHED_DIR / "bookings.parquet")
    write_parquet(customers.drop(columns=["activity_bucket", "target_bookings"]),
                  ENRICHED_DIR / "customers.parquet")
    # Also keep the activity bucket meta for downstream analyses
    customers[["customer_id", "activity_bucket", "target_bookings"]].to_parquet(
        ENRICHED_DIR / "customers_activity_meta.parquet", index=False
    )

    # Quick summary
    print("\nSummary:")
    print(f"  Total bookings: {len(bookings):,}")
    print(f"  Booking status mix: {bookings['booking_status'].value_counts(normalize=True).round(3).to_dict()}")
    print(f"  Fare class mix    : {bookings['fare_class'].value_counts(normalize=True).round(3).to_dict()}")
    print(f"  Avg ticket price  : {bookings['ticket_price_usd'].mean():.2f} USD")
    print(f"  Ancillary attach  : {(bookings['ancillary_revenue_usd']>0).mean()*100:.1f}%")
    # Approximate load factor
    pax_per_flight = bookings.groupby("flight_id").size()
    capacities = flights.set_index("flight_id")["seat_capacity"]
    lf = (pax_per_flight / capacities).dropna()
    print(f"  Realised LF       : mean={lf.mean():.2f}, p10={lf.quantile(0.1):.2f}, p90={lf.quantile(0.9):.2f}")
    # Active customer share
    active = bookings["customer_id"].nunique()
    print(f"  Active customers  : {active}/{len(customers)} ({active/len(customers)*100:.1f}%)")


if __name__ == "__main__":
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    main()

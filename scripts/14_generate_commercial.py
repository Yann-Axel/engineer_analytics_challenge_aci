"""
Step 14 - Commercial / loyalty layer:
  - loyalty_activity.parquet  (earn + redeem events per customer)
  - ancillary_offers.parquet  (offer presentation + accept flag per booking)
  - cargo_shipments.parquet   (long-haul cargo only)
  - competitors.parquet       (monthly snapshot per route/competitor)
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from lib.config import (
    ANCILLARY_TYPES,
    END_DATE,
    ENRICHED_DIR,
    LOYALTY_POINTS_PER_KM,
    LOYALTY_REDEEM_PROB_PER_BOOKING,
    START_DATE,
)
from lib.utils import get_rng, write_parquet


COMPETITORS_BY_ROUTE = {
    "R009": ["Air France", "Brussels Airlines", "Royal Air Maroc"],
    "R013": ["Air France", "Brussels Airlines", "Royal Air Maroc"],
    "R005": ["Asky Airlines", "Air Senegal"],
    "R011": ["Asky Airlines", "Air Senegal"],
    "R006": ["Asky Airlines", "Africa World Airlines"],
    "R012": ["Asky Airlines", "Africa World Airlines"],
    "R004": ["Africa World Airlines", "PassionAir"],
    "R010": ["Africa World Airlines", "PassionAir"],
    "R007": ["Asky Airlines"],
    "R008": ["Asky Airlines", "Air Burkina"],
    "R014": ["Royal Air Maroc", "Air France"],
    "R016": ["Emirates", "Ethiopian Airlines"],
}


def build_loyalty_activity(bookings: pd.DataFrame, customers: pd.DataFrame,
                           flights: pd.DataFrame, routes: pd.DataFrame,
                           rng: np.random.Generator) -> pd.DataFrame:
    """1 earn event per booking for loyalty members. Occasional redemptions."""
    members = customers[customers["loyalty_tier"].notna()].copy()
    member_set = set(members["customer_id"])
    tier_map = dict(zip(members["customer_id"], members["loyalty_tier"]))

    # Restrict to bookings of members on flown flights
    bm = bookings[bookings["customer_id"].isin(member_set)
                  & (bookings["booking_status"] == "Flown")].copy()

    # Merge route distance via flight -> route
    f_to_route = flights.set_index("flight_id")["route_id"].to_dict()
    bm["route_id"] = bm["flight_id"].map(f_to_route)
    dist_map = routes.set_index("route_id")["distance_km"].to_dict()
    bm["distance_km"] = bm["route_id"].map(dist_map).fillna(500).astype(int)
    bm["tier"] = bm["customer_id"].map(tier_map)

    # Earn events
    earn = bm.copy()
    earn["points_delta"] = (
        earn["distance_km"].astype(float)
        * earn["tier"].map(LOYALTY_POINTS_PER_KM).astype(float)
    ).round(0).astype(int)
    earn["event_type"] = "earn"
    earn["event_date"] = earn["booking_date"]
    earn = earn[["customer_id", "tier", "event_type", "points_delta", "event_date",
                 "flight_id", "route_id"]].rename(columns={"tier": "tier_at_event"})

    # Redemption events (separate)
    n_redeem = int(LOYALTY_REDEEM_PROB_PER_BOOKING * len(bm))
    if n_redeem > 0:
        idx = rng.choice(len(bm), size=n_redeem, replace=False)
        redeem = bm.iloc[idx].copy()
        redeem["points_delta"] = -rng.choice([2000, 5000, 10000, 20000], size=n_redeem,
                                              p=[0.4, 0.3, 0.2, 0.1])
        redeem["event_type"] = "redeem"
        redeem["event_date"] = redeem["booking_date"]
        redeem = redeem[["customer_id", "tier", "event_type", "points_delta", "event_date",
                         "flight_id", "route_id"]].rename(columns={"tier": "tier_at_event"})
        out = pd.concat([earn, redeem], ignore_index=True)
    else:
        out = earn

    out["loyalty_event_id"] = [f"LYE{i+1:08d}" for i in range(len(out))]
    return out[["loyalty_event_id", "customer_id", "tier_at_event", "event_type",
                "points_delta", "event_date", "flight_id", "route_id"]]


def build_ancillary_offers(bookings: pd.DataFrame, customers: pd.DataFrame,
                           rng: np.random.Generator) -> pd.DataFrame:
    """For each booking, present a subset of offers, with acceptance dependent on
    fare_class and customer segment."""
    cust_seg = customers.set_index("customer_id")["customer_segment"].to_dict()
    cust_tier = customers.set_index("customer_id")["loyalty_tier"].to_dict()

    rows = []
    offer_id_counter = 1

    # Vectorise: for each offer type, draw presentation across all bookings
    n = len(bookings)
    fare = bookings["fare_class"].values
    seg = bookings["customer_id"].map(cust_seg).fillna("Standard").values
    tier = bookings["customer_id"].map(cust_tier).fillna("None").values
    booking_ids = bookings["booking_id"].values
    booking_dates = bookings["booking_date"].values

    for offer_type, base_price, present_prob, base_accept in ANCILLARY_TYPES:
        # Eligibility: upgrade_J only from Premium Economy; upgrade_W only from Economy
        eligible = np.ones(n, dtype=bool)
        if offer_type == "upgrade_W":
            eligible = fare == "Economy"
        elif offer_type == "upgrade_J":
            eligible = fare == "Premium Economy"

        # Presentation probability adjusted by channel/segment
        present_p = np.full(n, present_prob)
        presented = (rng.random(n) < present_p) & eligible

        # Acceptance probability adjusted: Business/Premium segment + Gold tier accept more
        accept_p = np.full(n, base_accept)
        accept_p = np.where(seg == "Premium",  accept_p * 1.7, accept_p)
        accept_p = np.where(seg == "Business", accept_p * 1.4, accept_p)
        accept_p = np.where(tier == "Gold",    accept_p * 1.3, accept_p)
        accept_p = accept_p.clip(0, 0.95)

        accepted = presented & (rng.random(n) < accept_p)

        # Build rows (presented only)
        idx = np.where(presented)[0]
        if len(idx) == 0:
            continue

        offer_price = np.full(len(idx), base_price, dtype=float)
        # Add noise
        offer_price *= rng.normal(1.0, 0.10, size=len(idx)).clip(0.7, 1.4)
        # Upgrade prices scale with fare class baseline
        if offer_type in ("upgrade_W", "upgrade_J"):
            offer_price *= rng.normal(1.0, 0.20, size=len(idx)).clip(0.7, 1.8)

        rows.append(pd.DataFrame({
            "ancillary_offer_id": [f"AO{offer_id_counter + i:08d}" for i in range(len(idx))],
            "booking_id": booking_ids[idx],
            "offer_type": offer_type,
            "offer_price_usd": offer_price.round(2),
            "presented_flag": True,
            "accepted_flag": accepted[idx],
            "offer_date": booking_dates[idx],
        }))
        offer_id_counter += len(idx)

    return pd.concat(rows, ignore_index=True)


def build_cargo(flights: pd.DataFrame, routes: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Cargo only on long-haul or A330 widebody flights."""
    long_haul_routes = routes[routes["distance_km"] > 2500]["route_id"].tolist()
    eligible = flights[flights["route_id"].isin(long_haul_routes)
                       & (flights["flight_status"] != "Cancelled")]
    n_flights = len(eligible)
    if n_flights == 0:
        return pd.DataFrame(columns=["cargo_shipment_id", "flight_id", "weight_kg",
                                     "revenue_usd", "cargo_type", "shipper_country"])

    # 1-6 shipments per long-haul flight
    n_per_flight = rng.integers(1, 7, size=n_flights)
    flight_ids = np.repeat(eligible["flight_id"].values, n_per_flight)
    total = int(n_per_flight.sum())

    weights = rng.gamma(2.5, 200, size=total).clip(50, 4000).round(1)
    rate_per_kg = rng.normal(4.5, 1.0, size=total).clip(1.5, 9)
    revenue = (weights * rate_per_kg).round(2)
    cargo_types = rng.choice(
        ["General", "Perishable", "Mail", "Pharma", "Live Animals", "High-Value"],
        size=total, p=[0.40, 0.25, 0.10, 0.10, 0.05, 0.10],
    )
    shipper_countries = rng.choice(
        ["Côte d'Ivoire", "France", "Senegal", "Morocco", "UAE", "Ghana"],
        size=total, p=[0.35, 0.30, 0.10, 0.10, 0.10, 0.05],
    )

    return pd.DataFrame({
        "cargo_shipment_id": [f"CGO{i+1:07d}" for i in range(total)],
        "flight_id": flight_ids,
        "weight_kg": weights,
        "revenue_usd": revenue,
        "cargo_type": cargo_types,
        "shipper_country": shipper_countries,
    })


def build_competitors(rng: np.random.Generator) -> pd.DataFrame:
    """Monthly snapshot of competing fare and frequency per route."""
    rows = []
    months = pd.date_range(START_DATE, END_DATE, freq="MS")
    for route_id, comps in COMPETITORS_BY_ROUTE.items():
        for comp in comps:
            base_fare = rng.uniform(150, 900)
            base_freq = rng.integers(3, 14)
            for m in months:
                fare = round(base_fare * rng.normal(1.0, 0.07), 2)
                freq = int(max(1, base_freq + rng.integers(-2, 3)))
                rows.append((route_id, comp, m.date(), fare, freq))
    return pd.DataFrame(rows, columns=[
        "route_id", "competitor_name", "snapshot_month", "avg_fare_usd", "weekly_frequency"
    ])


def main() -> None:
    print("=== Step 14: Commercial layer ===")
    rng = get_rng(stream=14)

    customers = pd.read_parquet(ENRICHED_DIR / "customers.parquet")
    flights   = pd.read_parquet(ENRICHED_DIR / "flights.parquet")
    bookings  = pd.read_parquet(ENRICHED_DIR / "bookings.parquet")
    routes    = pd.read_parquet(ENRICHED_DIR / "routes.parquet")

    print("  Building loyalty activity...")
    loyalty = build_loyalty_activity(bookings, customers, flights, routes, rng)
    write_parquet(loyalty, ENRICHED_DIR / "loyalty_activity.parquet")

    print("  Building ancillary offers...")
    offers = build_ancillary_offers(bookings, customers, rng)
    write_parquet(offers, ENRICHED_DIR / "ancillary_offers.parquet")

    print("  Building cargo shipments...")
    cargo = build_cargo(flights, routes, rng)
    write_parquet(cargo, ENRICHED_DIR / "cargo_shipments.parquet")

    print("  Building competitors...")
    competitors = build_competitors(rng)
    write_parquet(competitors, ENRICHED_DIR / "competitors.parquet")

    print("\nSummary:")
    print(f"  Loyalty events    : {len(loyalty):,} ({(loyalty['event_type']=='earn').sum():,} earn / {(loyalty['event_type']=='redeem').sum():,} redeem)")
    print(f"  Ancillary offers  : {len(offers):,} presented, {offers['accepted_flag'].sum():,} accepted ({offers['accepted_flag'].mean()*100:.1f}%)")
    print(f"  Acceptance by type:\n{offers.groupby('offer_type')['accepted_flag'].mean().round(3).to_string()}")
    print(f"  Cargo shipments   : {len(cargo):,}, total revenue {cargo['revenue_usd'].sum():,.0f} USD")
    print(f"  Competitors       : {len(competitors):,} monthly observations")


if __name__ == "__main__":
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    main()

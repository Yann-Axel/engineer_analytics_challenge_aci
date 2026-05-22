"""
Step 10 - Generate enriched fleet & network reference tables.

Outputs to data/enriched/:
  - airports.parquet  (10 starter + 3 new = 13)
  - routes.parquet    (12 starter + 4 new = 16)
  - aircraft.parquet  (new entity: 9 tails)
  - customers.parquet (300 starter + 700 new = 1000)
"""
from __future__ import annotations

from datetime import datetime, date, timedelta

import numpy as np
import pandas as pd

from lib.config import (
    AIRCRAFT_TYPE_CAPACITY,
    ENRICHED_DIR,
    FLEET,
    NEW_AIRPORTS,
    NEW_CUSTOMERS_COUNT,
    NEW_ROUTES,
    RAW_DIR,
)
from lib.utils import first_names_pool, get_rng, last_names_pool, write_parquet


def build_airports() -> pd.DataFrame:
    starter = pd.read_parquet(RAW_DIR / "airports.parquet")
    new_rows = pd.DataFrame(NEW_AIRPORTS, columns=[
        "airport_code", "airport_name", "city", "country", "timezone", "latitude", "longitude"
    ])
    return pd.concat([starter, new_rows], ignore_index=True)


def build_routes() -> pd.DataFrame:
    starter = pd.read_parquet(RAW_DIR / "routes.parquet")
    starter["route_status"] = "operated"
    new_rows = pd.DataFrame(NEW_ROUTES, columns=[
        "route_id", "origin_airport_code", "destination_airport_code",
        "route_type", "distance_km", "block_time_min", "route_status",
    ])
    routes = pd.concat([starter, new_rows], ignore_index=True)
    # Tag whether route is strategically important (used in ontology layer later).
    routes["is_strategic"] = routes["route_id"].isin(
        ["R009", "R013", "R014", "R016"]  # CDG-ABJ both ways, Casa, Dubai
    )
    return routes


def build_aircraft() -> pd.DataFrame:
    cols = ["tail_number", "aircraft_type", "manufacturer", "build_year",
            "seats_business", "seats_premium_eco", "seats_economy", "fleet_status"]
    df = pd.DataFrame(FLEET, columns=cols)
    df["total_seats"] = df[["seats_business", "seats_premium_eco", "seats_economy"]].sum(axis=1)
    # Sanity vs canonical type capacity
    df["typed_capacity"] = df["aircraft_type"].map(AIRCRAFT_TYPE_CAPACITY)
    return df


def build_customers() -> pd.DataFrame:
    """Keep starter 300 customers untouched, add 700 new ones with realistic
    distribution of segments, loyalty tiers, channels, and origin countries."""
    starter = pd.read_parquet(RAW_DIR / "customers.parquet")
    rng = get_rng(stream=10)

    n = NEW_CUSTOMERS_COUNT
    customer_ids = [f"CUST{i:04d}" for i in range(301, 301 + n)]

    first_names = first_names_pool()
    last_names = last_names_pool()

    segments = rng.choice(
        ["Standard", "Business", "Budget", "Premium"],
        size=n, p=[0.50, 0.25, 0.18, 0.07],
    )
    # 35% of new customers have no loyalty tier (non-members)
    tier_choices = rng.choice(
        ["Explorer", "Silver", "Gold", None],
        size=n, p=[0.35, 0.18, 0.12, 0.35],
    )
    countries = rng.choice(
        ["Côte d'Ivoire", "France", "Ghana", "Nigeria", "Senegal", "Benin",
         "Burkina Faso", "Morocco", "Togo", "UAE", "USA", "Canada"],
        size=n, p=[0.30, 0.18, 0.10, 0.08, 0.08, 0.06, 0.05, 0.04, 0.04, 0.02, 0.03, 0.02],
    )
    cities_per_country = {
        "Côte d'Ivoire": ["Abidjan", "Bouaké", "Yamoussoukro", "Korhogo", "San-Pédro"],
        "France": ["Paris", "Lyon", "Marseille", "Bordeaux"],
        "Ghana": ["Accra", "Kumasi"],
        "Nigeria": ["Lagos", "Abuja"],
        "Senegal": ["Dakar"],
        "Benin": ["Cotonou"],
        "Burkina Faso": ["Ouagadougou"],
        "Morocco": ["Casablanca", "Rabat"],
        "Togo": ["Lomé"],
        "UAE": ["Dubai"],
        "USA": ["New York", "Atlanta"],
        "Canada": ["Montreal", "Toronto"],
    }
    cities = [rng.choice(cities_per_country[c]) for c in countries]

    channels = rng.choice(
        ["Web", "Mobile App", "Travel Agency", "Corporate Desk"],
        size=n, p=[0.34, 0.30, 0.22, 0.14],
    )
    genders = rng.choice(["M", "F"], size=n, p=[0.55, 0.45])

    # birth dates between 1955 and 2005
    birth_offsets = rng.integers(low=0, high=(date(2005, 12, 31) - date(1955, 1, 1)).days, size=n)
    birth_dates = [date(1955, 1, 1) + timedelta(days=int(o)) for o in birth_offsets]

    # signup dates spread between 2019 and 2024
    signup_offsets = rng.integers(low=0, high=(date(2024, 12, 31) - date(2019, 1, 1)).days, size=n)
    signup_dates = [date(2019, 1, 1) + timedelta(days=int(o)) for o in signup_offsets]

    new = pd.DataFrame({
        "customer_id": customer_ids,
        "first_name": rng.choice(first_names, size=n),
        "last_name": rng.choice(last_names, size=n),
        "gender": genders,
        "birth_date": pd.to_datetime(birth_dates),
        "country": countries,
        "city": cities,
        "customer_segment": segments,
        "loyalty_tier": tier_choices,
        "signup_date": pd.to_datetime(signup_dates),
        "preferred_channel": channels,
    })

    combined = pd.concat([starter, new], ignore_index=True)
    return combined


def main() -> None:
    print("=== Step 10: Fleet & Network ===")
    airports = build_airports()
    routes = build_routes()
    aircraft = build_aircraft()
    customers = build_customers()

    write_parquet(airports, ENRICHED_DIR / "airports.parquet")
    write_parquet(routes,   ENRICHED_DIR / "routes.parquet")
    write_parquet(aircraft, ENRICHED_DIR / "aircraft.parquet")
    write_parquet(customers, ENRICHED_DIR / "customers.parquet")


if __name__ == "__main__":
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    main()

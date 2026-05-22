"""
Validation checks for the enriched layer. Run last to catch silent regressions.
Each check prints PASS/FAIL with the actual value.
"""
from __future__ import annotations

import sys

import pandas as pd

from lib.config import ENRICHED_DIR


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(ENRICHED_DIR / f"{name}.parquet")


def check(label: str, condition: bool, value=None) -> bool:
    status = "PASS" if condition else "FAIL"
    extra = f"  ({value})" if value is not None else ""
    print(f"  [{status}] {label}{extra}")
    return condition


def main() -> int:
    print("=== Pipeline validation ===")
    failures = 0

    airports = load("airports")
    routes = load("routes")
    aircraft = load("aircraft")
    customers = load("customers")
    flights = load("flights")
    bookings = load("bookings")
    flight_costs = load("flight_costs")
    disruptions = load("disruptions")
    weather = load("weather_daily")
    loyalty = load("loyalty_activity")
    offers = load("ancillary_offers")
    cargo = load("cargo_shipments")
    competitors = load("competitors")
    feedback = load("customer_feedback")

    # --- Volumes
    print("\n--- Row counts ---")
    failures += not check("airports >= 13", len(airports) >= 13, len(airports))
    failures += not check("routes >= 16", len(routes) >= 16, len(routes))
    failures += not check("aircraft == 9", len(aircraft) == 9, len(aircraft))
    failures += not check("customers == 1000", len(customers) == 1000, len(customers))
    failures += not check("flights > 8000", len(flights) > 8000, len(flights))
    failures += not check("bookings > 500000", len(bookings) > 500000, len(bookings))
    failures += not check("flight_costs == flights", len(flight_costs) == len(flights),
                          f"{len(flight_costs)} vs {len(flights)}")
    failures += not check("feedback == 3000", len(feedback) == 3000, len(feedback))

    # --- Referential integrity
    print("\n--- Referential integrity ---")
    failures += not check("flights.route_id ⊂ routes.route_id",
        flights["route_id"].isin(routes["route_id"]).all())
    failures += not check("flights.tail_number ⊂ aircraft.tail_number",
        flights["tail_number"].isin(aircraft["tail_number"]).all())
    failures += not check("bookings.customer_id ⊂ customers.customer_id",
        bookings["customer_id"].isin(customers["customer_id"]).all())
    failures += not check("bookings.flight_id ⊂ flights.flight_id",
        bookings["flight_id"].isin(flights["flight_id"]).all())
    failures += not check("disruptions.flight_id ⊂ flights.flight_id",
        disruptions["flight_id"].isin(flights["flight_id"]).all())
    failures += not check("flight_costs.flight_id ⊂ flights.flight_id",
        flight_costs["flight_id"].isin(flights["flight_id"]).all())
    failures += not check("feedback.customer_id ⊂ customers.customer_id",
        feedback["customer_id"].isin(customers["customer_id"]).all())

    # --- Business-realism checks
    print("\n--- Business realism ---")
    pax_per_flight = bookings.groupby("flight_id").size()
    cap = flights.set_index("flight_id")["seat_capacity"]
    lf = (pax_per_flight / cap).dropna()
    failures += not check("Mean load factor between 0.60 and 0.90",
                          0.60 <= lf.mean() <= 0.90, f"{lf.mean():.3f}")
    failures += not check("No flight overbooked (LF <= 1.05)",
                          (lf <= 1.05).all(), f"max={lf.max():.3f}")

    cancel_rate = (flights["flight_status"] == "Cancelled").mean()
    failures += not check("Cancellation rate between 1% and 7%",
                          0.01 <= cancel_rate <= 0.07, f"{cancel_rate:.3f}")

    otp = (flights[flights["flight_status"] != "Cancelled"]["delay_min"] <= 15).mean()
    failures += not check("OTP15 between 55% and 80%",
                          0.55 <= otp <= 0.80, f"{otp:.3f}")

    attach = (bookings["ancillary_revenue_usd"] > 0).mean()
    failures += not check("Ancillary attach rate between 70% and 90%",
                          0.70 <= attach <= 0.90, f"{attach:.3f}")

    active_share = bookings["customer_id"].nunique() / len(customers)
    failures += not check("Active customers share between 70% and 90%",
                          0.70 <= active_share <= 0.90, f"{active_share:.3f}")

    # --- Unstructured layer realism
    print("\n--- Unstructured ---")
    lang_mix = feedback["language"].value_counts(normalize=True).to_dict()
    failures += not check("Feedback FR share between 55% and 75%",
                          0.55 <= lang_mix.get("fr", 0) <= 0.75, f"{lang_mix.get('fr', 0):.3f}")
    failures += not check("All feedback rows have raw_text",
                          feedback["raw_text"].notna().all())
    failures += not check("Feedback raw_text length > 30 chars on average",
                          feedback["raw_text"].str.len().mean() > 30,
                          f"{feedback['raw_text'].str.len().mean():.1f}")

    print(f"\n=== {failures} failure(s) ===")
    return 1 if failures > 0 else 0


if __name__ == "__main__":
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    sys.exit(main())

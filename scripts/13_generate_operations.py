"""
Step 13 - Operations layer:
  - flight_costs.parquet      (1 row per flight, decomposed cost model)
  - disruptions.parquet       (1 row per disruption event tied to a flight)
  - weather_daily.parquet     (1 row per airport-day, simple proxy)
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from lib.config import (
    DISRUPTION_TYPES,
    END_DATE,
    ENRICHED_DIR,
    START_DATE,
)
from lib.utils import block_hour_cost, daterange, get_rng, write_parquet


# Reason text templates per disruption type, mixing FR & EN (free text -> later NLP)
REASON_TEMPLATES = {
    "Weather": [
        "Orage tropical au-dessus d'Abidjan, attente de fenêtre météo.",
        "Heavy thunderstorm at ABJ delayed pushback and ATC slot.",
        "Visibilité réduite en approche, déroutement envisagé.",
        "Strong crosswind at destination, holding required.",
        "Pluies de mousson, ground operations suspended for 35 minutes.",
    ],
    "Technical": [
        "APU defect, replacement before departure required.",
        "Anomalie capteur pression cabine signalée par l'équipage.",
        "Maintenance unscheduled — engine vibration alert.",
        "Problème hydraulique mineur, troubleshooting effectué.",
        "Cabin door sensor fault, MEL applied.",
    ],
    "ATC": [
        "Slot ATC Paris CDG décalé de 45 minutes.",
        "Flow restriction over UTA airspace.",
        "Encombrement de l'espace aérien, attente au sol.",
    ],
    "Crew": [
        "Crew duty time exceeded, replacement crew assigned.",
        "Late arrival of inbound crew on previous rotation.",
        "Reposition d'équipage nécessaire suite à délai amont.",
    ],
    "Other": [
        "Bird strike inspection required on arrival.",
        "Passager indiscipliné, intervention du PNC.",
        "Bagage non identifié à bord, fouille de sécurité.",
        "Late baggage loading on connecting flight.",
    ],
}


def build_flight_costs(flights: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Decompose operating cost into fuel / crew / airport_fees / maintenance."""
    df = flights.copy()
    # Block hours from scheduled times
    block_min = (df["scheduled_arrival"] - df["scheduled_departure"]).dt.total_seconds() / 60.0
    block_min = block_min.fillna(0).clip(lower=20)
    block_hours = block_min / 60.0

    # Base block-hour cost per aircraft type (~total direct cost)
    base = df["aircraft_type"].map(block_hour_cost).astype(float)
    total_direct = base * block_hours

    # Decompose: 55% fuel / 22% crew / 13% airport / 10% maintenance
    fuel = total_direct * rng.normal(0.55, 0.05, size=len(df)).clip(0.40, 0.70)
    crew = total_direct * rng.normal(0.22, 0.03, size=len(df)).clip(0.15, 0.30)
    airport = total_direct * rng.normal(0.13, 0.02, size=len(df)).clip(0.08, 0.20)
    maintenance = total_direct - fuel - crew - airport

    # For cancelled flights, costs are recovered but irregular ops costs apply (~25% of normal)
    cancel_mask = (df["flight_status"] == "Cancelled").values
    fuel = np.where(cancel_mask, fuel * 0.05, fuel)
    crew = np.where(cancel_mask, crew * 0.30, crew)
    airport = np.where(cancel_mask, airport * 0.30, airport)
    maintenance = np.where(cancel_mask, maintenance * 0.10, maintenance)
    # IROPS cost penalty for cancellations: rebooking, hotels, compensation
    irops_penalty = np.where(cancel_mask, rng.gamma(5, 800, size=len(df)), 0)

    return pd.DataFrame({
        "flight_id": df["flight_id"].values,
        "block_hours": block_hours.round(3).values,
        "fuel_cost_usd": fuel.round(2),
        "crew_cost_usd": crew.round(2),
        "airport_fees_usd": airport.round(2),
        "maintenance_alloc_usd": maintenance.round(2),
        "irops_penalty_usd": irops_penalty.round(2),
        "total_operating_cost_usd": (fuel + crew + airport + maintenance + irops_penalty).round(2),
    })


def build_disruptions(flights: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Disruption events for cancelled or significantly delayed flights."""
    types = [t[0] for t in DISRUPTION_TYPES]
    probs = np.array([t[1] for t in DISRUPTION_TYPES])
    probs = probs / probs.sum()

    # Generate disruptions for:
    #   - all cancelled flights
    #   - all flights delayed > 60min
    #   - 30% of flights delayed between 16 and 60 min
    cancelled = flights[flights["flight_status"] == "Cancelled"]
    delayed_major = flights[(flights["flight_status"] == "Delayed") & (flights["delay_min"] > 60)]
    delayed_minor = flights[(flights["flight_status"] == "Delayed") &
                            (flights["delay_min"].between(16, 60))]
    delayed_minor = delayed_minor.sample(frac=0.3, random_state=42)

    affected = pd.concat([cancelled, delayed_major, delayed_minor]).drop_duplicates("flight_id")
    n = len(affected)
    if n == 0:
        return pd.DataFrame(columns=[
            "disruption_id", "flight_id", "disruption_type", "severity",
            "duration_min", "root_cause_text",
        ])

    # Disruption type with seasonal bias (more Weather in Jun-Aug)
    months = pd.to_datetime(affected["flight_date"]).dt.month.values
    rainy = np.isin(months, [6, 7, 8])
    type_assigned = np.where(
        rainy & (rng.random(n) < 0.55),
        "Weather",
        rng.choice(types, size=n, p=probs),
    )

    # Severity from delay
    delay = affected["delay_min"].fillna(180).values  # cancelled -> assume severe
    severity = np.where(delay > 180, "Severe", np.where(delay > 60, "Major", "Minor"))
    duration = delay.astype(int)

    # Root cause text
    root_cause = [rng.choice(REASON_TEMPLATES[t]) for t in type_assigned]

    return pd.DataFrame({
        "disruption_id": [f"DSR{i+1:06d}" for i in range(n)],
        "flight_id": affected["flight_id"].values,
        "disruption_type": type_assigned,
        "severity": severity,
        "duration_min": duration,
        "root_cause_text": root_cause,
    })


def build_weather(airports: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """1 row per (airport, day). Light proxy: precip mm, wind kph, severity flag."""
    rows = []
    for _, ap in airports.iterrows():
        code = ap["airport_code"]
        # Climate profile by region
        if ap["country"] in ("France",):
            base_precip = 2.0   # mm/day
            base_wind = 15.0
            rainy_months = [10, 11, 12, 1]
        elif ap["country"] in ("UAE",):
            base_precip = 0.2
            base_wind = 12.0
            rainy_months = []
        elif ap["country"] in ("Morocco",):
            base_precip = 1.0
            base_wind = 14.0
            rainy_months = [11, 12, 1, 2]
        else:  # West Africa - tropical
            base_precip = 3.5
            base_wind = 10.0
            rainy_months = [6, 7, 8, 9]

        for d in daterange(START_DATE, END_DATE):
            seasonal_factor = 3.0 if d.month in rainy_months else 1.0
            precip = float(np.clip(rng.gamma(1.2, base_precip * seasonal_factor / 2.0), 0, 200))
            wind = float(np.clip(rng.normal(base_wind, 5.0), 0, 60))
            severity = "High" if precip > 25 or wind > 40 else "Medium" if precip > 10 or wind > 30 else "Low"
            rows.append((code, d, round(precip, 1), round(wind, 1), severity))

    return pd.DataFrame(rows, columns=[
        "airport_code", "weather_date", "precipitation_mm", "wind_kph", "severity_flag"
    ])


def main() -> None:
    print("=== Step 13: Operations (cost, disruption, weather) ===")
    rng = get_rng(stream=13)

    flights = pd.read_parquet(ENRICHED_DIR / "flights.parquet")
    airports = pd.read_parquet(ENRICHED_DIR / "airports.parquet")

    print("  Computing flight costs...")
    costs = build_flight_costs(flights, rng)
    write_parquet(costs, ENRICHED_DIR / "flight_costs.parquet")

    print("  Computing disruptions...")
    disruptions = build_disruptions(flights, rng)
    write_parquet(disruptions, ENRICHED_DIR / "disruptions.parquet")

    print("  Computing weather proxy...")
    weather = build_weather(airports, rng)
    write_parquet(weather, ENRICHED_DIR / "weather_daily.parquet")

    print("\nSummary:")
    print(f"  Cost per flight (avg): {costs['total_operating_cost_usd'].mean():,.0f} USD")
    print(f"  Disruption types     : {disruptions['disruption_type'].value_counts().to_dict()}")
    print(f"  Severity mix         : {disruptions['severity'].value_counts().to_dict()}")
    print(f"  Weather rows         : {len(weather):,}")


if __name__ == "__main__":
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    main()

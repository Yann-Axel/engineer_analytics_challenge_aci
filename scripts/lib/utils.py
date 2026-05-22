"""Helpers used across the synthetic generation pipeline."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

import numpy as np
import pandas as pd

from .config import (
    AIRCRAFT_TYPE_BLOCK_HOUR_USD,
    SEASONAL_MULTIPLIER,
    SEED,
)


def get_rng(stream: int = 0) -> np.random.Generator:
    """Return a deterministic numpy RNG. Use distinct streams per generator
    so changes in one entity do not perturb another."""
    return np.random.default_rng(SEED + stream)


def daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def month_seasonality(d: date) -> float:
    return SEASONAL_MULTIPLIER[d.month]


def block_hour_cost(aircraft_type: str) -> float:
    return AIRCRAFT_TYPE_BLOCK_HOUR_USD.get(aircraft_type, 3_500)


def assign_aircraft_type(route_type: str, distance_km: int, rng: np.random.Generator) -> str:
    """Pick a compatible aircraft type for a route."""
    if route_type == "Domestic":
        return str(rng.choice(["A319", "A320"], p=[0.55, 0.45]))
    if route_type == "Regional":
        return str(rng.choice(["A319", "A320", "A320neo"], p=[0.30, 0.30, 0.40]))
    # International: long-haul uses A330neo, short-int'l uses A320neo
    if distance_km > 3500:
        return "A330-900neo"
    return "A320neo"


def write_parquet(df: pd.DataFrame, path) -> None:
    df.to_parquet(path, index=False)
    print(f"  -> {path.name:30s} ({len(df):>7,} rows, {df.shape[1]:>2} cols)")


def first_names_pool() -> list[str]:
    return [
        "Mariam", "Amadou", "Didier", "Fatou", "Yao", "Aminata", "Kouadio", "Aïcha",
        "Issouf", "Salif", "Aya", "Aminata", "Karim", "Awa", "Souleymane", "Affoué",
        "Pierre", "Marie", "Jean", "Sophie", "François", "Camille", "Lucas", "Manon",
        "John", "Sarah", "David", "Emma", "Michael", "Olivia", "Adama", "Mamadou",
        "Aïssatou", "Boubacar", "Ousmane", "Habiba", "Ibrahima", "Khadija", "Moussa", "Ramatoulaye",
    ]


def last_names_pool() -> list[str]:
    return [
        "Ouattara", "Koné", "Traoré", "Diallo", "Diabaté", "Coulibaly", "Bamba",
        "Touré", "Cissé", "Yao", "Konan", "Kouamé", "Bakayoko", "Camara",
        "Dupont", "Martin", "Bernard", "Dubois", "Thomas", "Robert",
        "Smith", "Johnson", "Williams", "Brown", "Jones",
        "Sow", "Ndiaye", "Diop", "Fall", "Sall", "Mbaye",
    ]

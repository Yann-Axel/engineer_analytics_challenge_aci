"""
Step 15 - CustomerFeedback (UNSTRUCTURED dataset, mandatory per the brief).

Design choices (senior):
  - We generate RAW free text only. Sentiment scoring, complaint categorisation,
    and route-issue theme extraction belong to the dbt staging NLP step (Part 2).
    This proves a real unstructured -> structured pipeline.
  - Texts are bilingual FR/EN (~65/30 + 5% code-switched) to reflect the Air CIV
    customer base, with placeholders {route} and {city} filled at runtime.
  - Probability of producing a feedback is boosted when the underlying flight was
    disrupted, when the customer is in Business class, or when loyalty tier is high
    (these cohorts complain or praise more).
  - Polarity correlates with disruption presence to enable realistic downstream
    sentiment analytics ("complaints driving low satisfaction on route X").

Output: data/enriched/customer_feedback.parquet
"""
from __future__ import annotations

import re
from datetime import timedelta

import numpy as np
import pandas as pd

from lib.config import (
    ENRICHED_DIR,
    FEEDBACK_CHANNEL_MIX,
    FEEDBACK_LANG_MIX,
    FEEDBACK_RATE_BASELINE,
    FEEDBACK_RATE_IF_BUSINESS,
    FEEDBACK_RATE_IF_DISRUPTED,
    TARGET_FEEDBACK_COUNT,
)
from lib.feedback_templates import (
    POLARITY_IF_CLEAN,
    POLARITY_IF_DISRUPTED,
    TEMPLATES,
    THEME_TRIGGERS,
)
from lib.utils import get_rng, write_parquet


CITY_LOOKUP = {
    "ABJ": "Abidjan", "BYK": "Bouaké", "MJC": "Man", "HGO": "Korhogo",
    "ACC": "Accra", "DKR": "Dakar", "LOS": "Lagos", "COO": "Cotonou",
    "OUA": "Ouagadougou", "CDG": "Paris", "CMN": "Casablanca", "LFW": "Lomé", "DXB": "Dubai",
}


def pick_template(theme: str, polarity: str, lang: str, rng: np.random.Generator) -> str | None:
    """Return a template string for the chosen (theme, polarity, lang) or fallback."""
    key = f"{lang}_{polarity}"
    if theme in TEMPLATES and key in TEMPLATES[theme]:
        choices = TEMPLATES[theme][key]
        return str(rng.choice(choices))
    # Fallback: try the other language
    other_lang = "en" if lang == "fr" else "fr"
    alt_key = f"{other_lang}_{polarity}"
    if theme in TEMPLATES and alt_key in TEMPLATES[theme]:
        return str(rng.choice(TEMPLATES[theme][alt_key]))
    # Fallback: general theme
    if "general" in TEMPLATES and key in TEMPLATES["general"]:
        return str(rng.choice(TEMPLATES["general"][key]))
    return None


def render(template: str, route_id: str, dest_code: str) -> str:
    """Fill {route} and {city} placeholders."""
    city = CITY_LOOKUP.get(dest_code, "Abidjan")
    return template.replace("{route}", route_id).replace("{city}", city)


def main() -> None:
    print("=== Step 15: CustomerFeedback (unstructured) ===")
    rng = get_rng(stream=15)

    bookings = pd.read_parquet(ENRICHED_DIR / "bookings.parquet")
    flights  = pd.read_parquet(ENRICHED_DIR / "flights.parquet")
    routes   = pd.read_parquet(ENRICHED_DIR / "routes.parquet")
    customers = pd.read_parquet(ENRICHED_DIR / "customers.parquet")
    disruptions = pd.read_parquet(ENRICHED_DIR / "disruptions.parquet")

    # Annotate bookings with flight info, disruption flag, fare class, segment, tier
    disrupted_flights = set(disruptions["flight_id"].unique())
    flight_to_route = flights.set_index("flight_id")["route_id"].to_dict()
    route_to_dest = routes.set_index("route_id")["destination_airport_code"].to_dict()

    flown = bookings[bookings["booking_status"] == "Flown"].copy()
    flown["has_disruption"] = flown["flight_id"].isin(disrupted_flights)
    flown["route_id"] = flown["flight_id"].map(flight_to_route)
    flown["dest_code"] = flown["route_id"].map(route_to_dest)
    seg_map = customers.set_index("customer_id")["customer_segment"].to_dict()
    tier_map = customers.set_index("customer_id")["loyalty_tier"].to_dict()
    flown["segment"] = flown["customer_id"].map(seg_map)
    flown["loyalty_tier"] = flown["customer_id"].map(tier_map)

    # Compute per-booking probability of feedback
    p = np.full(len(flown), FEEDBACK_RATE_BASELINE)
    p = np.where(flown["has_disruption"].values, FEEDBACK_RATE_IF_DISRUPTED, p)
    p = np.where(flown["fare_class"].values == "Business",
                 np.maximum(p, FEEDBACK_RATE_IF_BUSINESS), p)

    selected_mask = rng.random(len(flown)) < p
    candidates = flown[selected_mask].copy()
    # Sample down to TARGET_FEEDBACK_COUNT
    if len(candidates) > TARGET_FEEDBACK_COUNT:
        candidates = candidates.sample(TARGET_FEEDBACK_COUNT, random_state=15)
    n = len(candidates)
    print(f"  Generating {n:,} feedback rows...")

    # For each candidate, pick a theme weighted by triggers, then a polarity, then a template
    themes_list = list(TEMPLATES.keys())
    rows = []
    fb_id = 1
    cand_arr = candidates.reset_index(drop=True)
    for i in range(n):
        row = cand_arr.iloc[i]
        # Build theme weights for this booking
        weights = np.ones(len(themes_list))
        for j, theme in enumerate(themes_list):
            trig = THEME_TRIGGERS[theme]
            boost = trig.get("boost", 1.0)
            applies = True
            if "disruption_types" in trig and not row["has_disruption"]:
                applies = False
            if "fare_classes" in trig and row["fare_class"] not in trig["fare_classes"]:
                applies = False
            if "tiers" in trig and (pd.isna(row.get("loyalty_tier")) or
                                    row["loyalty_tier"] not in trig["tiers"]):
                applies = False
            if applies:
                weights[j] *= boost
        weights /= weights.sum()
        theme = str(rng.choice(themes_list, p=weights))

        # Polarity
        pol_dist = POLARITY_IF_DISRUPTED if row["has_disruption"] else POLARITY_IF_CLEAN
        polarity = str(rng.choice(list(pol_dist.keys()), p=list(pol_dist.values())))

        # Language
        lang = str(rng.choice(list(FEEDBACK_LANG_MIX.keys()),
                              p=list(FEEDBACK_LANG_MIX.values())))
        if lang == "mixed":
            # 50/50 of the time render in fr then append a short en clause
            lang = "fr"
            mixed = True
        else:
            mixed = False

        template = pick_template(theme, polarity, lang, rng)
        if template is None:
            template = pick_template("general", polarity, lang, rng)
            if template is None:
                continue
        text = render(template, row["route_id"], row["dest_code"])
        if mixed:
            extra = pick_template("general", polarity, "en", rng)
            if extra:
                text = text + " " + render(extra, row["route_id"], row["dest_code"])

        # Channel & date (within 0-30 days after booking)
        channel = str(rng.choice(list(FEEDBACK_CHANNEL_MIX.keys()),
                                 p=list(FEEDBACK_CHANNEL_MIX.values())))
        days_offset = int(rng.integers(0, 30))
        feedback_date = pd.to_datetime(row["booking_date"]) + timedelta(days=days_offset)

        rows.append({
            "feedback_id": f"FB{fb_id:06d}",
            "customer_id": row["customer_id"],
            "booking_id": row["booking_id"],
            "flight_id": row["flight_id"],
            "route_id": row["route_id"],
            "feedback_channel": channel,
            "feedback_date": feedback_date,
            "language": lang if not mixed else "fr+en",
            "raw_text": text,
        })
        fb_id += 1

    df = pd.DataFrame(rows)
    write_parquet(df, ENRICHED_DIR / "customer_feedback.parquet")

    print("\nSummary:")
    print(f"  Total feedbacks   : {len(df):,}")
    print(f"  Language mix      : {df['language'].value_counts(normalize=True).round(3).to_dict()}")
    print(f"  Channel mix       : {df['feedback_channel'].value_counts(normalize=True).round(3).to_dict()}")
    # quick raw heuristic: count negative words
    def quick_polarity(t: str) -> str:
        neg_words = ["perdu", "retardé", "désagréable", "cassé", "delay", "lost", "rude", "poor", "bad", "nightmare", "déçu", "inacceptable"]
        pos_words = ["bravo", "parfait", "excellent", "outstanding", "merci", "great", "smooth", "fantastique"]
        tl = t.lower()
        n = sum(w in tl for w in neg_words)
        p = sum(w in tl for w in pos_words)
        if n > p: return "neg"
        if p > n: return "pos"
        return "neu"
    print(f"  Heuristic polarity: {df['raw_text'].map(quick_polarity).value_counts(normalize=True).round(3).to_dict()}")
    print(f"  Sample feedback   :")
    for _, r in df.sample(3, random_state=1).iterrows():
        print(f"    [{r['language']:5s}] [{r['route_id']}] {r['raw_text']}")


if __name__ == "__main__":
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    main()

"""
Global configuration for synthetic data generation.
All knobs in one place so reviewers can audit reproducibility and scale.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

# ---------- Paths ----------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ENRICHED_DIR = PROJECT_ROOT / "data" / "enriched"
ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Reproducibility ----------
SEED = 42

# ---------- Time window ----------
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)

# ---------- Fleet (Aircraft) ----------
# Cabin configuration is informed by typical Air Côte d'Ivoire-class operators.
FLEET = [
    # (tail_number, type, manufacturer, year, seats_J, seats_W, seats_Y, fleet_status)
    ("TU-TSA", "A319",        "Airbus", 2009, 12, 12,  98, "Owned"),
    ("TU-TSB", "A319",        "Airbus", 2011, 12, 12,  98, "Owned"),
    ("TU-TSC", "A320",        "Airbus", 2015, 12, 18, 120, "Leased"),
    ("TU-TSD", "A320",        "Airbus", 2017, 12, 18, 120, "Owned"),
    ("TU-TSE", "A320neo",     "Airbus", 2020, 12, 18, 120, "Owned"),
    ("TU-TSF", "A320neo",     "Airbus", 2021, 12, 18, 120, "Owned"),
    ("TU-TSG", "A320neo",     "Airbus", 2022, 12, 18, 120, "Leased"),
    ("TU-TSH", "A330-900neo", "Airbus", 2024, 28, 21, 232, "Owned"),
    ("TU-TSI", "A330-900neo", "Airbus", 2025, 28, 21, 232, "Owned"),
]

# Aircraft type to seat capacity (used to override the starter capacities)
AIRCRAFT_TYPE_CAPACITY = {
    "A319": 122,
    "A320": 150,
    "A320neo": 150,
    "A330-900neo": 281,
}

# Block-hour direct cost in USD per aircraft type (industry-aligned synthetic values).
# Covers fuel + crew + maintenance + airport fees split downstream.
AIRCRAFT_TYPE_BLOCK_HOUR_USD = {
    "A319":        3_400,
    "A320":        3_600,
    "A320neo":     2_900,
    "A330-900neo": 7_200,
}

# ---------- Routes additions (candidates for growth decision) ----------
NEW_AIRPORTS = [
    # code, name, city, country, timezone, lat, lon
    ("CMN", "Mohammed V International Airport", "Casablanca", "Morocco", "Africa/Casablanca", 33.37, -7.59),
    ("LFW", "Lomé-Tokoin Airport",              "Lomé",       "Togo",    "Africa/Lome",       6.17,   1.25),
    ("DXB", "Dubai International Airport",      "Dubai",      "UAE",     "Asia/Dubai",       25.25,  55.36),
]

# Each new route is annotated as "candidate" (potential growth) — not yet operated heavily.
NEW_ROUTES = [
    # route_id, origin, dest, type, distance_km, block_time_min, status
    ("R013", "CDG", "ABJ", "International", 4880, 390, "operated"),
    ("R014", "ABJ", "CMN", "International", 3700, 320, "candidate"),
    ("R015", "ABJ", "LFW", "Regional",       310,  50, "candidate"),
    ("R016", "ABJ", "DXB", "International", 6900, 510, "candidate"),
]

# ---------- Customer base scaling ----------
TOTAL_CUSTOMERS = 1_000  # 300 starter + 700 new
NEW_CUSTOMERS_COUNT = TOTAL_CUSTOMERS - 300

# Activity distribution buckets — share of customers and their booking range over 24 months.
CUSTOMER_ACTIVITY_BUCKETS = [
    ("inactive",     0.20, (0, 0)),
    ("occasional",   0.50, (1, 5)),
    ("regular",      0.25, (6, 20)),
    ("power_user",   0.05, (21, 60)),
]

# ---------- Flight schedule ----------
# Weekly frequency target per route (mean) — multiplied by seasonal factor.
ROUTE_WEEKLY_FREQUENCY = {
    "R001": 5,  "R002": 5,  "R003": 4,                     # domestic
    "R004": 7,  "R005": 6,  "R006": 7,  "R007": 5, "R008": 5,  # regional outbound
    "R009": 7,                                              # ABJ-CDG strategic
    "R010": 7,  "R011": 6,  "R012": 7,                     # regional return
    "R013": 7,                                              # CDG-ABJ return
    "R014": 0.5,  # candidate routes get very low (or simulation only)
    "R015": 0.5,
    "R016": 0,
}

# Seasonal multiplier per month (1 = baseline)
SEASONAL_MULTIPLIER = {
    1: 1.05, 2: 0.95, 3: 1.00, 4: 1.00, 5: 0.95, 6: 1.10,
    7: 1.25, 8: 1.25, 9: 0.90, 10: 1.00, 11: 1.05, 12: 1.20,
}

# Probability of cancellation per route_type
CANCELLATION_RATE = {"Domestic": 0.03, "Regional": 0.04, "International": 0.025}

# Aircraft assignment rule per route_type
ROUTE_TYPE_AIRCRAFT = {
    "Domestic":      ["A319", "A320"],
    "Regional":      ["A319", "A320", "A320neo"],
    "International": ["A320neo", "A330-900neo"],  # CDG, CMN, DXB
}

# ---------- Load factor targets ----------
# Realistic average load factor per route_type
LOAD_FACTOR_TARGET = {
    "Domestic":      0.72,
    "Regional":      0.78,
    "International": 0.82,
}

# ---------- Pricing ----------
# Base ticket price (USD) per route_type, scaled by fare class.
BASE_PRICE_USD = {"Domestic": 90, "Regional": 230, "International": 620}
FARE_CLASS_PRICE_MULT = {"Economy": 1.0, "Premium Economy": 1.8, "Business": 3.2}
FARE_CLASS_MIX = {"Economy": 0.78, "Premium Economy": 0.12, "Business": 0.10}
FARE_FAMILY_MIX = {"Basic": 0.35, "Standard": 0.45, "Flex": 0.20}
FARE_FAMILY_PRICE_MULT = {"Basic": 0.85, "Standard": 1.0, "Flex": 1.25}

# ---------- Channels ----------
BOOKING_CHANNEL_MIX = {"Web": 0.34, "Mobile App": 0.27, "Travel Agency": 0.24, "Corporate Desk": 0.15}

# ---------- Ancillary ----------
ANCILLARY_TYPES = [
    # type, base price, presentation prob, baseline acceptance
    ("seat_selection",   12, 0.95, 0.45),
    ("extra_bag",        25, 0.90, 0.30),
    ("upgrade_W",        80, 0.40, 0.10),  # Economy -> Premium Eco
    ("upgrade_J",       180, 0.20, 0.05),  # Premium Eco -> Business
    ("lounge_access",    35, 0.30, 0.15),
    ("priority_board",   10, 0.50, 0.20),
]

# ---------- Disruption ----------
DISRUPTION_TYPES = [
    ("Weather", 0.35),
    ("Technical", 0.25),
    ("ATC",      0.15),
    ("Crew",     0.15),
    ("Other",    0.10),
]

# ---------- Feedback ----------
TARGET_FEEDBACK_COUNT = 3_000
FEEDBACK_LANG_MIX = {"fr": 0.65, "en": 0.30, "mixed": 0.05}
FEEDBACK_CHANNEL_MIX = {"support_ticket": 0.50, "review": 0.35, "social_post": 0.15}

# Probability that a flown booking generates a feedback (driven up by disruption / down by perfect flight)
FEEDBACK_RATE_BASELINE     = 0.018
FEEDBACK_RATE_IF_DISRUPTED = 0.085
FEEDBACK_RATE_IF_BUSINESS  = 0.025

# ---------- Loyalty ----------
LOYALTY_POINTS_PER_KM = {"Explorer": 1.0, "Silver": 1.25, "Gold": 1.5}
LOYALTY_REDEEM_PROB_PER_BOOKING = 0.02  # 2% of eligible bookings have a redemption event

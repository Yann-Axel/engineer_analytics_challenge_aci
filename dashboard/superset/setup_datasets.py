"""
Provision the Air Côte d'Ivoire DuckDB database and its 19 datasets in Superset
via the REST API. Idempotent: re-running skips what already exists (the API
returns a 422 "already exists" which we treat as success).

Why this script instead of clicking in the UI:
  * Reproducibility — a reviewer runs `python setup_datasets.py` and gets the
    same Superset state regardless of build order.
  * Versioning — the list of exposed tables lives in code, in Git.
  * Audit — what the dashboard exposes is reviewable in a single file.

Usage (assuming Superset is up via `docker compose up -d`):

    .venv/Scripts/python dashboard/superset/setup_datasets.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import requests

SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088")
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
DB_DISPLAY_NAME = "airline-duckdb"
DUCKDB_URI = "duckdb:////app/data/airline.duckdb?access_mode=read_only"


@dataclass(frozen=True)
class DatasetSpec:
    schema: str
    table: str
    description: str


DATASETS: list[DatasetSpec] = [
    # Dimensions (6)
    DatasetSpec("main_marts", "dim_date",              "Rich daily date dimension"),
    DatasetSpec("main_marts", "dim_airport",           "Airport reference"),
    DatasetSpec("main_marts", "dim_route",             "Routes with distance band and strategic flag"),
    DatasetSpec("main_marts", "dim_aircraft",          "Fleet reference"),
    DatasetSpec("main_marts", "dim_fare",              "Fare class × family"),
    DatasetSpec("main_marts", "dim_customer_current",  "Customer point-in-time view"),
    # Facts (5)
    DatasetSpec("main_marts", "fct_flights",           "One row per flight"),
    DatasetSpec("main_marts", "fct_bookings",          "One row per booking (SCD2-joined)"),
    DatasetSpec("main_marts", "fct_customer_feedback", "Feedback enriched with NLP fields"),
    DatasetSpec("main_marts", "fct_ancillary_offers",  "Ancillary offer presentation + acceptance"),
    DatasetSpec("main_marts", "fct_loyalty_events",    "Loyalty earn / redeem events"),
    # Intermediate (3)
    DatasetSpec("main_intermediate", "int_route_monthly_perf",     "Pre-aggregated route × month KPIs"),
    DatasetSpec("main_intermediate", "int_route_complaint_themes", "Route × month NLP themes + sentiment"),
    DatasetSpec("main_intermediate", "int_customer_lifetime",      "LTV + churn risk per customer"),
    # Ontology (5)
    DatasetSpec("main_ontology", "ont_high_value_at_risk_customer",      "High-value at-risk customers"),
    DatasetSpec("main_ontology", "ont_strategic_underperforming_route",  "Strategic underperforming routes"),
    DatasetSpec("main_ontology", "ont_premium_upsell_candidate",         "Premium upsell candidates"),
    DatasetSpec("main_ontology", "ont_loyal_detractor",                  "Gold-tier detractors (early-warning)"),
    DatasetSpec("main_ontology", "ont_irops_heavy_route",                "IROPS-heavy routes (ops fragility)"),
]


class SupersetClient:
    """Thin REST client. Idempotency via 422 'already exists' detection
    rather than pre-listing — Superset 4.1's list endpoint has a default
    filter that hides API-created resources unless explicitly owned."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.access_token: str | None = None
        self.csrf_token: str | None = None

    def _hdr(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "X-CSRFToken": self.csrf_token or "",
            "Content-Type": "application/json",
            "Referer": self.base_url,
        }

    def login(self) -> None:
        resp = self.session.post(
            f"{self.base_url}/api/v1/security/login",
            json={
                "username": self.username,
                "password": self.password,
                "provider": "db",
                "refresh": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        self.access_token = resp.json()["access_token"]
        resp = self.session.get(
            f"{self.base_url}/api/v1/security/csrf_token/",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )
        resp.raise_for_status()
        self.csrf_token = resp.json()["result"]
        print("  ✓ Authenticated as admin")

    def create_database(self, display_name: str, sqlalchemy_uri: str) -> tuple[str, int | None]:
        """Returns (status, id). status ∈ {'created', 'exists'}. id may be None if exists."""
        payload = {
            "database_name": display_name,
            "sqlalchemy_uri": sqlalchemy_uri,
            "expose_in_sqllab": True,
            "allow_run_async": False,
            "allow_dml": False,
        }
        resp = self.session.post(
            f"{self.base_url}/api/v1/database/",
            headers=self._hdr(),
            json=payload,
            timeout=60,
        )
        if resp.status_code == 422 and "already exists" in resp.text:
            return ("exists", None)
        resp.raise_for_status()
        return ("created", resp.json()["id"])

    def create_dataset(self, database_id: int, schema: str, table: str) -> tuple[str, int | None]:
        payload = {"database": database_id, "schema": schema, "table_name": table}
        resp = self.session.post(
            f"{self.base_url}/api/v1/dataset/",
            headers=self._hdr(),
            json=payload,
            timeout=60,
        )
        if resp.status_code == 422 and ("already exists" in resp.text or "duplicate" in resp.text.lower()):
            return ("exists", None)
        if resp.status_code >= 400:
            print(f"  ! Dataset create failed for {schema}.{table}: {resp.status_code} {resp.text[:200]}")
            resp.raise_for_status()
        return ("created", resp.json()["id"])


def resolve_database_id(client: SupersetClient, display_name: str) -> int:
    """If the API list shows the DB, return its id. Otherwise default to 1
    (first DB created in a fresh install). This is OK for our single-DB demo."""
    resp = client.session.get(
        f"{client.base_url}/api/v1/database/",
        headers={"Authorization": f"Bearer {client.access_token}"},
        params={"page_size": 100},
        timeout=30,
    )
    if resp.status_code == 200:
        for db in resp.json().get("result", []):
            if db.get("database_name") == display_name:
                return db["id"]
    # Fallback: probe id=1, the first created database id in a fresh metastore.
    return 1


def main() -> int:
    print(f">>> Connecting to Superset at {SUPERSET_URL}")
    client = SupersetClient(SUPERSET_URL, ADMIN_USER, ADMIN_PASS)
    try:
        client.login()
    except requests.exceptions.RequestException as e:
        print(f"  ! Cannot reach Superset. Is `docker compose up -d` running? Error: {e}")
        return 1

    print(f"\n>>> Database '{DB_DISPLAY_NAME}'")
    status, db_id = client.create_database(DB_DISPLAY_NAME, DUCKDB_URI)
    if status == "created":
        print(f"  + Created (id={db_id})")
    else:
        db_id = resolve_database_id(client, DB_DISPLAY_NAME)
        print(f"  ✓ Already exists (resolved id={db_id})")

    print(f"\n>>> Datasets ({len(DATASETS)} total)")
    created = 0
    existing = 0
    failed = 0
    for spec in DATASETS:
        full = f"{spec.schema}.{spec.table}"
        try:
            status, ds_id = client.create_dataset(db_id, spec.schema, spec.table)
            if status == "created":
                print(f"  + {full:<60s} (id={ds_id}, created)")
                created += 1
            else:
                print(f"  ✓ {full:<60s} (already exists, skipped)")
                existing += 1
        except requests.exceptions.HTTPError as e:
            print(f"  ✗ {full:<60s} FAILED: {e}")
            failed += 1

    print(f"\n>>> Summary")
    print(f"    Created : {created}")
    print(f"    Existing: {existing}")
    print(f"    Failed  : {failed}")
    print(f"    Total   : {len(DATASETS)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

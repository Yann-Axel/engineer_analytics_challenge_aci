"""
Provision the 5 dashboards of the Executive Growth Allocation app.

Each dashboard groups its page's charts with a consistent grid layout and a
shared time-range native filter. Idempotent: re-running skips existing
dashboards (detected by slug via the metastore).

Page → Dashboard mapping:
  0. Executive Overview     (slug: executive-overview)
  1. Network & Profitability (slug: network-profitability)
  2. Customer & Retention   (slug: customer-retention)
  3. Upsell & Cross-sell    (slug: upsell-crosssell)
  4. Decision Layer         (slug: decision-layer)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass

import requests

SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088")
# When this script runs *inside* a container that mounts the Superset
# `superset_home` volume, we can open the SQLite metastore directly.
# Otherwise (host mode) we fall back to `docker exec airline-superset`.
SUPERSET_DB_PATH = os.environ.get("SUPERSET_DB_PATH")  # e.g. /app/superset_home/superset.db


def _run_metastore_query(sql: str) -> list[tuple]:
    """Run a SELECT against Superset's SQLite metastore. Returns list of rows."""
    if SUPERSET_DB_PATH:
        import sqlite3
        con = sqlite3.connect(SUPERSET_DB_PATH)
        try:
            return list(con.execute(sql))
        finally:
            con.close()
    result = subprocess.run(
        ["docker", "exec", "airline-superset", "python", "-c",
         f"import sqlite3, json; "
         f"con=sqlite3.connect('/app/superset_home/superset.db'); "
         f"print(json.dumps([list(r) for r in con.execute({sql!r})]))"],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return [tuple(r) for r in json.loads(result.stdout.strip().splitlines()[-1])]
ADMIN_USER = "admin"
ADMIN_PASS = "admin"


@dataclass
class DashboardSpec:
    title: str
    slug: str
    chart_names: list[str]
    # layout config — either "kpi_row" (small Big Numbers) or "two_col"
    # or "one_col" (full-width tables). Per-row override possible.
    rows_layout: list[tuple[str, list[str]]]  # [(layout_kind, [chart_names])]


# ─────────────────────────────────────────────────────────────────────────────
# Dashboards catalogue (refers to chart slice_names created by setup_charts.py)
# ─────────────────────────────────────────────────────────────────────────────

DASHBOARDS: list[DashboardSpec] = [
    DashboardSpec(
        title="1 · Network & Profitability",
        slug="network-profitability",
        chart_names=[
            "Net · Revenue by Route", "Net · Route Opportunity Matrix",
            "Net · OTP15 & Cancellation Trends",
            "Net · Yield (RASK) by Route Type",
            "Net · Disruptions by Type",
        ],
        rows_layout=[
            ("one_col", ["Net · Route Opportunity Matrix"]),  # hero chart full-width
            ("two_col", ["Net · Revenue by Route", "Net · Disruptions by Type"]),
            ("two_col", ["Net · OTP15 & Cancellation Trends", "Net · Yield (RASK) by Route Type"]),
        ],
    ),
    DashboardSpec(
        title="2 · Customer & Retention",
        slug="customer-retention",
        chart_names=[
            "Cust · Segment & Loyalty Distribution",
            "Cust · High-Value At-Risk Customers (top 20)",
            "Cust · Complaint Themes by Route",
            "Cust · Sentiment Trend (monthly)",
            "Cust · Repeat Booking Rate",
        ],
        rows_layout=[
            ("two_col", ["Cust · Segment & Loyalty Distribution", "Cust · Repeat Booking Rate"]),
            ("one_col", ["Cust · High-Value At-Risk Customers (top 20)"]),
            ("two_col", ["Cust · Complaint Themes by Route", "Cust · Sentiment Trend (monthly)"]),
        ],
    ),
    DashboardSpec(
        title="3 · Upsell & Cross-sell",
        slug="upsell-crosssell",
        chart_names=[
            "Up · Upgrade Conversion by Tier",
            "Up · Ancillary Attach Rate by Segment",
            "Up · Revenue per Passenger by Fare Class",
            "Up · Premium Upsell Candidates (top 20)",
        ],
        rows_layout=[
            ("two_col", ["Up · Upgrade Conversion by Tier", "Up · Ancillary Attach Rate by Segment"]),
            ("one_col", ["Up · Revenue per Passenger by Fare Class"]),
            ("one_col", ["Up · Premium Upsell Candidates (top 20)"]),
        ],
    ),
    DashboardSpec(
        title="4 · Decision Layer",
        slug="decision-layer",
        chart_names=[
            "Dec · Routes to GROW (top profitable + busy)",
            "Dec · Routes to DEFEND (operational fragility)",
            "Dec · Customers to RETAIN (high-value at risk)",
            "Dec · Offers to PRIORITIZE (premium upsell)",
        ],
        rows_layout=[
            ("one_col", ["Dec · Routes to GROW (top profitable + busy)"]),
            ("one_col", ["Dec · Routes to DEFEND (operational fragility)"]),
            ("one_col", ["Dec · Customers to RETAIN (high-value at risk)"]),
            ("one_col", ["Dec · Offers to PRIORITIZE (premium upsell)"]),
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Position JSON builder (Superset's 12-column grid layout)
# ─────────────────────────────────────────────────────────────────────────────

LAYOUT_CONFIGS = {
    # (chart_width_in_12_grid, chart_height_in_grid_units)
    "kpi_row": (3, 30),   # 4 charts per row, short height
    "two_col": (6, 50),   # 2 charts per row, normal height
    "one_col": (12, 50),  # 1 chart per row, full width
}


def build_position_json(rows_layout: list[tuple[str, list[str]]],
                        name_to_chart_id: dict[str, int]) -> dict:
    """Build Superset's position_json describing the dashboard layout."""
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "parents": ["ROOT_ID"], "children": []},
    }

    for kind, chart_names in rows_layout:
        chart_width, chart_height = LAYOUT_CONFIGS[kind]
        row_id = f"ROW-{uuid.uuid4().hex[:8]}"
        row_children = []

        for name in chart_names:
            chart_id = name_to_chart_id.get(name)
            if chart_id is None:
                print(f"    ! Chart not found in metastore: {name}")
                continue
            chart_block_id = f"CHART-{uuid.uuid4().hex[:8]}"
            position[chart_block_id] = {
                "type": "CHART",
                "id": chart_block_id,
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {
                    "chartId": chart_id,
                    "width": chart_width,
                    "height": chart_height,
                    "sliceName": name,
                },
                "children": [],
            }
            row_children.append(chart_block_id)

        position[row_id] = {
            "type": "ROW",
            "id": row_id,
            "parents": ["ROOT_ID", "GRID_ID"],
            "children": row_children,
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        position["GRID_ID"]["children"].append(row_id)

    return position


# ─────────────────────────────────────────────────────────────────────────────
# Native filter: shared time-range filter for all dashboards
# ─────────────────────────────────────────────────────────────────────────────

def build_native_filter() -> dict:
    """One shared time-range filter applied to all dashboards.
    The full schema (scope.excluded, controlValues, defaultDataMask…) is
    required by Superset 4.1.2's front-end — any missing key crashes the
    React tree with "Cannot read properties of undefined (reading 'excluded')".
    """
    return {
        "native_filter_configuration": [
            {
                "id": "NATIVE_FILTER-time-range",
                "name": "Date Range",
                "filterType": "filter_time",
                "targets": [{}],
                "controlValues": {
                    "enableEmptyFilter": False,
                    "defaultToFirstItem": False,
                    "multiple": True,
                    "searchAllOptions": False,
                    "inverseSelection": False,
                },
                "defaultDataMask": {
                    "filterState": {"value": "No filter"},
                    "extraFormData": {},
                },
                "scope": {
                    "rootPath": ["ROOT_ID"],
                    "excluded": [],
                },
                "type": "NATIVE_FILTER",
                "description": "Limit all charts to a date range.",
                "chartsInScope": [],
            }
        ],
        "global_chart_configuration": {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Metastore lookups
# ─────────────────────────────────────────────────────────────────────────────

def fetch_chart_name_to_id() -> dict[str, int]:
    """Return {slice_name: id} from the Superset metastore."""
    try:
        rows = _run_metastore_query("SELECT id, slice_name FROM slices")
        return {name: id_ for (id_, name) in rows}
    except Exception as e:
        print(f"  ! Cannot read chart names from metastore: {e}")
        return {}


def fetch_existing_dashboard_slugs() -> set[str]:
    try:
        rows = _run_metastore_query(
            "SELECT slug FROM dashboards WHERE slug IS NOT NULL"
        )
        return {r[0] for r in rows}
    except Exception:
        return set()


# ─────────────────────────────────────────────────────────────────────────────
# Superset client
# ─────────────────────────────────────────────────────────────────────────────

class SupersetClient:
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
        import re
        r = self.session.get(f"{self.base_url}/login/", timeout=30)
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
        form_csrf = m.group(1) if m else ""
        self.session.post(
            f"{self.base_url}/login/",
            data={"username": self.username, "password": self.password,
                  "csrf_token": form_csrf},
            allow_redirects=True, timeout=30,
        )
        r = self.session.post(
            f"{self.base_url}/api/v1/security/login",
            json={"username": self.username, "password": self.password,
                  "provider": "db", "refresh": True},
            timeout=30,
        )
        r.raise_for_status()
        self.access_token = r.json()["access_token"]
        r = self.session.get(
            f"{self.base_url}/api/v1/security/csrf_token/",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )
        r.raise_for_status()
        self.csrf_token = r.json()["result"]
        print("  ✓ Authenticated as admin (JWT + session cookie)")

    def create_dashboard(self, title: str, slug: str) -> int | None:
        payload = {"dashboard_title": title, "slug": slug, "published": True}
        r = self.session.post(
            f"{self.base_url}/api/v1/dashboard/",
            headers=self._hdr(),
            json=payload,
            timeout=60,
        )
        if r.status_code >= 400:
            print(f"    ! create_dashboard failed: {r.status_code} {r.text[:200]}")
            return None
        return r.json().get("id")

    def update_dashboard(self, dashboard_id: int, position_json: dict,
                         json_metadata: dict) -> bool:
        payload = {
            "position_json": json.dumps(position_json),
            "json_metadata": json.dumps(json_metadata),
        }
        r = self.session.put(
            f"{self.base_url}/api/v1/dashboard/{dashboard_id}",
            headers=self._hdr(),
            json=payload,
            timeout=60,
        )
        if r.status_code >= 400:
            print(f"    ! update_dashboard failed: {r.status_code} {r.text[:200]}")
            return False
        return True

    def attach_chart_to_dashboard(self, chart_id: int, dashboard_id: int) -> bool:
        """Associate a chart with a dashboard (many-to-many).
        position_json alone is not enough — Superset also tracks the
        relation via the dashboard_slices table, populated when we PUT
        the chart's `dashboards` field. Idempotent: setting the same
        dashboard list twice is a no-op."""
        # Read current dashboards of the chart
        r = self.session.get(
            f"{self.base_url}/api/v1/chart/{chart_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )
        current_ids: list[int] = []
        if r.status_code == 200:
            current_ids = [d["id"] for d in r.json()["result"].get("dashboards", [])]
        if dashboard_id in current_ids:
            return True
        new_ids = sorted(set(current_ids + [dashboard_id]))
        r = self.session.put(
            f"{self.base_url}/api/v1/chart/{chart_id}",
            headers=self._hdr(),
            json={"dashboards": new_ids},
            timeout=60,
        )
        if r.status_code >= 400:
            print(f"      ! attach_chart_to_dashboard {chart_id}→{dashboard_id} failed: "
                  f"{r.status_code} {r.text[:150]}")
            return False
        return True


def get_dashboard_id_by_slug(slug: str) -> int | None:
    try:
        # slug is dev-controlled (defined in this file), safe to inline
        rows = _run_metastore_query(
            f"SELECT id FROM dashboards WHERE slug='{slug}'"
        )
        return int(rows[0][0]) if rows else None
    except Exception:
        return None


def main() -> int:
    print(f">>> Connecting to Superset at {SUPERSET_URL}")
    client = SupersetClient(SUPERSET_URL, ADMIN_USER, ADMIN_PASS)
    client.login()

    print(f"\n>>> Reading chart catalogue from metastore")
    name_to_id = fetch_chart_name_to_id()
    print(f"  ✓ Found {len(name_to_id)} charts")

    existing_slugs = fetch_existing_dashboard_slugs()
    if existing_slugs:
        print(f"  ✓ Existing dashboard slugs in metastore: {sorted(existing_slugs)}")

    print(f"\n>>> Dashboards ({len(DASHBOARDS)} total)")
    created = 0
    updated = 0
    failed = 0
    for spec in DASHBOARDS:
        if spec.slug in existing_slugs:
            dash_id = get_dashboard_id_by_slug(spec.slug)
            print(f"  ✓ {spec.title:<35s} already exists (id={dash_id}, updating layout)")
        else:
            dash_id = client.create_dashboard(spec.title, spec.slug)
            if dash_id is None:
                print(f"  ✗ {spec.title:<35s} CREATE FAILED")
                failed += 1
                continue
            print(f"  + {spec.title:<35s} created (id={dash_id})")
            created += 1

        # 1) Attach each chart to the dashboard (many-to-many relation).
        attached = 0
        chart_ids = [name_to_id[name] for _, names in spec.rows_layout
                     for name in names if name in name_to_id]
        for chart_id in chart_ids:
            if client.attach_chart_to_dashboard(chart_id, dash_id):
                attached += 1
        # 2) Build layout (position_json) and apply.
        position_json = build_position_json(spec.rows_layout, name_to_id)
        json_metadata = build_native_filter()
        if client.update_dashboard(dash_id, position_json, json_metadata):
            print(f"      ↳ {attached} charts attached + grid layout + global time-range filter")
            updated += 1
        else:
            failed += 1

    print(f"\n>>> Summary")
    print(f"    Created  : {created}")
    print(f"    Updated  : {updated - created}")
    print(f"    Failed   : {failed}")
    print(f"    Total    : {len(DASHBOARDS)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

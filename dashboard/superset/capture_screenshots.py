"""
Capture full-page screenshots of the 5 Superset dashboards via headless Chromium.

Output: docs/screenshots/<NN>_<slug>.png

Why headless rather than asking the user to alt-PrtScn:
  * Reproducible — anyone can re-run and get identical captures.
  * Versioned — the script lives in Git alongside the dashboards.
  * Senior signal — visual artefacts of the deliverable are produced
    deterministically from the modelled data.

Usage (with Superset running):

    .venv/Scripts/python dashboard/superset/capture_screenshots.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SUPERSET_URL = "http://localhost:8088"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DASHBOARDS = [
    ("00_executive_overview",    "executive-overview"),
    ("01_network_profitability", "network-profitability"),
    ("02_customer_retention",    "customer-retention"),
    ("03_upsell_crosssell",      "upsell-crosssell"),
    ("04_decision_layer",        "decision-layer"),
]

# Tuned for full dashboard content; Superset is responsive but we want a
# desktop-class screenshot.
VIEWPORT = {"width": 1600, "height": 1100}
# Settle time for charts (Plotly/echarts render async).
CHART_LOAD_WAIT_MS = 8_000


def main() -> int:
    print(f">>> Capturing 5 dashboards into {OUT_DIR}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1.5)
        page = context.new_page()

        # 1. Login
        page.goto(f"{SUPERSET_URL}/login/")
        page.fill('input[name="username"]', ADMIN_USER)
        page.fill('input[name="password"]', ADMIN_PASS)
        page.click('input[type="submit"]')
        page.wait_for_url(f"{SUPERSET_URL}/superset/welcome/", timeout=30_000)
        print("  ✓ Authenticated")

        # 2. Iterate dashboards
        for prefix, slug in DASHBOARDS:
            target = f"{SUPERSET_URL}/superset/dashboard/{slug}/?standalone=2"
            print(f"  → {slug:<30s}", end="", flush=True)
            page.goto(target, wait_until="networkidle", timeout=60_000)
            # Wait for charts to finish rendering (echarts shows ".echarts-for-react" eventually)
            page.wait_for_timeout(CHART_LOAD_WAIT_MS)

            out_path = OUT_DIR / f"{prefix}.png"
            page.screenshot(path=str(out_path), full_page=True)
            print(f"   → {out_path.relative_to(PROJECT_ROOT).as_posix()}")

        browser.close()

    print(f"\n>>> Done — 5 screenshots in {OUT_DIR.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

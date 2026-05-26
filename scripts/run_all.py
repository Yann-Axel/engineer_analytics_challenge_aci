"""
Orchestrator — runs the full Part 1 generation pipeline end-to-end.
Idempotent: re-running rewrites the enriched layer.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

STEPS = [
    "10_generate_fleet_and_network.py",
    "11_generate_flights.py",
    "12_generate_bookings.py",
    "13_generate_operations.py",
    "14_generate_commercial.py",
    "15_generate_customer_feedback.py",
]


def main() -> None:
    print("=" * 70)
    print("Part 1 — Synthetic data generation pipeline")
    print("=" * 70)
    t0 = time.time()
    for step in STEPS:
        script = SCRIPTS_DIR / step
        print(f"\n>>> Running {step}")
        rc = subprocess.call([sys.executable, str(script)], cwd=str(SCRIPTS_DIR))
        if rc != 0:
            print(f"!!! Step {step} failed with code {rc}")
            sys.exit(rc)
    print(f"\n=== Done in {time.time() - t0:.1f}s ===")


if __name__ == "__main__":
    main()

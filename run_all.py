"""
Run the whole pipeline in order.

    python run_all.py            # everything
    python run_all.py 4          # start from step 4 (earlier outputs must exist)
"""
import runpy
import sys
import time
from pathlib import Path

STEPS = [
    "01_clean_data.py",
    "02_build_features.py",
    "03_classify_solar.py",
    "04_classify_ev.py",
    "05_classify_heating.py",
    "06_classify_ac.py",
    "07_seasonal_customers.py",
    "08_customer_segments.py",
    "09_peak_usage.py",
    "10_ev_charging_behavior.py",
    "11_battery_simulation.py",
    "12_demand_flex_and_tiers.py",
    "13_value_and_impact.py",
    "14_make_charts.py",
]


def main():
    start_at = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    here = Path(__file__).resolve().parent
    for step in STEPS[start_at - 1:]:
        t = time.time()
        print(f"\n=== {step} ===")
        runpy.run_path(str(here / step), run_name="__main__")
        print(f"--- done in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()

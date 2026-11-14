"""
Settings shared by every script in this project.
If your data lives somewhere else, change RAW_DIR (or set the AMI_RAW_DIR environment variable).
"""
import os
from pathlib import Path

# ---------------------------------------------------------------
# Folders
# RAW_DIR holds the unzipped AMI folders (part-*.csv files), the weather
# workbook and the label workbook. Everything we create goes to data/clean
# and outputs/.
# ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
RAW_DIR = Path(os.environ.get("AMI_RAW_DIR", ROOT / "data" / "raw"))
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "outputs"
FIG_DIR = OUT_DIR / "figures"

AMI_CLEAN = CLEAN_DIR / "ami"                 # folder of parquet chunks, sorted by customer
WEATHER_CLEAN = CLEAN_DIR / "weather.parquet"
SYSTEM_HOURLY = CLEAN_DIR / "system_hourly.parquet"
FEATURES = OUT_DIR / "customer_features.csv"

# ---------------------------------------------------------------
# Processing settings
# DuckDB does the heavy lifting. Keep memory modest so it runs on a laptop.
# CHUNK = how many customers we process at once.
# ---------------------------------------------------------------
DUCKDB_MEMORY = "2GB"
CHUNK = 3000
START_DATE = "2025-09-01"                     # first day of the AMI data

# ---------------------------------------------------------------
# Battery (2 x Enphase IQ 10C, from the challenge statement)
# We also test a single unit (half the size).
# ---------------------------------------------------------------
BATTERY_2_UNITS = {"kwh": 20.16, "kw": 7.68}
BATTERY_1_UNIT = {"kwh": 10.08, "kw": 3.84}
ROUND_TRIP_EFF = 0.894
MAX_ADDED_LOAD_KW = 3.0                       # 200-amp service: ~3 kVA of extra load
PEAK_WINDOW = [18, 19, 17, 20, 16, 21, 15, 22]  # hour-ending, most important first
CHARGE_HOURS = [23, 24, 1, 2, 3, 4, 5, 6]

# ---------------------------------------------------------------
# Money (see README for sources)
# ---------------------------------------------------------------
GEN_CAPACITY_SUMMER = 5.0 * 6      # $/kW-yr, NYISO rest-of-state, ~$5/kW-month x 6 months
GEN_CAPACITY_WINTER = 3.0 * 6      # $/kW-yr, ~$3/kW-month x 6 months
DIST_VALUE_SYSTEM = 26.02          # $/kW-yr, NYSEG 2025 MCOS, system-weighted
DIST_VALUE_CONSTRAINED = 70.61     # $/kW-yr, NYSEG 2025 MCOS, capacity-constrained areas
ESS_PAY_PER_KW = 50.0              # $/kW, NYSEG/RG&E Energy Storage Solutions
NYSERDA_PER_KWH = 200.0            # $/kWh upfront, capped at $5,000
NYSERDA_CAP = 5000.0
BATTERY_COST_PER_KWH = 1116.0      # installed, national average
RETAIL_RATE = 0.22                 # $/kWh, NYSEG residential (approx.)

# ---------------------------------------------------------------
# Demand-response assumptions (our own estimates, not measured)
# ---------------------------------------------------------------
THERMOSTAT_SHARE = 0.40            # share of AC load a smart thermostat can shave at peak
HEAT_SETBACK_SHARE = 0.20          # share of heating load shaved by pre-heating / setback


def make_folders():
    """Create the output folders if they don't exist yet."""
    for p in [CLEAN_DIR, AMI_CLEAN, OUT_DIR, FIG_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def find_file(pattern):
    """Return the first file in RAW_DIR (searched recursively) whose name matches pattern."""
    hits = sorted(RAW_DIR.rglob(pattern))
    if not hits:
        raise FileNotFoundError(f"No file matching '{pattern}' under {RAW_DIR}")
    return hits[0]

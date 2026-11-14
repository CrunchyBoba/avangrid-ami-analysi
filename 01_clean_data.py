"""
Step 1 - Load and clean the raw data.

Reads every AMI part-*.csv file plus the weather workbook, removes bad rows,
and writes clean files sorted by customer, then date, then hour.

Output:
    data/clean/ami/chunk_*.parquet   hourly usage, sorted by customer
    data/clean/weather.parquet       hourly weather aligned to the meter hours
    outputs/cleaning_report.csv      what was removed and why
"""
import pandas as pd
import config
from utils import connect, save_out


# ---------------------------------------------------------------
# Load the raw meter files.
# All part-*.csv files are read together as one table. Column names are
# shortened so the rest of the code is easier to read.
# ---------------------------------------------------------------
def load_raw_ami(con):
    """Create a DuckDB view called raw_ami over every part-*.csv under RAW_DIR.

    Args:
        con: duckdb connection
    Returns:
        number of raw rows
    """
    files = sorted(str(p) for p in config.RAW_DIR.rglob("part-*.csv"))
    if not files:
        raise FileNotFoundError(f"No part-*.csv files under {config.RAW_DIR}. Unzip the AMI data there.")
    print(f"  found {len(files)} AMI files")
    con.execute(f"""
        CREATE OR REPLACE VIEW raw_ami AS
        SELECT TRY_CAST(CUSTOMER_NUMBER AS INTEGER) AS customer,
               TRY_CAST(usage_date AS DATE)         AS date,
               TRY_CAST(hour_ending AS INTEGER)     AS hour,
               TRY_CAST(hourly_kwh AS DOUBLE)       AS kwh,
               TRY_CAST(is_complete_hour AS INTEGER) AS complete
        FROM read_csv({files}, header=true, all_varchar=true)
    """)
    return con.execute("SELECT count(*) FROM raw_ami").fetchone()[0]


# ---------------------------------------------------------------
# Clean the meter data.
# We drop rows with missing values, impossible values (negative kWh, hour
# outside 1-24) and incomplete hours, then keep one row per customer-hour.
# ---------------------------------------------------------------
def clean_ami(con):
    """Create a table called ami with only good rows (one per customer, date, hour).

    Args:
        con: duckdb connection
    Returns:
        dict with counts of rows removed for each reason
    """
    counts = con.execute("""
        SELECT
          sum(CASE WHEN customer IS NULL OR date IS NULL OR hour IS NULL OR kwh IS NULL THEN 1 ELSE 0 END),
          sum(CASE WHEN kwh < 0 THEN 1 ELSE 0 END),
          sum(CASE WHEN hour NOT BETWEEN 1 AND 24 THEN 1 ELSE 0 END),
          sum(CASE WHEN complete = 0 THEN 1 ELSE 0 END)
        FROM raw_ami
    """).fetchone()
    con.execute("""
        CREATE OR REPLACE TABLE ami AS
        SELECT customer, date, hour, any_value(kwh) AS kwh
        FROM raw_ami
        WHERE customer IS NOT NULL AND date IS NOT NULL AND hour IS NOT NULL AND kwh IS NOT NULL
          AND kwh >= 0 AND hour BETWEEN 1 AND 24 AND coalesce(complete, 1) = 1
        GROUP BY customer, date, hour
    """)
    return {"missing values": counts[0], "negative kwh": counts[1],
            "bad hour": counts[2], "incomplete hour": counts[3]}


# ---------------------------------------------------------------
# Save the clean meter data sorted by customer.
# We write one parquet file per block of customers so the sort fits in memory
# and later scripts can read only the customers they need.
# ---------------------------------------------------------------
def save_sorted(con):
    """Write the ami table to data/clean/ami/ as chunk files sorted by customer, date, hour."""
    for old in config.AMI_CLEAN.glob("*.parquet"):
        old.unlink()
    lo, hi = con.execute("SELECT min(customer), max(customer) FROM ami").fetchone()
    for start in range(lo, hi + 1, config.CHUNK):
        out = config.AMI_CLEAN / f"chunk_{start:06d}.parquet"
        con.execute(f"""
            COPY (SELECT * FROM ami WHERE customer >= {start} AND customer < {start + config.CHUNK}
                  ORDER BY customer, date, hour)
            TO '{out}' (FORMAT parquet)
        """)


# ---------------------------------------------------------------
# Clean the weather data.
# Weather time stamps mark the start of the hour (0:00 = midnight-1am) while
# the meter uses hour-ending (1 = midnight-1am), so we add 1 to the hour.
# Duplicate hours (daylight-saving) are dropped and short gaps are filled.
# ---------------------------------------------------------------
def clean_weather():
    """Read the weather workbook and return a tidy hourly table.

    Returns:
        DataFrame with columns date, hour, temp_f, humidity, wind
    """
    w = pd.read_excel(config.find_file("Weather*.xlsx"))
    w.columns = [c.strip().lower() for c in w.columns]
    w["date"] = pd.to_datetime(w["date"]).dt.date
    w["hour"] = w["time"].astype(str).str.split(":").str[0].astype(int) + 1
    w = w.rename(columns={"temp": "temp_f", "windspeed": "wind"})
    w = w.drop_duplicates(["date", "hour"]).sort_values(["date", "hour"])
    missing = int(w["temp_f"].isna().sum())
    for col in ["temp_f", "humidity", "wind"]:
        w[col] = w[col].interpolate(limit_direction="both")
    print(f"  weather: {len(w):,} hours, filled {missing} missing temperatures")
    return w[["date", "hour", "temp_f", "humidity", "wind"]]


def main():
    config.make_folders()
    work_db = config.CLEAN_DIR / "work.duckdb"      # on-disk scratch database, deleted at the end
    con = connect(work_db)

    print("Loading AMI files...")
    raw_rows = load_raw_ami(con)
    removed = clean_ami(con)
    clean_rows, customers = con.execute("SELECT count(*), count(DISTINCT customer) FROM ami").fetchone()
    duplicates = raw_rows - clean_rows - sum(removed.values())
    save_sorted(con)
    print(f"  {raw_rows:,} raw rows -> {clean_rows:,} clean rows, {customers:,} customers")

    print("Cleaning weather...")
    clean_weather().to_parquet(config.WEATHER_CLEAN, index=False)

    report = pd.DataFrame(
        [{"step": "raw rows", "rows": raw_rows}]
        + [{"step": f"removed: {k}", "rows": v} for k, v in removed.items()]
        + [{"step": "removed: duplicate customer-hour", "rows": max(duplicates, 0)},
           {"step": "clean rows", "rows": clean_rows},
           {"step": "customers", "rows": customers}])
    save_out(report, "cleaning_report.csv")
    con.close()
    work_db.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

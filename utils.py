"""
Small helpers used by several scripts: opening DuckDB, reading the cleaned data,
loading the label lists, and saving tables.
"""
import duckdb
import pandas as pd
import config


def connect(db_file=None):
    """Open a DuckDB connection with a memory cap.

    Args:
        db_file: optional path for an on-disk database (used for very large tables)
    Returns:
        duckdb connection
    """
    con = duckdb.connect(str(db_file) if db_file else ":memory:")
    con.execute(f"SET memory_limit='{config.DUCKDB_MEMORY}'")
    con.execute("SET preserve_insertion_order=false")
    return con


def ami_glob():
    """Path pattern for the cleaned hourly data (one parquet file per customer chunk)."""
    return str(config.AMI_CLEAN / "*.parquet")


def customer_chunks(con):
    """Split the customer list into ranges so big queries fit in memory.

    Args:
        con: duckdb connection
    Returns:
        list of (low, high) customer-number ranges, high exclusive
    """
    lo, hi = con.execute(f"SELECT min(customer), max(customer) FROM '{ami_glob()}'").fetchone()
    return [(s, s + config.CHUNK) for s in range(lo, hi + 1, config.CHUNK)]


def load_labels():
    """Read the EV / heat pump / solar label lists from the Avangrid workbook.

    Returns:
        dict like {"ev": set(customer numbers), "hp": set(...), "pv": set(...)}
    """
    path = config.find_file("EV_Heat Pump_Solar PV Customers*.xlsx")
    sheets = pd.read_excel(path, sheet_name=None)
    return {
        "ev": set(sheets["EV Customers"]["CUSTOMER_NUMBER"]),
        "hp": set(sheets["HP Customers"]["CUSTOMER_NUMBER"]),
        "pv": set(sheets["PV Customers"]["CUSTOMER_NUMBER"]),
    }


def read_out(name):
    """Read a CSV from the outputs folder."""
    return pd.read_csv(config.OUT_DIR / name)


def save_out(df, name):
    """Write a CSV to the outputs folder and print a one-line note."""
    config.make_folders()
    df.to_csv(config.OUT_DIR / name, index=False)
    print(f"  saved outputs/{name}  ({len(df):,} rows)")

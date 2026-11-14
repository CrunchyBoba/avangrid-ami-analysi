"""
Step 11 - Hour-by-hour battery simulation for every home.

Each home gets a virtual battery (1 unit = 10.08 kWh / 3.84 kW, or 2 units =
20.16 kWh / 7.68 kW). Every day the battery covers the home's load during the
evening peak and recharges overnight, then we measure the results.

Output:
    outputs/battery_simulation.csv   one row per customer per battery size
"""
import numpy as np
import pandas as pd
import config
from utils import connect, ami_glob, customer_chunks, save_out

HOURS = 365 * 24
START = pd.Timestamp(config.START_DATE)


# ---------------------------------------------------------------
# Hour index.
# Turn (date, hour-ending) into a position 0..8759 in the year so each home's
# usage fits in one row of a numpy array.
# ---------------------------------------------------------------
def hour_index(dates, hours):
    """Return the position in the year for each (date, hour-ending) pair."""
    return ((pd.to_datetime(dates) - START).dt.days * 24 + hours - 1).to_numpy()


def load_matrix(con, lo, hi):
    """Read customers lo..hi-1 into a (customers x 8760) array of hourly kWh.

    Returns:
        (customer numbers, usage array)
    """
    df = con.execute(f"SELECT customer, date, hour, kwh FROM '{ami_glob()}' "
                     f"WHERE customer >= {lo} AND customer < {hi}").df()
    if df.empty:
        return np.array([]), None
    df["i"] = hour_index(df.date, df.hour)
    df = df[(df.i >= 0) & (df.i < HOURS)]
    customers = np.sort(df.customer.unique())
    usage = np.zeros((len(customers), HOURS), dtype=np.float32)
    usage[np.searchsorted(customers, df.customer), df.i] = df.kwh
    return customers, usage


# ---------------------------------------------------------------
# Battery rules (one day at a time).
# Discharge: cover the home's load during 3-10pm, starting with the 6-7pm system
# peak, never more than the battery's kW or the energy left.
# Recharge: 11pm-6am at no more than 3 kW (the 3 kVA rule), and never pushing
# the home above its own 99th-percentile load.
# ---------------------------------------------------------------
def simulate(usage, kwh, kw):
    """Run the battery for a block of homes.

    Args:
        usage: (homes x hours) kWh array
        kwh, kw: battery energy and power
    Returns:
        (discharge array, charge array), same shape as usage
    """
    n = usage.shape[0]
    stored = np.full(n, kwh)
    ceiling = np.quantile(usage, 0.99, axis=1)
    discharge = np.zeros_like(usage)
    charge = np.zeros_like(usage)
    max_charge = min(config.MAX_ADDED_LOAD_KW, kw)
    for day in range(365):
        base = day * 24
        for he in config.PEAK_WINDOW:
            h = base + he - 1
            out = np.minimum(np.minimum(usage[:, h], kw), stored)
            discharge[:, h] = out
            stored -= out
        for he in config.CHARGE_HOURS:
            h = base + he - 1 if he >= 23 else base + 24 + he - 1
            if h >= HOURS:
                continue
            room = np.maximum(0, ceiling - usage[:, h])
            inp = np.minimum(np.minimum(max_charge, (kwh - stored) / config.ROUND_TRIP_EFF), room)
            charge[:, h] = inp
            stored += inp * config.ROUND_TRIP_EFF
    return discharge, charge


# ---------------------------------------------------------------
# Results per home.
# Peak relief at the system's top hours, energy shifted, energy lost,
# and the home's highest hour before and after.
# ---------------------------------------------------------------
def summarize(customers, usage, discharge, charge, size, summer_idx, winter_idx):
    """Return a DataFrame of battery results for each home."""
    after = usage - discharge + charge
    kwh = config.BATTERY_2_UNITS["kwh"] if size == 2 else config.BATTERY_1_UNIT["kwh"]
    return pd.DataFrame({
        "customer": customers, "units": size,
        "relief_summer_kw": discharge[:, summer_idx].mean(axis=1),
        "relief_winter_kw": discharge[:, winter_idx].mean(axis=1),
        "load_summer_peak_kw": usage[:, summer_idx].mean(axis=1),
        "load_winter_peak_kw": usage[:, winter_idx].mean(axis=1),
        "shifted_kwh_per_year": discharge.sum(axis=1),
        "charged_kwh_per_year": charge.sum(axis=1),
        "home_max_before_kw": usage.max(axis=1),
        "home_max_after_kw": after.max(axis=1),
        "ess_event_kw": min(kwh / 3, config.BATTERY_2_UNITS["kw"] if size == 2 else config.BATTERY_1_UNIT["kw"]),
    })


def main():
    con = connect()
    system = pd.read_parquet(config.SYSTEM_HOURLY)
    summer = system[system.month.isin([6, 7, 8])].nlargest(20, "avg_kw")
    winter = system[system.month.isin([12, 1, 2])].nlargest(20, "avg_kw")
    summer_idx, winter_idx = hour_index(summer.date, summer.hour), hour_index(winter.date, winter.hour)

    results = []
    for lo, hi in customer_chunks(con):
        customers, usage = load_matrix(con, lo, hi)
        if usage is None:
            continue
        for size, spec in [(1, config.BATTERY_1_UNIT), (2, config.BATTERY_2_UNITS)]:
            d, c = simulate(usage, spec["kwh"], spec["kw"])
            results.append(summarize(customers, usage, d, c, size, summer_idx, winter_idx))
        print(f"  customers {lo}-{hi - 1} simulated")

    out = pd.concat(results)
    print(out.groupby("units")[["relief_summer_kw", "relief_winter_kw", "shifted_kwh_per_year"]].mean().round(2))
    save_out(out.round(3), "battery_simulation.csv")


if __name__ == "__main__":
    main()

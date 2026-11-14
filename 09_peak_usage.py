"""
Step 9 - When the grid peaks and who drives it.

Finds the summer and winter system peak hours, shows how system load moves with
temperature, measures each segment's share of the peak, and estimates how many
kW each technology adds at the peak.

Output:
    outputs/peak_hours.csv          top 20 summer and winter system hours
    outputs/load_vs_temperature.csv system load by 10F temperature band
    outputs/peak_by_segment.csv     share of customers vs share of peak, per segment
    outputs/kw_added_by_tech.csv    extra kW per home at the peak for each technology
"""
import numpy as np
import pandas as pd
import config
from utils import read_out, save_out


# ---------------------------------------------------------------
# System peak hours.
# The top 20 hours in Jun-Aug and in Dec-Feb. Day of week is added because the
# winter peaks turned out to be cold weekends.
# ---------------------------------------------------------------
def top_hours(system):
    """Return the top 20 summer and top 20 winter system hours."""
    out = []
    for season, months in [("summer", [6, 7, 8]), ("winter", [12, 1, 2])]:
        top = system[system.month.isin(months)].nlargest(20, "avg_kw").copy()
        top["season"] = season
        out.append(top)
    out = pd.concat(out)
    out["weekday"] = pd.to_datetime(out.date).dt.day_name()
    return out[["season", "date", "weekday", "hour", "avg_kw", "temp_f"]]


def load_vs_temperature(system):
    """Average kW per customer in each 10F temperature band (shows the U-shape)."""
    system = system.assign(temp_band=(system.temp_f // 10 * 10).astype(int))
    return system.groupby("temp_band").agg(avg_kw=("avg_kw", "mean"), hours=("avg_kw", "size")).reset_index()


# ---------------------------------------------------------------
# Who makes up the peak.
# Compare each segment's share of customers with its share of the summer
# and winter peak load.
# ---------------------------------------------------------------
def peak_by_segment(s):
    """Return per-segment customers, kW per home and share of each peak."""
    g = s.groupby("segment").agg(customers=("customer", "size"),
                                 kw_summer=("kw_summer_peak", "mean"), kw_winter=("kw_winter_peak", "mean"),
                                 sum_summer=("kw_summer_peak", "sum"), sum_winter=("kw_winter_peak", "sum"))
    g["share_customers"] = g.customers / g.customers.sum()
    g["share_summer_peak"] = g.sum_summer / g.sum_summer.sum()
    g["share_winter_peak"] = g.sum_winter / g.sum_winter.sum()
    return g.drop(columns=["sum_summer", "sum_winter"]).reset_index()


# ---------------------------------------------------------------
# kW added by each technology.
# A simple linear regression: peak kW = base + one bump per technology.
# Each coefficient is the average extra kW that technology adds at the peak.
# ---------------------------------------------------------------
def kw_added(s):
    """Return a table of extra kW per home at the summer and winter peak for each technology."""
    X = pd.DataFrame({"central AC": s.central_ac, "room AC": s.ac == "room/partial", "EV": s.ev,
                      "electric heat": s.electric_heat, "solar": s.solar}).astype(float)
    X["base"] = 1.0
    rows = {}
    for season, col in [("summer", "kw_summer_peak"), ("winter", "kw_winter_peak")]:
        ok = s[col].notna().to_numpy()
        coef = np.linalg.lstsq(X.to_numpy()[ok], s[col].to_numpy()[ok], rcond=None)[0]
        rows[season] = dict(zip(X.columns, coef))
    return pd.DataFrame(rows).reset_index().rename(columns={"index": "technology"})


def main():
    system = pd.read_parquet(config.SYSTEM_HOURLY)
    s = read_out("customer_segments.csv")
    s = s[s.exclude.isna() | (s.exclude == "")]

    peaks = top_hours(system)
    print(peaks.groupby("season").head(3).to_string(index=False))
    by_seg = peak_by_segment(s)
    print(by_seg.round(3).to_string(index=False))
    added = kw_added(s[s.seasonal.isna() | (s.seasonal == "")])
    print(added.round(2).to_string(index=False))

    save_out(peaks, "peak_hours.csv")
    save_out(load_vs_temperature(system).round(3), "load_vs_temperature.csv")
    save_out(by_seg.round(4), "peak_by_segment.csv")
    save_out(added.round(3), "kw_added_by_tech.csv")


if __name__ == "__main__":
    main()

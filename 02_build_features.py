"""
Step 2 - Build one row of features per customer.

Every classifier and analysis after this reads the same feature table, so the
heavy work on ~300 million hourly rows happens only once.

Output:
    data/clean/system_hourly.parquet   total load of all customers for each hour
    outputs/customer_features.csv      one row per customer
"""
import pandas as pd
import config
from utils import connect, ami_glob, customer_chunks, save_out


# ---------------------------------------------------------------
# System load.
# Adding every customer together for each hour gives the "system" curve.
# Its top hours tell us when the grid peaks in summer and in winter.
# ---------------------------------------------------------------
def build_system_hourly(con):
    """Sum all customers for each date and hour and attach the temperature.

    Returns:
        DataFrame with date, hour, month, customers, total_kwh, avg_kw, temp_f
    """
    df = con.execute(f"""
        SELECT a.date, a.hour, month(a.date) AS month, count(*) AS customers,
               sum(a.kwh) AS total_kwh, avg(a.kwh) AS avg_kw, any_value(w.temp_f) AS temp_f
        FROM '{ami_glob()}' a LEFT JOIN weather w USING (date, hour)
        GROUP BY a.date, a.hour ORDER BY a.date, a.hour
    """).df()
    df.to_parquet(config.SYSTEM_HOURLY, index=False)
    return df


def peak_hours(system, months, n=20):
    """Return the n highest system hours inside the given months as a DataFrame (date, hour)."""
    return system[system["month"].isin(months)].nlargest(n, "avg_kw")[["date", "hour"]]


# ---------------------------------------------------------------
# Usage and weather features.
# These describe how much a home uses, when, and how usage moves with
# temperature. They feed the solar, heating and AC classifiers.
# ---------------------------------------------------------------
USAGE_SQL = """
SELECT a.customer,
  count(*)                                   AS hours,
  sum(a.kwh) * 8760.0 / count(*)             AS annual_kwh,
  avg(a.kwh)                                 AS avg_kw,
  max(a.kwh)                                 AS max_kw,
  quantile_cont(a.kwh, 0.05)                 AS p05_kw,
  quantile_cont(a.kwh, 0.50)                 AS p50_kw,
  quantile_cont(a.kwh, 0.99)                 AS p99_kw,
  avg(CASE WHEN a.kwh = 0 THEN 1 ELSE 0 END) AS zero_share,
  {months},
  avg(a.kwh) FILTER (month(a.date) IN (6,7,8) AND a.hour BETWEEN 11 AND 15) AS summer_midday_kw,
  avg(a.kwh) FILTER (month(a.date) IN (6,7,8) AND a.hour BETWEEN 1 AND 5)   AS summer_night_kw,
  avg(a.kwh) FILTER (w.temp_f < 20)                                          AS kw_below_20f,
  avg(a.kwh) FILTER (w.temp_f BETWEEN 50 AND 65)                             AS kw_50_65f,
  avg(a.kwh) FILTER (w.temp_f >= 80 AND a.hour BETWEEN 13 AND 21)            AS kw_hot_afternoon,
  avg(a.kwh) FILTER (w.temp_f BETWEEN 55 AND 65 AND a.hour BETWEEN 13 AND 21) AS kw_mild_afternoon,
  avg(a.kwh) FILTER (month(a.date) IN (7,8) AND a.hour BETWEEN 14 AND 21 AND d.tmax >= 85) AS kw_hot_days,
  avg(a.kwh) FILTER (month(a.date) IN (7,8) AND a.hour BETWEEN 14 AND 21 AND d.tmax < 75)  AS kw_cool_days,
  corr(a.kwh, w.temp_f) FILTER (w.temp_f < 50)                               AS heat_temp_corr,
  avg(a.kwh) FILTER ((a.date, a.hour) IN (SELECT (date, hour) FROM summer_peak)) AS kw_summer_peak,
  avg(a.kwh) FILTER ((a.date, a.hour) IN (SELECT (date, hour) FROM winter_peak)) AS kw_winter_peak,
  sum(CASE WHEN a.kwh >= 6 AND w.temp_f BETWEEN 45 AND 70 THEN 1 ELSE 0 END)  AS big_hours_mild
FROM '{glob}' a
JOIN weather w USING (date, hour)
JOIN daily_max d USING (date)
WHERE a.customer >= {lo} AND a.customer < {hi}
GROUP BY a.customer
"""


# ---------------------------------------------------------------
# EV charging events.
# In mild weather (45-70F, no heating or AC) we compare each hour with the
# home's normal level for that hour. A jump of 3+ kWh held for 1-8 hours looks
# like Level 2 charging; an extra 1-2.4 kWh held 4+ hours overnight looks like Level 1.
# ---------------------------------------------------------------
EV_SQL = """
WITH x AS (
  SELECT a.customer, a.date, a.hour, a.kwh, (w.temp_f BETWEEN 45 AND 70) AS mild,
         row_number() OVER (PARTITION BY a.customer ORDER BY a.date, a.hour) AS rn
  FROM '{glob}' a JOIN weather w USING (date, hour)
  WHERE a.customer >= {lo} AND a.customer < {hi}),
normal AS (SELECT customer, hour, median(kwh) AS normal_kw FROM x WHERE mild GROUP BY customer, hour),
z AS (SELECT x.*, x.kwh - n.normal_kw AS extra FROM x JOIN normal n USING (customer, hour)),
l2 AS (SELECT customer, count(*) AS len, avg(extra) AS kw, arg_min(hour, rn) AS start_hour, bool_and(mild) AS all_mild
       FROM (SELECT *, rn - row_number() OVER (PARTITION BY customer ORDER BY rn) AS grp FROM z WHERE extra >= 3)
       GROUP BY customer, grp),
l1 AS (SELECT customer, count(*) AS len, arg_min(hour, rn) AS start_hour, bool_and(mild) AS all_mild
       FROM (SELECT *, rn - row_number() OVER (PARTITION BY customer ORDER BY rn) AS grp FROM z WHERE extra >= 1.0 AND extra < 2.4)
       GROUP BY customer, grp)
SELECT c.customer,
  coalesce(s2.l2_sessions, 0) AS l2_sessions, s2.l2_kw, s2.l2_hours, s2.l2_night_share, s2.l2_evening_share,
  coalesce(s1.l1_sessions, 0) AS l1_sessions
FROM (SELECT DISTINCT customer FROM x) c
LEFT JOIN (SELECT customer, count(*) AS l2_sessions, median(kw) AS l2_kw, median(len) AS l2_hours,
                  avg(CASE WHEN start_hour >= 21 OR start_hour <= 4 THEN 1 ELSE 0 END) AS l2_night_share,
                  avg(CASE WHEN start_hour BETWEEN 15 AND 20 THEN 1 ELSE 0 END)      AS l2_evening_share
           FROM l2 WHERE all_mild AND len BETWEEN 1 AND 8 AND kw >= 3.3 GROUP BY customer) s2 USING (customer)
LEFT JOIN (SELECT customer, count(*) AS l1_sessions FROM l1
           WHERE all_mild AND len >= 4 AND (start_hour >= 21 OR start_hour <= 3) GROUP BY customer) s1 USING (customer)
"""


def main():
    con = connect()
    con.execute(f"CREATE TABLE weather AS SELECT * FROM '{config.WEATHER_CLEAN}'")
    con.execute("CREATE TABLE daily_max AS SELECT date, max(temp_f) AS tmax FROM weather GROUP BY date")

    print("Building system load...")
    system = build_system_hourly(con)
    con.register("summer_peak_df", peak_hours(system, [6, 7, 8]))
    con.register("winter_peak_df", peak_hours(system, [12, 1, 2]))
    con.execute("CREATE TABLE summer_peak AS SELECT * FROM summer_peak_df")
    con.execute("CREATE TABLE winter_peak AS SELECT * FROM winter_peak_df")

    print("Building customer features (in chunks)...")
    months = ",\n  ".join(f"avg(a.kwh) FILTER (month(a.date) = {m}) AS m{m}" for m in range(1, 13))
    parts = []
    for lo, hi in customer_chunks(con):
        usage = con.execute(USAGE_SQL.format(months=months, glob=ami_glob(), lo=lo, hi=hi)).df()
        if usage.empty:
            continue
        ev = con.execute(EV_SQL.format(glob=ami_glob(), lo=lo, hi=hi)).df()
        parts.append(usage.merge(ev, on="customer", how="left"))
        print(f"  customers {lo}-{hi - 1} done")

    features = pd.concat(parts).sort_values("customer")
    save_out(features.round(4), "customer_features.csv")


if __name__ == "__main__":
    main()

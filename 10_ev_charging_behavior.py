"""
Step 10 - EV charging behavior.

Looks closer at EV homes: do they charge on a timer overnight or as soon as they
get home (on-peak)? Did anyone start charging during the year (a new EV)? And how
many homes on Avangrid's EV list actually charge at home?

Output:
    outputs/ev_monthly_sessions.csv  Level-2-like sessions per customer per month
    outputs/ev_behavior.csv          one row per EV home: charging style, new-adopter month
"""
import numpy as np
import pandas as pd
from utils import connect, ami_glob, customer_chunks, read_out, save_out

ORDER = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]   # data runs Sep 2025 - Aug 2026


# ---------------------------------------------------------------
# Monthly charging sessions.
# A session starts when usage jumps 3+ kWh and sits 3.3+ kWh above the home's
# normal level for that hour in that month.
# ---------------------------------------------------------------
def monthly_sessions(con):
    """Count Level-2-like charging starts per customer per month."""
    parts = []
    for lo, hi in customer_chunks(con):
        parts.append(con.execute(f"""
            WITH x AS (SELECT customer, date, hour, kwh, month(date) AS month FROM '{ami_glob()}'
                       WHERE customer >= {lo} AND customer < {hi}),
            normal AS (SELECT customer, month, hour, median(kwh) AS normal_kw FROM x GROUP BY ALL),
            z AS (SELECT x.customer, x.month, x.kwh - n.normal_kw AS extra,
                         x.kwh - lag(x.kwh) OVER (PARTITION BY x.customer ORDER BY x.date, x.hour) AS jump
                  FROM x JOIN normal n USING (customer, month, hour))
            SELECT customer, month, sum(CASE WHEN extra >= 3.3 AND jump >= 3 THEN 1 ELSE 0 END) AS sessions
            FROM z GROUP BY customer, month
        """).df())
    return pd.concat(parts)


# ---------------------------------------------------------------
# New EV owners.
# Little or no charging in the first months, then steady charging from a
# given month on. That month is the likely purchase month.
# ---------------------------------------------------------------
def adoption_month(row):
    """Return the month charging started (1-12) or NaN if the home charged all year or never."""
    r = row.to_numpy()
    for k in range(3, 11):
        if r[:k].max() <= 1 and r[k] >= 6 and (r[k:] >= 4).mean() >= 0.75:
            return ORDER[k]
    return np.nan


def charging_style(row):
    """Label an EV home 'overnight timer', 'on arrival (on-peak)' or 'mixed'."""
    if row.l2_night_share >= 0.5:
        return "overnight timer"
    if row.l2_evening_share >= 0.5:
        return "on arrival (on-peak)"
    return "mixed"


def main():
    con = connect()
    sessions = monthly_sessions(con)
    wide = sessions.pivot_table(index="customer", columns="month", values="sessions", fill_value=0)
    wide = wide.reindex(columns=ORDER, fill_value=0)

    ev = read_out("class_ev.csv")
    seg = read_out("customer_segments.csv")[["customer", "solar", "electric_heat", "central_ac", "annual_kwh"]]
    ev = ev.merge(seg, on="customer").merge(wide.sum(axis=1).rename("sessions_per_year"),
                                            left_on="customer", right_index=True, how="left")
    ev["adopted_month"] = ev.customer.map(wide.apply(adoption_month, axis=1))

    homes = ev[ev.ev].copy()
    homes["charging_style"] = homes.apply(charging_style, axis=1)
    print("  charging style:", homes.charging_style.value_counts().to_dict())

    new = homes[homes.adopted_month.notna()]
    print(f"  new EV owners during the year: {len(new)} "
          f"(central AC {new.central_ac.mean():.0%}, solar {new.solar.mean():.0%})")

    labeled = ev[ev.ev_label]
    for name, g in [("labeled & detected", labeled[labeled.ev]), ("labeled & not detected", labeled[~labeled.ev])]:
        print(f"  {name:24s} {len(g):4d} homes, median sessions/yr {g.sessions_per_year.median():.0f}")

    save_out(sessions, "ev_monthly_sessions.csv")
    save_out(homes[["customer", "ev_level", "charging_style", "adopted_month", "sessions_per_year",
                    "solar", "electric_heat", "central_ac", "annual_kwh"]].round(3), "ev_behavior.csv")


if __name__ == "__main__":
    main()

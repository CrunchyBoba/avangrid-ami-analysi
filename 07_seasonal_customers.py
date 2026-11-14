"""
Step 7 - Seasonal and unusual customers.

Some homes are empty for part of the year (student rentals, lake camps) and a
few accounts are vacant, partial-year or clearly not a normal house. We flag them
so they do not distort the other results.

Output:
    outputs/class_seasonal.csv
"""
import numpy as np
from utils import read_out, save_out

MONTHS = [f"m{m}" for m in range(1, 13)]


# ---------------------------------------------------------------
# Accounts to leave out of the main analysis.
# Vacant (<500 kWh/yr), very large (>40 MWh/yr, likely a farm or business) and
# accounts with less than half a year of data.
# ---------------------------------------------------------------
def exclusion_reason(f):
    """Return a text reason for excluding each customer, or '' to keep them."""
    return np.select(
        [f.annual_kwh < 500, f.annual_kwh > 40000, f.hours < 4380],
        ["vacant", "non-residential (>40 MWh)", "partial year"], "")


# ---------------------------------------------------------------
# Seasonal homes.
# A home is seasonal if 3+ months fall below 15% of its busiest month.
# If summer is the empty season it is "summer-vacant", otherwise "winter-vacant".
# ---------------------------------------------------------------
def seasonal_type(f):
    """Return 'summer-vacant', 'winter-vacant' or '' for each customer."""
    busiest = f[MONTHS].max(axis=1)
    low_months = (f[MONTHS].lt(0.15 * busiest, axis=0)).sum(axis=1)
    summer_low = f[["m6", "m7", "m8"]].mean(axis=1) < f[["m12", "m1", "m2"]].mean(axis=1)
    return np.where(low_months >= 3, np.where(summer_low, "summer-vacant", "winter-vacant"), "")


def main():
    f = read_out("customer_features.csv")
    heat = read_out("class_heating.csv")[["customer", "electric_heat"]]
    f = f.merge(heat, on="customer", how="left")

    f["exclude"] = exclusion_reason(f)
    f["seasonal"] = seasonal_type(f)
    print("  excluded:", f.exclude.value_counts().drop("", errors="ignore").to_dict())
    print("  seasonal:", f.seasonal.value_counts().drop("", errors="ignore").to_dict())

    sv = f[f.seasonal == "summer-vacant"]
    print(f"  summer-vacant homes with electric heat: {sv.electric_heat.mean():.0%} "
          f"(winter peak {sv.kw_winter_peak.mean():.2f} kW vs summer {sv.kw_summer_peak.mean():.2f} kW)")

    save_out(f[["customer", "exclude", "seasonal"]], "class_seasonal.csv")


if __name__ == "__main__":
    main()

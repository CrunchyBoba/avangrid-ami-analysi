"""
Step 12 - Demand flexibility, battery sizing and customer tiers.

For every home: how much peak a smart thermostat / managed charging / heating
setback could shave, which battery size makes sense, and which tier of offer
the home belongs to.

Output:
    outputs/candidates.csv   every home ranked, with tier, battery size and kW relief
"""
import numpy as np
import pandas as pd
import config
from utils import read_out, save_out


# ---------------------------------------------------------------
# Demand flexibility without a battery.
# Smart thermostat: a share of the AC load at the summer peak.
# Managed charging: move the EV's measured peak load to overnight.
# Heating setback: a share of the heating load at the winter peak.
# ---------------------------------------------------------------
def demand_flex(h, ev_kw):
    """Add dr_summer_kw and dr_winter_kw columns.

    Args:
        h: merged customer table
        ev_kw: dict with the measured EV kW at the summer and winter peak (from step 9)
    """
    ac_load = (h.kw_summer_peak - h.kw_mild_afternoon).clip(lower=0)
    heat_load = (h.kw_winter_peak - h.kw_50_65f).clip(lower=0)
    h["dr_thermostat_kw"] = config.THERMOSTAT_SHARE * ac_load * h.has_ac
    h["dr_ev_summer_kw"] = np.where(h.ev, ev_kw["summer"], 0)
    h["dr_ev_winter_kw"] = np.where(h.ev, ev_kw["winter"], 0)
    h["dr_heat_kw"] = config.HEAT_SETBACK_SHARE * heat_load * h.electric_heat
    h["dr_summer_kw"] = h.dr_thermostat_kw + h.dr_ev_summer_kw
    h["dr_winter_kw"] = h.dr_heat_kw + h.dr_ev_winter_kw
    return h


# ---------------------------------------------------------------
# Battery size.
# Start with one unit. Add the second unit only if it adds at least 0.5 kW of
# combined summer + winter peak relief.
# ---------------------------------------------------------------
def pick_battery(h, sim):
    """Attach the chosen battery size and its simulated results to each home."""
    one = sim[sim.units == 1].set_index("customer")
    two = sim[sim.units == 2].set_index("customer")
    gain = (two.relief_summer_kw + two.relief_winter_kw) - (one.relief_summer_kw + one.relief_winter_kw)
    choice = pd.Series(np.where(gain >= 0.5, 2, 1), index=one.index, name="battery_units")
    chosen = pd.concat([two.loc[choice[choice == 2].index], one.loc[choice[choice == 1].index]])
    chosen = chosen.drop(columns="units").add_prefix("b_").join(choice)
    return h.merge(chosen, left_on="customer", right_index=True, how="left")


# ---------------------------------------------------------------
# Candidate flags (from the challenge statement).
# Persistent peak: top 20% of kW at the system peak (summer or winter).
# Limited capacity: home already peaks at 10+ kW, or has Level 2 charging
# (which alone adds more than the ~3 kVA a 200-amp service should take).
# ---------------------------------------------------------------
def flags(h):
    """Add the candidate flags used to assign tiers."""
    peak = np.maximum(h.kw_summer_peak, h.kw_winter_peak)
    h["flag_persistent_peak"] = peak >= peak.quantile(0.80)
    h["flag_level2_ev"] = h.ev_level == "Level 2"
    h["flag_low_headroom"] = h.b_home_max_before_kw >= 10
    return h


def tier(row):
    """Return the offer tier for one home."""
    battery_relief = row.b_relief_summer_kw + row.b_relief_winter_kw
    if (row.flag_persistent_peak or row.flag_level2_ev or row.flag_low_headroom) and battery_relief >= 2.0:
        return "Tier 2: battery + demand response"
    if row.solar:
        return "Tier 2s: solar + battery"
    if row.dr_summer_kw + row.dr_winter_kw >= 0.5:
        return "Tier 1: demand response only"
    return "Tier 0: monitor"


def main():
    seg = read_out("customer_segments.csv")
    feats = read_out("customer_features.csv")[["customer", "kw_mild_afternoon", "kw_50_65f"]]
    h = seg.merge(feats, on="customer")
    h = h[(h.exclude.isna() | (h.exclude == "")) & (h.seasonal != "winter-vacant")].copy()
    for col in ["ev", "electric_heat", "solar", "has_ac"]:
        h[col] = h[col].astype(bool)

    added = read_out("kw_added_by_tech.csv").set_index("technology")
    h = demand_flex(h, {"summer": added.loc["EV", "summer"], "winter": added.loc["EV", "winter"]})
    h = pick_battery(h, read_out("battery_simulation.csv"))
    h = flags(h)
    h["tier"] = h.apply(tier, axis=1)

    # Rank inside the battery tier: most peak relief first, small bonus for EV and low headroom
    h["priority_score"] = (h.b_relief_summer_kw + h.b_relief_winter_kw
                           + 0.5 * h.flag_level2_ev + 0.3 * h.flag_low_headroom)
    h = h.sort_values(["tier", "priority_score"], ascending=[False, False])
    print(h.tier.value_counts().to_string())
    save_out(h.round(3), "candidates.csv")


if __name__ == "__main__":
    main()

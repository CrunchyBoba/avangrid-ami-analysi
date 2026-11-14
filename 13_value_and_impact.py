"""
Step 13 - Impact and dollar value.

Turns the tiers into the numbers the challenge asks for: peak reduction, load
shifting, capacity relief, bill impact, electrification enablement and solar
charging. Also checks that targeting beats picking homes at random.

Output:
    outputs/impact_summary.csv     the headline numbers
    outputs/targeting_vs_random.csv
    outputs/tier_summary.csv
"""
import numpy as np
import pandas as pd
import config
from utils import read_out, save_out

PROGRAM_SHARE = 0.03  # first battery program = top 3% of homes (about 1,000 of 33,000)


# ---------------------------------------------------------------
# Dollar value per battery.
# Utility: generation capacity (summer + winter) plus distribution capacity.
# Customer: Energy Storage Solutions event pay, minus energy lost in the battery.
# ---------------------------------------------------------------
def add_value(h):
    """Add utility and customer $/year columns for each home's chosen battery."""
    biggest = np.maximum(h.b_relief_summer_kw, h.b_relief_winter_kw)
    gen = h.b_relief_summer_kw * config.GEN_CAPACITY_SUMMER + h.b_relief_winter_kw * config.GEN_CAPACITY_WINTER
    h["utility_value"] = gen + biggest * config.DIST_VALUE_SYSTEM
    h["utility_value_constrained"] = gen + biggest * config.DIST_VALUE_CONSTRAINED
    h["customer_ess_pay"] = config.ESS_PAY_PER_KW * h.b_ess_event_kw
    h["customer_energy_loss"] = (h.b_charged_kwh_per_year - h.b_shifted_kwh_per_year) * config.RETAIL_RATE
    h["battery_kwh"] = np.where(h.battery_units == 2, config.BATTERY_2_UNITS["kwh"], config.BATTERY_1_UNIT["kwh"])
    h["battery_cost"] = h.battery_kwh * config.BATTERY_COST_PER_KWH
    h["nyserda_rebate"] = np.minimum(h.battery_kwh * config.NYSERDA_PER_KWH, config.NYSERDA_CAP)
    return h


def mw(series):
    """Sum a kW column and return MW."""
    return series.sum() / 1000


# ---------------------------------------------------------------
# Targeted vs random.
# Same number of batteries, placed by our ranking or at random.
# ---------------------------------------------------------------
def targeting_test(h, shares=(0.015, 0.03, 0.06)):
    """Return MW of peak relief for targeted vs random placement (1.5%, 3% and 6% of homes)."""
    pool = h[h.tier.str.startswith("Tier 2")]
    rows = []
    for share in shares:
        n = min(int(len(h) * share), len(pool))
        top = pool.nlargest(n, "priority_score")
        rnd = h.sample(n, random_state=1)
        rows.append({"batteries": n,
                     "targeted_summer_mw": mw(top.b_relief_summer_kw), "targeted_winter_mw": mw(top.b_relief_winter_kw),
                     "random_summer_mw": mw(rnd.b_relief_summer_kw), "random_winter_mw": mw(rnd.b_relief_winter_kw)})
    out = pd.DataFrame(rows)
    out["times_better"] = ((out.targeted_summer_mw + out.targeted_winter_mw)
                           / (out.random_summer_mw + out.random_winter_mw))
    return out


# ---------------------------------------------------------------
# Headline impacts.
# MW are also shown per 100,000 homes so they can be scaled to any service area.
# ---------------------------------------------------------------
def impact_summary(h):
    """Return a two-column table of the headline numbers."""
    n = len(h)
    per100k = lambda kw_sum: kw_sum / 1000 / n * 100_000
    t1 = h[h.tier.str.startswith("Tier 1")]
    top_n = int(n * PROGRAM_SHARE)
    top = h[h.tier.str.startswith("Tier 2")].nlargest(top_n, "priority_score")
    l2 = h[h.flag_level2_ev]
    solar = h[h.solar]
    items = {
        "homes analysed": n,
        "Tier 1 demand response: summer MW per 100k homes": per100k(t1.dr_summer_kw.sum()),
        "Tier 1 demand response: winter MW per 100k homes": per100k(t1.dr_winter_kw.sum()),
        "Battery program size (top 3% of homes)": top_n,
        "Battery program: summer MW per 100k homes": per100k(top.b_relief_summer_kw.sum()),
        "Battery program: winter MW per 100k homes": per100k(top.b_relief_winter_kw.sum()),
        "Battery program: summer kW relief per battery": top.b_relief_summer_kw.mean(),
        "Battery program: winter kW relief per battery": top.b_relief_winter_kw.mean(),
        "Battery program: kWh shifted per battery per year": top.b_shifted_kwh_per_year.mean(),
        "Battery program: home max kW before": top.b_home_max_before_kw.mean(),
        "Battery program: home max kW after": top.b_home_max_after_kw.mean(),
        "Utility value per battery $/yr (system average)": top.utility_value.mean(),
        "Utility value per battery $/yr (constrained area)": top.utility_value_constrained.mean(),
        "Customer ESS pay per battery $/yr": top.customer_ess_pay.mean(),
        "Customer energy-loss cost per battery $/yr": top.customer_energy_loss.mean(),
        "Battery installed cost $": top.battery_cost.mean(),
        "NYSERDA rebate $": top.nyserda_rebate.mean(),
        "Level 2 EV homes (each adds more than 3 kVA)": len(l2),
        "Level 2 EV homes: battery relief at summer peak (kW)": l2.b_relief_summer_kw.mean(),
        "Solar homes": len(solar),
        "Solar homes: battery kWh per year that solar could charge": solar.b_shifted_kwh_per_year.mean(),
    }
    return pd.DataFrame({"metric": list(items), "value": list(items.values())})


def main():
    h = add_value(read_out("candidates.csv"))
    summary = impact_summary(h)
    print(summary.round(2).to_string(index=False))
    test = targeting_test(h)
    print(test.round(2).to_string(index=False))

    tiers = h.groupby("tier").agg(homes=("customer", "size"),
                                  battery_relief_summer_kw=("b_relief_summer_kw", "mean"),
                                  battery_relief_winter_kw=("b_relief_winter_kw", "mean"),
                                  dr_summer_kw=("dr_summer_kw", "mean"), dr_winter_kw=("dr_winter_kw", "mean"),
                                  utility_value=("utility_value", "mean")).reset_index()
    save_out(summary.round(3), "impact_summary.csv")
    save_out(test.round(3), "targeting_vs_random.csv")
    save_out(tiers.round(3), "tier_summary.csv")
    save_out(h.round(3), "candidates.csv")


if __name__ == "__main__":
    main()

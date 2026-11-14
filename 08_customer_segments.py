"""
Step 8 - Customer segments and technology overlap.

Puts the four classifications together, groups customers into segments by how
many technologies they have, and measures how often technologies show up
together (co-adoption).

Output:
    outputs/customer_segments.csv   one row per customer with all labels and the segment
    outputs/segment_summary.csv     size and usage of each segment
    outputs/coadoption.csv          how much more likely tech B is when a home has tech A
"""
import numpy as np
import pandas as pd
from utils import read_out, load_labels, save_out


# ---------------------------------------------------------------
# Combine all the classifier outputs into one table.
# ---------------------------------------------------------------
def combine():
    """Merge features with solar, EV, heating, AC and seasonal results."""
    f = read_out("customer_features.csv")
    for name in ["class_solar.csv", "class_ev.csv", "class_heating.csv", "class_ac.csv", "class_seasonal.csv"]:
        f = f.merge(read_out(name), on="customer", how="left")
    f["exclude"] = f.exclude.fillna("")
    f["seasonal"] = f.seasonal.fillna("")
    for col in ["solar", "ev", "electric_heat", "has_ac"]:
        f[col] = f[col].fillna(False).astype(bool)
    f["central_ac"] = f.ac == "central"
    return f


# ---------------------------------------------------------------
# Segments.
# Seasonal homes first (occupancy matters more than equipment). Then count the
# three "electrification" technologies: EV, electric heat, solar. AC is used to
# split the homes that have none of them.
# ---------------------------------------------------------------
def segment(row):
    """Return the segment name for one customer."""
    if row.seasonal:
        return f"Seasonal ({row.seasonal})"
    n = int(row.ev) + int(row.electric_heat) + int(row.solar)
    if n >= 2:
        return "High-electrified (2+ techs)"
    if n == 1:
        return "Single-tech: " + ("EV" if row.ev else "Electric heat" if row.electric_heat else "Solar")
    if row.central_ac:
        return "No tech: central AC"
    return "No tech: room/partial AC" if row.has_ac else "No tech: no AC"


# ---------------------------------------------------------------
# Co-adoption ("lift").
# Lift = how common tech B is among homes with tech A, divided by how common
# B is overall. Lift 6 means six times more likely than average.
# ---------------------------------------------------------------
def lift_table(f, pairs):
    """Return a DataFrame of P(B | A), base rate of B, and the lift for each (A, B) pair."""
    rows = []
    for a, b in pairs:
        base = f[b].mean()
        given = f.loc[f[a], b].mean()
        rows.append({"if_home_has": a, "then_has": b, "rate_given": given, "base_rate": base,
                     "lift": given / base if base else np.nan})
    return pd.DataFrame(rows)


def label_lift(labels, n_customers):
    """Lift from Avangrid's own lists, correcting EV and HP for the 25% sampling.

    Args:
        labels: dict of label sets
        n_customers: number of customers in the data
    Returns:
        DataFrame with the label-based lifts
    """
    ev_total, hp_total = len(labels["ev"]) / 0.25, len(labels["hp"]) / 0.25
    rows = [("solar", "EV", len(labels["pv"] & labels["ev"]) / 0.25 / len(labels["pv"]), ev_total / n_customers),
            ("solar", "heat pump", len(labels["pv"] & labels["hp"]) / 0.25 / len(labels["pv"]), hp_total / n_customers),
            ("heat pump", "EV", len(labels["hp"] & labels["ev"]) / 0.25 / len(labels["hp"]), ev_total / n_customers)]
    out = pd.DataFrame(rows, columns=["if_home_has", "then_has", "rate_given", "base_rate"])
    out["lift"] = out.rate_given / out.base_rate
    return out


def main():
    f = combine()
    f["segment"] = f.apply(segment, axis=1)
    keep = f[f.exclude == ""]

    summary = keep.groupby("segment").agg(
        customers=("customer", "size"), annual_kwh=("annual_kwh", "mean"),
        kw_summer_peak=("kw_summer_peak", "mean"), kw_winter_peak=("kw_winter_peak", "mean")).reset_index()
    summary["share_of_customers"] = summary.customers / summary.customers.sum()
    print(summary.round(2).to_string(index=False))

    year_round = keep[keep.seasonal == ""]
    pairs = [("solar", "ev"), ("ev", "solar"), ("ev", "electric_heat"), ("electric_heat", "ev"),
             ("solar", "electric_heat"), ("central_ac", "ev")]
    lifts = pd.concat([lift_table(year_round, pairs).assign(source="our classifiers"),
                       label_lift(load_labels(), len(f)).assign(source="Avangrid label lists")])
    print(lifts.round(3).to_string(index=False))

    cols = ["customer", "segment", "exclude", "seasonal", "ev", "ev_level", "electric_heat", "heating",
            "solar", "ac", "has_ac", "central_ac", "annual_kwh", "kw_summer_peak", "kw_winter_peak"]
    save_out(f[cols].round(3), "customer_segments.csv")
    save_out(summary.round(3), "segment_summary.csv")
    save_out(lifts.round(3), "coadoption.csv")


if __name__ == "__main__":
    main()

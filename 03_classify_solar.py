"""
Step 3 - Solar (PV) customers.

Avangrid's solar list is complete, so it is the answer for who has solar.
We still build a simple usage rule to (1) show solar is easy to see in the data
and (2) flag homes that look like solar but are not on the list.

Output:
    outputs/class_solar.csv
"""
import config
from utils import read_out, load_labels, save_out


# ---------------------------------------------------------------
# Solar signature.
# The meter only records power taken from the grid, so a solar home shows some
# zero hours AND much lower summer midday use than summer night use.
# Needing both signs keeps vacant homes (zeros all day) from being flagged.
# ---------------------------------------------------------------
def solar_rule(f):
    """Flag homes whose usage looks like rooftop solar.

    Args:
        f: customer features table
    Returns:
        boolean Series, True = looks like solar
    """
    midday_vs_night = f["summer_midday_kw"] / f["summer_night_kw"]
    return (f["zero_share"] > 0.02) & (midday_vs_night < 0.6) & (f["summer_night_kw"] > 0.2)


def check_rule(f):
    """Print how well the rule matches the official solar list (precision and recall)."""
    tp = (f.solar_rule & f.solar).sum()
    print(f"  rule finds {tp} of {f.solar.sum()} listed solar homes (recall {tp / f.solar.sum():.0%}), "
          f"precision {tp / max(f.solar_rule.sum(), 1):.0%}")


def main():
    f = read_out("customer_features.csv")
    f["solar"] = f.customer.isin(load_labels()["pv"])
    f["solar_rule"] = solar_rule(f)
    check_rule(f)

    # Homes that look like solar, are not on the list, and are occupied in summer
    seasonal_like = f[["m6", "m7", "m8"]].mean(axis=1) < 0.15 * f[[f"m{m}" for m in range(1, 13)]].max(axis=1)
    f["solar_candidate"] = ~f.solar & (f.summer_midday_kw / f.summer_night_kw < 0.4) & (f.summer_night_kw > 0.3) & ~seasonal_like
    print(f"  solar on list: {f.solar.sum():,}   unlisted solar-like homes: {f.solar_candidate.sum():,}")

    save_out(f[["customer", "solar", "solar_rule", "solar_candidate"]], "class_solar.csv")


if __name__ == "__main__":
    main()

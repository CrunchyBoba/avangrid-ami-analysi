"""
Step 5 - Electric heating customers.

There is no full heating list, only 100 heat-pump homes. We use physics instead:
a home heated with electricity uses a lot more power on very cold hours than on
mild ones. The heat-pump list is used to check the rule.

Output:
    outputs/class_heating.csv
"""
import numpy as np
from utils import read_out, load_labels, save_out

PRIMARY_KW = 1.0       # extra kW below 20F that means electricity is the main heat
SUPPLEMENTAL_KW = 0.5  # smaller bump = some electric heat (space heaters, mini-split)


# ---------------------------------------------------------------
# Heating size.
# Extra power when it is below 20F compared with mild 50-65F weather.
# Gas or oil heated homes only add a little (fans, lights).
# ---------------------------------------------------------------
def heating_kw(f):
    """Return the extra kW a home uses on cold (<20F) hours versus mild hours."""
    return f.kw_below_20f - f.kw_50_65f


def heating_type(kw):
    """Turn extra cold-weather kW into a label: 'primary', 'supplemental' or 'none'."""
    return np.select([kw >= PRIMARY_KW, kw >= SUPPLEMENTAL_KW], ["primary", "supplemental"], "none")


def main():
    f = read_out("customer_features.csv")
    hp = load_labels()["hp"]
    f["heat_kw"] = heating_kw(f)
    f["heating"] = heating_type(f.heat_kw)
    f["heat_pump_label"] = f.customer.isin(hp)
    # A labeled heat pump always counts as electric heat
    f["electric_heat"] = (f.heating == "primary") | f.heat_pump_label

    print("  heating groups:", f.heating.value_counts().to_dict())
    print("  labeled heat pumps by group:", f.loc[f.heat_pump_label, "heating"].value_counts().to_dict())
    print(f"  electric-heat homes: {f.electric_heat.sum():,}")

    save_out(f[["customer", "heat_kw", "heating", "heat_pump_label", "electric_heat"]].round(4),
             "class_heating.csv")


if __name__ == "__main__":
    main()

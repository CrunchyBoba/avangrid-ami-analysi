"""
Step 6 - Air conditioning (AC) customers.

No AC labels exist, so this is a physics rule. A home with AC uses more power on
hot afternoons than on mild ones, and more on hot July/August days than on cool
days in the same months (this second test rules out pools and summer visitors).

Output:
    outputs/class_ac.csv
"""
import numpy as np
from utils import read_out, save_out


# ---------------------------------------------------------------
# Cooling size, measured two ways.
# 1) hot (80F+) vs mild (55-65F) afternoons
# 2) hot (85F+) vs cool (<75F) days within July and August
# ---------------------------------------------------------------
def cooling_kw(f):
    """Return (extra kW on hot afternoons, extra kW on hot days in the same months)."""
    return f.kw_hot_afternoon - f.kw_mild_afternoon, f.kw_hot_days - f.kw_cool_days


# ---------------------------------------------------------------
# AC type.
# Central AC adds roughly 2-5 kW, window/room units about 0.5-1.5 kW.
# Both tests must agree before we call a home AC.
# ---------------------------------------------------------------
def ac_type(hot_vs_mild, hot_vs_cool):
    """Label each home 'central', 'room/partial' or 'none'."""
    central = (hot_vs_mild >= 1.2) & (hot_vs_cool >= 0.8)
    room = (hot_vs_mild >= 0.3) & (hot_vs_cool >= 0.2)
    return np.select([central, room], ["central", "room/partial"], "none")


def main():
    f = read_out("customer_features.csv")
    f["cool_kw"], f["cool_kw_same_month"] = cooling_kw(f)
    f["ac"] = ac_type(f.cool_kw, f.cool_kw_same_month)
    f["has_ac"] = f.ac != "none"
    print("  AC groups:", f.ac.value_counts().to_dict())
    save_out(f[["customer", "cool_kw", "cool_kw_same_month", "ac", "has_ac"]].round(4), "class_ac.csv")


if __name__ == "__main__":
    main()

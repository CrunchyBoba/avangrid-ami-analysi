"""
Step 14 - Charts for the slides and the README.

Reads the output tables and saves PNG charts to outputs/figures/.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import config
from utils import read_out

SUMMER, WINTER, GREY, GREEN = "#e8710a", "#1a73e8", "#9aa0a6", "#188038"


def save(fig, name):
    """Save a figure to outputs/figures and close it."""
    fig.tight_layout()
    fig.savefig(config.FIG_DIR / name, dpi=130)
    plt.close(fig)
    print(f"  saved outputs/figures/{name}")


# ---------------------------------------------------------------
# Chart 1 and 2: the grid's peak.
# System load against temperature (U-shape), and each segment's share of
# customers vs. share of the summer and winter peak.
# ---------------------------------------------------------------
def chart_load_vs_temp():
    """Scatter of every hour's average kW per customer against temperature."""
    s = pd.read_parquet(config.SYSTEM_HOURLY)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(s.temp_f, s.avg_kw, s=3, alpha=0.3, color="#555")
    top = s.loc[s.avg_kw.idxmax()]
    ax.annotate(f"Peak: {top.date} hour {top.hour}, {top.temp_f:.0f}F", (top.temp_f, top.avg_kw),
                xytext=(10, top.avg_kw * 0.97), arrowprops=dict(arrowstyle="->"))
    ax.set(xlabel="Outdoor temperature (F)", ylabel="Average kW per customer",
           title="System load vs temperature: peaks on hot and cold days")
    save(fig, "01_load_vs_temperature.png")


def chart_peak_by_segment():
    """Bar chart of share of customers vs share of summer and winter peak per segment."""
    g = read_out("peak_by_segment.csv").sort_values("share_summer_peak")
    y = np.arange(len(g))
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(y - 0.27, 100 * g.share_customers, 0.27, color=GREY, label="% of customers")
    ax.barh(y, 100 * g.share_summer_peak, 0.27, color=SUMMER, label="% of summer peak")
    ax.barh(y + 0.27, 100 * g.share_winter_peak, 0.27, color=WINTER, label="% of winter peak")
    ax.set_yticks(y, g.segment)
    ax.set(xlabel="%", title="Who makes up the peak")
    ax.legend()
    save(fig, "02_peak_by_segment.png")


def chart_kw_added():
    """Extra kW each technology adds at the summer and winter peak."""
    k = read_out("kw_added_by_tech.csv")
    k = k[k.technology != "base"]
    x = np.arange(len(k))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - 0.2, k.summer, 0.4, color=SUMMER, label="Summer peak")
    ax.bar(x + 0.2, k.winter, 0.4, color=WINTER, label="Winter peak")
    ax.set_xticks(x, k.technology)
    ax.set(ylabel="Extra kW per home at the peak", title="What each technology adds to the peak")
    ax.legend()
    save(fig, "03_kw_added_by_tech.png")


# ---------------------------------------------------------------
# Chart 4 and 5: the recommendation.
# Targeted vs random battery placement, and peak relief by tier.
# ---------------------------------------------------------------
def chart_targeting():
    """Grouped bars: MW relief from targeted vs random batteries."""
    t = read_out("targeting_vs_random.csv")
    x = np.arange(len(t))
    tgt = (t.targeted_summer_mw + t.targeted_winter_mw) / 2
    rnd = (t.random_summer_mw + t.random_winter_mw) / 2
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - 0.2, tgt, 0.4, color=GREEN, label="Data-targeted")
    ax.bar(x + 0.2, rnd, 0.4, color=GREY, label="Random")
    for i in range(len(t)):
        ax.text(x[i] - 0.2, tgt[i], f"{tgt[i]:.1f} MW", ha="center", va="bottom")
    ax.set_xticks(x, [f"{n:,} batteries" for n in t.batteries])  # 1.5%, 3%, 6% of homes
    ax.set(ylabel="Peak relief (MW, avg of summer and winter)", title="Targeting batteries vs random placement")
    ax.legend()
    save(fig, "04_targeting_vs_random.png")


def chart_tiers():
    """Average kW relief per home by tier, battery and demand response."""
    t = read_out("tier_summary.csv")
    x = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - 0.3, t.battery_relief_summer_kw, 0.2, color=SUMMER, label="Battery, summer")
    ax.bar(x - 0.1, t.battery_relief_winter_kw, 0.2, color=WINTER, label="Battery, winter")
    ax.bar(x + 0.1, t.dr_summer_kw, 0.2, color="#f9ab00", label="Demand response, summer")
    ax.bar(x + 0.3, t.dr_winter_kw, 0.2, color="#8ab4f8", label="Demand response, winter")
    ax.set_xticks(x, [f"{a}\n({b:,} homes)" for a, b in zip(t.tier, t.homes)], fontsize=8)
    ax.set(ylabel="kW of peak relief per home", title="Peak relief per home by tier")
    ax.legend(fontsize=8)
    save(fig, "05_relief_by_tier.png")


def main():
    config.make_folders()
    chart_load_vs_temp()
    chart_peak_by_segment()
    chart_kw_added()
    chart_targeting()
    chart_tiers()


if __name__ == "__main__":
    main()

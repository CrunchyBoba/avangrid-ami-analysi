"""
Step 4 - Electric vehicle (EV) customers, Level 1 vs Level 2.

Avangrid labeled a random 25% of likely EV homes. The other 75% are hidden among
"unlabeled" homes, so we use positive-unlabeled (PU) learning: many small models,
each comparing the labeled EVs with a random slice of unlabeled homes.

Output:
    outputs/class_ev.csv
"""
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from utils import read_out, load_labels, save_out

LABEL_RATE = 0.25        # Avangrid: the list is ~25% of all EV homes
N_BAGS = 15              # small models per fold
FEATURES = ["l2_sessions", "l2_kw", "l2_hours", "l2_night_share", "l2_evening_share", "l1_sessions",
            "big_hours_mild", "max_kw", "p99_kw", "p05_kw", "p50_kw", "annual_kwh", "zero_share",
            "heat_kw", "cool_kw", "heat_temp_corr", "solar"]


# ---------------------------------------------------------------
# Extra features.
# Heating and cooling size help the model tell EV charging apart from big
# weather-driven loads, which also create large hours.
# ---------------------------------------------------------------
def add_features(f, labels):
    """Add heating/cooling size and the solar flag to the feature table."""
    f["heat_kw"] = f.kw_below_20f - f.kw_50_65f
    f["cool_kw"] = f.kw_hot_afternoon - f.kw_mild_afternoon
    f["solar"] = f.customer.isin(labels["pv"]).astype(int)
    return f


# ---------------------------------------------------------------
# PU learning with bagging.
# For each of 5 folds we train N_BAGS models (labeled EVs vs. a random sample of
# unlabeled homes) and average them. Every customer gets an out-of-fold score.
# ---------------------------------------------------------------
def pu_scores(X, y, seed=0):
    """Score every customer for 'looks like a labeled EV'.

    Args:
        X: feature matrix (numpy)
        y: 1 for labeled EV, 0 for unlabeled
    Returns:
        numpy array of scores between 0 and 1 (higher = more EV-like)
    """
    rng = np.random.default_rng(seed)
    scores = np.zeros(len(y))
    folds = StratifiedKFold(5, shuffle=True, random_state=1)
    for train, test in folds.split(X, y):
        pos, unl = train[y[train] == 1], train[y[train] == 0]
        for _ in range(N_BAGS):
            sample = rng.choice(unl, size=min(len(unl), len(pos) * 8), replace=False)
            rows = np.r_[pos, sample]
            model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05,
                                                   max_leaf_nodes=15, min_samples_leaf=20)
            model.fit(X[rows], y[rows])
            scores[test] += model.predict_proba(X[test])[:, 1] / N_BAGS
    return scores


# ---------------------------------------------------------------
# Decide who has an EV and which charger.
# We know roughly how many EVs exist (labeled / 0.25), so the top-scoring
# homes up to that count are called EVs. Charger level comes from session size.
# ---------------------------------------------------------------
def pick_evs(f):
    """Mark the expected number of top-scoring homes as EVs and print recall on the labels."""
    n_expected = int(round(f.ev_label.sum() / LABEL_RATE))
    f["ev_rank"] = f.ev_score.rank(ascending=False)
    f["ev"] = f.ev_rank <= n_expected
    recall = f.loc[f.ev_label, "ev"].mean()
    print(f"  expected EV homes: {n_expected:,}  |  labeled EVs found in that group: {recall:.0%} "
          f"(random guess would be {n_expected / len(f):.0%})")
    return f


def charger_level(row):
    """Return 'Level 2', 'Level 1', 'EV (unclear level)' or '' for one customer."""
    if not row.ev:
        return ""
    if row.l2_sessions >= 10 and row.l2_kw >= 3.3:
        return "Level 2"
    if row.l1_sessions >= 5:
        return "Level 1"
    return "EV (unclear level)"


def main():
    labels = load_labels()
    f = add_features(read_out("customer_features.csv"), labels)
    f["ev_label"] = f.customer.isin(labels["ev"])
    X = f[FEATURES].replace([np.inf, -np.inf], np.nan).to_numpy()

    print("Training PU models...")
    f["ev_score"] = pu_scores(X, f.ev_label.astype(int).to_numpy())
    f = pick_evs(f)
    f["ev_level"] = f.apply(charger_level, axis=1)
    print("  ", f.loc[f.ev, "ev_level"].value_counts().to_dict())

    save_out(f[["customer", "ev_label", "ev_score", "ev_rank", "ev", "ev_level",
                "l2_sessions", "l2_kw", "l2_night_share", "l2_evening_share", "l1_sessions"]].round(4),
             "class_ev.csv")


if __name__ == "__main__":
    main()

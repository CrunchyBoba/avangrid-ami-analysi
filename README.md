# Avangrid AMI Hackathon 2026: Who Drives the Peak, and What to Offer Them

We used one year of hourly smart-meter data (34,238 homes, Sep 2025 – Aug 2026) and hourly weather to:

1. **Classify** homes by the four big electric loads: **EV (Level 1 / Level 2), electric heating, solar, and AC**.
2. **Group** homes into segments and study **peak behavior** (summer vs winter, seasonal homes, EV charging habits).
3. **Recommend** the right offer for each home: demand response, a battery, or both. We size the battery and put a value on it.

A plain-language summary of the results is in **[FINDINGS.md](FINDINGS.md)**.

---

## How to run it

```bash
pip install -r requirements.txt
# put the data in data/raw/ (see "Data" below), then:
python run_all.py          # runs steps 01 → 14 in order (~2 minutes on a laptop)
python run_all.py 4        # or restart from a given step
```

Each script prints what it found and writes its tables to `outputs/` and charts to `outputs/figures/`.

## Data

The meter data is **not in this repository**: it is Avangrid customer data, and it is ~14 GB. To run the code:

1. Download the four zips (`2026 Avangrid Hackathon Data_*.zip`) from the hackathon SharePoint.
2. Unzip them into `data/raw/` (any sub-folder is fine; the code looks for `part-*.csv` files).
3. Put `Weather*.xlsx` and `EV_Heat Pump_Solar PV Customers.xlsx` in `data/raw/` too.

You can also point the code at another folder: `export AMI_RAW_DIR=/path/to/folder`.

## Repository layout

| Step | File | What it does |
|---|---|---|
| Setup | `config.py` | Folders, battery spec, prices, assumptions, all in one place |
| | `utils.py` | Small helpers (DuckDB connection, reading labels, saving tables) |
| **1. Prepare** | `01_clean_data.py` | Reads all CSVs, removes missing/negative/incomplete/duplicate rows, sorts by customer; cleans and aligns weather |
| | `02_build_features.py` | One row of ~45 features per customer (usage, temperature response, peak-hour load, EV charging events) |
| **2. Classify** | `03_classify_solar.py` | Solar homes (Avangrid's list) + a usage rule that checks it and flags unlisted solar-like homes |
| | `04_classify_ev.py` | EV homes with positive-unlabeled (PU) learning; Level 1 vs Level 2 from charging size |
| | `05_classify_heating.py` | Electric heat from the extra power used on very cold hours |
| | `06_classify_ac.py` | AC (none / room / central) from the extra power used on hot afternoons |
| **3. Behavior** | `07_seasonal_customers.py` | Summer-vacant and winter-vacant homes; vacant / non-residential exclusions |
| | `08_customer_segments.py` | Segments + how often technologies show up together (co-adoption) |
| | `09_peak_usage.py` | When the grid peaks, who makes up the peak, kW each technology adds |
| | `10_ev_charging_behavior.py` | Timer vs on-arrival charging, new EV owners during the year, label check |
| **4. Recommend** | `11_battery_simulation.py` | Hour-by-hour battery simulation for every home (1 and 2 units) |
| | `12_demand_flex_and_tiers.py` | Demand-response estimates, battery size, candidate flags, tiers |
| | `13_value_and_impact.py` | MW, kWh shifted, $ value, targeted-vs-random test |
| | `14_make_charts.py` | Charts in `outputs/figures/` |

---

## Methodology

### 1. Cleaning (`01`)
- Rows with missing values, negative kWh, hour outside 1–24, or `is_complete_hour = 0` are removed. Duplicate customer-hours are collapsed to one row.
- Weather time stamps mark the **start** of an hour while the meter uses **hour-ending**, so weather hour + 1 = meter hour.
- 94 missing temperatures (Mar 8–11) are filled by interpolation, and the duplicate daylight-saving hour is dropped.
- Note: the `_10001_20000_v2` zip is missing ~1,400 customers (18,152–18,346 and 18,747–19,953), so we analyse 34,238 of 35,725.

### 2. Classifying the four technologies (`03`–`06`)

| Technology | Signal in the data | Method | How we checked it |
|---|---|---|---|
| **Solar** | Meter records only grid imports, so solar shows **zero hours** and **summer midday use far below night use** | Avangrid's list is complete, so it is the answer. A rule (zeros + midday/night < 0.6) checks it | Rule finds 85% of listed solar homes at 87% precision; flags 231 unlisted solar-like homes |
| **EV** | In **mild weather (45–70°F)**, a jump of **3+ kWh** above the home's normal level for that hour, held 1–8 h (Level 2), or +1–2.4 kWh held 4+ h overnight (Level 1) | **PU learning**: the EV list is a random 25% of EV homes, so we train many gradient-boosting models (labeled EVs vs random unlabeled homes) and average them. The top *labeled ÷ 0.25* homes are called EVs | 30% of labeled EVs land in the top 2% of homes (15× random). The 130 labeled EVs we don't flag charge a median of 6 times a year vs 142 for the ones we do (see FINDINGS) |
| **Electric heat** | Extra kW on **<20°F hours vs 50–65°F hours**. Gas/oil homes barely change | ≥1.0 kW = primary electric heat, 0.5–1.0 = supplemental. Labeled heat pumps always count | Of 88 labeled heat pumps, 49% primary, 13% supplemental, 39% show little cold-weather load (likely mini-splits with fossil backup) |
| **AC** | Extra kW on **80°F+ afternoons vs 55–65°F**, and on **hot vs cool days in the same July/August** (rules out pools and summer visitors) | Both tests must agree: central (≥1.2 kW), room/partial (≥0.3 kW), none | Results line up with the summer system peak (central-AC homes = 40% of it) |

**Why mild weather for EVs?** In this cold climate, electric heat creates far more "Level 2-sized" hours than cars do. In a 5,700-home test slice, 48% of all 6+ kWh hours in non-EV homes happened below freezing. Looking only at 45–70°F hours removes that confusion.

### 3. Segments and peak behavior (`07`–`10`)
- **Exclusions:** vacant (<500 kWh/yr), non-residential (>40 MWh/yr), under half a year of data.
- **Seasonal:** 3+ months below 15% of the home's busiest month → *summer-vacant* or *winter-vacant*.
- **Segments:** seasonal first; then count EV + electric heat + solar: 2+ = **High-electrified**, 1 = **Single-tech**, 0 = **No tech**, split by AC type.
- **Co-adoption (lift):** how much more common tech B is in homes that have tech A, compared with all homes.
- **Peak:** the 20 highest system hours in Jun–Aug and in Dec–Feb. We compare each segment's share of customers with its share of each peak, and use a simple regression to estimate the kW each technology adds at the peak.

### 4. Demand flexibility and batteries (`11`–`13`)
- **Battery:** 2 × Enphase IQ 10C = 20.16 kWh / 7.68 kW, 89.4% round-trip (we also test 1 unit).
  - **Discharge:** covers the home's load 3–10 pm, starting with the 6–7 pm system peak.
  - **Recharge:** 11 pm–6 am at **≤3 kW** (the 3 kVA rule), never above the home's own 99th-percentile load, so recharging never creates a new household peak.
- **Size:** one unit unless the second adds ≥0.5 kW of peak relief.
- **Demand response** (no battery). The thermostat and setback shares are our assumptions:
  - smart thermostat = 40% of AC load at peak
  - managed charging = the EV's measured 1.0 kW (summer) / 0.8 kW (winter)
  - heating setback = 20% of heating load
- **Candidate flags:** persistent peak (top 20% kW at system peak), Level 2 EV (adds ~5.6 kW > 3 kVA), low headroom (home already ≥10 kW).
- **Tiers:**

| Tier | Rule | Offer |
|---|---|---|
| **Tier 2** | Any flag **and** battery relief ≥ 2 kW (summer + winter) | Battery + demand response |
| **Tier 2s** | Solar home | Solar-charged battery, export program, backup |
| **Tier 1** | Demand response would save ≥ 0.5 kW | Smart thermostat / managed charging / setback |
| **Tier 0** | Everyone else | Monitor; re-score yearly |

- **Value inputs:**
  - **Generation capacity:** NYISO rest-of-state, about $5/kW-month summer and $3/kW-month winter.
  - **Distribution capacity:** NYSEG 2025 marginal cost of service, $26.02/kW-yr system average and $70.61/kW-yr in capacity-constrained areas.
  - **Customer incentives:** NYSEG/RG&E Energy Storage Solutions pays $50/kW of event performance, and NYSERDA pays $200/kWh upfront (capped at $5,000).
  - **Battery cost:** about $1,116/kWh installed (national average).
  - **Retail rate:** about $0.22/kWh.

## Limitations
- EV and heat-pump labels are "likely" owners, not confirmed; heating and AC have no ground truth (physics rules).
- Solar exports appear as zero, so solar surplus and battery charging from solar can't be measured directly.
- Demand-response shares and capacity prices are assumptions; change them in `config.py`.
- ~1,400 customers are missing from the `_v2` data file.

## Sources
- NYSEG/RG&E Energy Storage Solutions: https://www.nyseg.com/energy-storage-solutions-program
- NYSERDA residential storage incentive: https://www.nyserda.ny.gov/All-Programs/Energy-Storage-Program
- NYSEG/RG&E 2025 Marginal Cost of Service Study: https://jointutilitiesofny.org/sites/default/files/NYSEG%20RGE%202025%20MCOS.pdf
- NYISO capacity prices (Modo Energy, 2026): https://modoenergy.com/research/nyiso-bess-may-2026-reference-price
- Battery cost (EnergySage): https://www.energysage.com/energy-storage/best-home-batteries/enphase-iq-battery-10c-review/
- PU learning: Elkan & Noto, KDD 2008; Bekker & Davis, *Machine Learning* 2020
- AC detection from smart meters: Chen, Sanders & Ban-Weiss, *Environ. Res. Lett.* 2019
- EV detection from hourly data: Hoffmann et al., CIRED 2019

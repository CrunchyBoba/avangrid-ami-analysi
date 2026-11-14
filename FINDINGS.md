# Findings: Who Drives Avangrid's Peak, and What to Offer Them

*Avangrid AMI Hackathon 2026 · 34,238 homes · hourly meter data, Sep 2025 – Aug 2026*

## The short version
The grid has **two peaks**. Summer is the biggest, and it is driven by air conditioning. Winter is driven by electric heat, and it grows as homes electrify. A small, data-picked group of homes causes much more than its share of each peak. The cheapest relief comes from **demand response** (smart thermostats, smarter EV charging). **Batteries pay off only when they are targeted**: at homes that would otherwise need a service upgrade, or on crowded parts of the grid.

## What we found

**1. Two peaks, two different causes.**
- The highest hour of the year was **July 2 at 6 pm (92°F)**, at 2.3 kW per home.
- The winter peak came on **cold Sunday evenings** (Jan 25 and Feb 8, 0–7°F, 5–8 pm), at 1.7 kW per home.
- Usage is lowest around 55°F and climbs in both directions.

**2. We can see the four big loads in the meter data.**
- **AC:** 69% of homes have it, 28% of them central AC.
- **Electric heat:** 5,226 homes (15%).
- **EVs:** about 744 homes, 598 of them with a Level 2 charger.
- **Solar:** 397 homes. Another 231 homes look like solar but are not on the list.

**3. A few groups make up most of each peak.**
- **Central AC homes (24% of homes) make up 40% of the summer peak.**
- **Electric-heat homes (13%) make up 31% of the winter peak.**
- What each technology adds at the peak:

  | Technology | Summer peak | Winter peak |
  |---|---|---|
  | Central AC | +2.9 kW | |
  | EV | +1.0 kW | +0.8 kW |
  | Electric heat | | +2.8 kW |

**4. "High-electrified" homes are the future, not today's problem.**
- There are 284 homes with two or more technologies (EV, electric heat, solar).
- Each one uses **4.6 kW at the winter peak**, about 3× a typical home. That is a preview of what electrification does to the grid.
- They are under 1% of homes, so they don't drive today's peak.

**5. Technologies come in bundles.**
- Solar homes are **about 7× more likely to have an EV**.
- In Avangrid's own lists, heat-pump homes are **17× more likely to have an EV**.
- So a home with one technology is the best place to look for the next one.

**6. Seasonal homes matter, especially in winter.**
- **1,083 homes empty out in summer** (likely student rentals). 62% of them have electric heat, and they use 3.1 kW at the winter peak but only 0.5 kW at the summer peak.
- **542 homes empty out in winter** (camps, lake houses).

**7. EV charging habits differ, and so does what they mean for the grid.**
- 241 EV homes charge on an overnight timer, which already helps the grid.
- **134 plug in when they get home (5–8 pm), right on the peak.**
- We saw 23 homes start charging during the year (new EVs). 70% of them have central AC.
- Of Avangrid's "likely EV" list, **130 homes barely charge at home** (median 6 sessions a year). What matters to the grid is home charging, and that is what we detect.

**8. Batteries work best when targeted, and they cover a lot of a home's evening.**
- We simulated a battery hour by hour for every home: 20.16 kWh, 7.68 kW, recharging at 3 kW or less to respect the 3 kVA rule.
- **The top 3% of homes** (about 1,000) each cut **2.7 kW at the summer peak and 3.3 kW at the winter peak**. That is **2.3× more than batteries placed at random**.
- Each of those batteries moves about 6,000 kWh a year out of the peak.

**9. The money: demand response is cheap, and batteries need a reason.**
- **Demand response:** across about 12,000 homes it delivers **27 MW of summer relief per 100,000 homes** at low cost.
- **Battery value per year:**
  - The grid gets **$225** of capacity value, or **$374 in crowded areas**.
  - The customer gets **$336** from Energy Storage Solutions event payments.
  - The customer loses about **$155** to battery losses on a flat rate.
- **Battery cost:** about **$22,500** installed, minus a **$4,032** NYSERDA rebate.
- Peak relief alone doesn't pay for a battery. Avoided upgrades and backup power have to carry the rest.

**10. EVs strain home service capacity.**
- Each of the 570 Level 2 chargers adds about **5.6 kW**, nearly double the ~3 kVA a 200-amp service should take.
- A 7.68 kW battery can cover a full charging session.

---

## Recommendations

**Offer the cheapest option that fixes each home's peak. Save batteries for homes where they avoid a grid upgrade.**

| Tier | Who (homes) | What to offer | Why |
|---|---|---|---|
| **Tier 1: Demand response** | 12,102: mostly AC homes, plus some electric heat and EV | Smart thermostat, managed EV charging, heating setback | 27 MW summer per 100k homes at low cost |
| **Tier 2: Battery + DR** | 6,820 candidates. **Start with the top ~1,000:** electric heat, central AC, high-electrified, Level 2 EV | 20.16 kWh battery (+ demand response), placed first on crowded feeders | 2.7 / 3.3 kW relief each, 2.3× better than random. Avoids service upgrades |
| **Tier 2s: Solar + battery** | 261 solar homes | Battery charged from solar, ESS export program, backup power | Little peak to shave, but free charging and resilience |
| **Tier 0: Monitor** | 14,130 low-impact homes | Nothing now; re-score every year | Small peak contribution |

**Messages by customer type:**

| Customer type | Message |
|---|---|
| **Central AC** | "Let your thermostat pre-cool and earn rewards." This is the summer peak. |
| **Electric heat** | Winter setback now. Heat pump + battery for the biggest users. This is the winter peak. |
| **EV, plugging in on arrival** | Move charging after 9 pm with managed charging (NYSEG OptimizEV). Leave timer chargers alone. |
| **Level 2 EV or next adopter** | "Add your EV or heat pump without a panel upgrade." A battery keeps added load under 3 kVA. |
| **Solar** | "Store your sunshine for the evening and keep the lights on in a storm." Lead with backup and ESS payments, not bill savings. |
| **Summer-vacant, electric heat** | Winter demand response (setback, smart thermostat). Skip summer programs. |
| **Funding** | Stack NYSERDA ($200/kWh), ESS ($50/kW-yr) and avoided distribution upgrades ($26–71/kW-yr) to make targeted batteries work. |

*Methods and code: see [README.md](README.md).*

# Data folder (not committed)

Put the raw files in `data/raw/`:

```
data/raw/
  2026 Avangrid Hackathon Data_1_10000/        part-*.csv
  2026 Avangrid Hackathon Data_10001_20000_v2/ part-*.csv
  2026 Avangrid Hackathon Data_20001_30000/    part-*.csv
  2026 Avangrid Hackathon Data_30001_35725/    part-*.csv
  Weather.xlsx   (or "Weather Data_Avangrid_Hackathon .xlsx")
  EV_Heat Pump_Solar PV Customers.xlsx
```

`python run_all.py` writes cleaned data to `data/clean/`. Both folders are ignored by git
because the data is confidential customer data and far larger than GitHub allows.

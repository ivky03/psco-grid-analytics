# PSCo Hourly Demand Analysis

**Source repository:** https://github.com/ivky03/psco-grid-analytics

An independent portfolio case study using public U.S. Energy Information Administration (EIA) Form 930 bulk data. It demonstrates a practical Python ingestion pipeline, SQL-backed analysis in SQLite, data quality checks, a simple chronological forecasting evaluation, and a small interactive dashboard.

**This project is not affiliated with or endorsed by Xcel Energy.** The source series is PSCo (Public Service Company of Colorado) balancing-authority data as published by EIA. It is not customer-level usage or a complete measure of all retail electricity activity.

## Business question

What do PSCo's hourly reported demand and day-ahead forecast data show about demand patterns, data quality, and forecast error, and how does a simple one-hour model compare with persistence baselines?

## Run it

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.pipeline --mode real
streamlit run dashboard.py
```

The default real run downloads the two public 2025 EIA bulk CSVs into `data/raw/`. No EIA API key is required. To show multi-year, large-source ingestion, select a broader period; for example, this reads seven years of all-balancing-authority source data and retains the PSCO rows:

```bash
python -m src.pipeline --mode real --start-year 2019 --end-year 2025
```

Each year is split into two public six-month files. The ingestion scans all balancing-authority records in 50,000-row chunks, selects PSCO, records source filenames, input bytes, rows scanned and PSCO rows retained in `outputs/results.json`, then stores the PSCO extract in `data/processed/grid.sqlite`. This makes the scale claim measurable: report the actual `source_rows_scanned` and `source_bytes` from your run, not just the size of the final PSCO table. The generated database and CSVs are ignored by Git because they are reproducible data products.

For an offline smoke test and dashboard preview, run:

```bash
python -m src.pipeline --mode demo
streamlit run dashboard.py
```

Demo mode is deterministic synthetic data. The app and outputs label it as synthetic; never describe demo outputs as EIA findings.

## What's included

- `src/pipeline.py`: public-file download, bounded-memory ingestion, PSCO selection, quality checks, SQLite storage, chronological model evaluation, and report outputs.
- `sql/`: runnable SQL for quality, peak hours, hourly profile, monthly profile, and EIA day-ahead forecast error.
- `dashboard.py`: a focused demand and forecast dashboard reading pipeline outputs.
- `tests/`: offline pipeline and SQL smoke tests.
- `reports/xcel_associate_data_scientist_case_study.pdf`: concise application work sample.

## Analysis and interpretation

The pipeline retains the raw demand field and sets nonpositive demand to null for analysis. It does not silently replace an invalid measurement. SQL analyses are run against the SQLite table and exported to `outputs/` as CSV files.

Forecasting uses a time-ordered 80/20 split. At each held-out hour, the model uses hour, weekday, month, demand through the prior hour, the same hour one day earlier, and a trailing 24-hour mean. It is a **rolling one-hour-ahead** evaluation: each scored hour may use actual demand from the immediately preceding hour. The baselines are previous-hour persistence and previous-day-same-hour demand.

EIA's supplied forecast is day-ahead. Its error is reported separately and must not be treated as a direct comparison to the one-hour model. On the shared 2019-2025 run, gradient boosting's MAE was 103.72 MW, compared with 181.26 MW for previous-hour persistence and 343.59 MW for the previous-day baseline. Its RMSE was 146.03 MW, compared with 230.17 MW and 455.42 MW, respectively. These are encouraging results on one held-out period, not proof of operational superiority; further rolling-origin validation would be needed.

## Data quality and limits

The shared 2019-2025 run scanned 3,848,038 source rows across 14 files (616,148,473 bytes) and retained 61,368 PSCo hourly records. It had no duplicate timestamps or missing hour slots; 24 demand values were missing and 13 were nonpositive, so 37 observations were excluded from demand analysis. The raw demand field remains available for review. This is a multi-million-row chunked processing demonstration, not a claim of petabyte-scale computing. The pipeline records exact counts for each local run in `outputs/results.json`.

The source timestamps are UTC end-of-hour timestamps; daylight-saving localization is not applied. This is a compact portfolio analysis, not a production grid-operations tool. It does not analyze generation mix, customer usage, weather, causal impacts, or operational dispatch decisions. Forecast results depend on the supplied data and evaluation window.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests use synthetic data only and do not require network access.

## Source and attribution

EIA, **Form EIA-930, Hourly and Daily Balancing Authority Operations Report**, public bulk CSV files: <https://www.eia.gov/electricity/gridmonitor/>. The data are public government statistics; cite EIA and the Form 930 source when reusing derived figures.

Portfolio: <https://portfolio-website-vignesh--kvk1011.replit.app/>

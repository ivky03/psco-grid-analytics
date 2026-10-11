"""Small, reproducible EIA-930 PSCo demand analytics pipeline."""
from __future__ import annotations

import argparse
import json
import sqlite3
from urllib.request import urlopen
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "outputs"
DB_PATH = ROOT / "data" / "processed" / "grid.sqlite"
BASE_URL = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles"
FIRST_AVAILABLE_YEAR = 2015


def source_files(start_year: int = 2025, end_year: int = 2025) -> tuple[str, ...]:
    """Return the public six-month EIA bulk files for an inclusive year range."""
    if start_year < FIRST_AVAILABLE_YEAR or end_year < start_year:
        raise ValueError(f"Choose years from {FIRST_AVAILABLE_YEAR} onward with end_year >= start_year")
    return tuple(
        f"EIA930_BALANCE_{year}_{half}.csv"
        for year in range(start_year, end_year + 1)
        for half in ("Jan_Jun", "Jul_Dec")
    )


def download_sources(raw_dir: Path = RAW_DIR, start_year: int = 2025,
                     end_year: int = 2025) -> list[Path]:
    """Download public bulk CSVs once; no API key is required."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in source_files(start_year, end_year):
        path = raw_dir / name
        if not path.exists():
            partial = path.with_suffix(path.suffix + ".part")
            try:
                with urlopen(f"{BASE_URL}/{name}", timeout=120) as response:
                    with partial.open("wb") as target:
                        while block := response.read(1024 * 1024):
                            target.write(block)
                partial.replace(path)
            finally:
                partial.unlink(missing_ok=True)
        paths.append(path)
    return paths


def load_psco(paths: list[Path], chunksize: int = 50_000) -> tuple[pd.DataFrame, dict]:
    """Scan EIA's multi-BA files in chunks and retain PSCO demand fields only."""
    usecols = ["Balancing Authority", "UTC Time at End of Hour", "Demand (MW)", "Demand Forecast (MW)"]
    frames, scanned_rows, source_bytes = [], 0, 0
    for path in paths:
        source_bytes += path.stat().st_size
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize, dtype=str, encoding="utf-8-sig"):
            scanned_rows += len(chunk)
            rows = chunk.loc[chunk["Balancing Authority"].str.strip().eq("PSCO"), usecols[1:]].copy()
            if not rows.empty:
                frames.append(rows)
    if not frames:
        raise ValueError("No PSCO rows found in the EIA bulk files")
    df = pd.concat(frames, ignore_index=True).rename(columns={
        "UTC Time at End of Hour": "timestamp",
        "Demand (MW)": "demand_mw_raw",
        "Demand Forecast (MW)": "forecast_mw",
    })
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True, errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError("Could not parse one or more PSCO UTC timestamps")
    for name in ("demand_mw_raw", "forecast_mw"):
        df[name] = pd.to_numeric(df[name].str.replace(",", "", regex=False), errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)
    if df["timestamp"].duplicated().any():
        raise ValueError("Duplicate PSCO timestamps found; inspect source before analysis")
    df["demand_mw"] = df["demand_mw_raw"].where(df["demand_mw_raw"] > 0)
    df["source"] = "EIA-930 public bulk CSV / PSCO"
    df["is_synthetic"] = False
    ingest = {"source_files": [p.name for p in paths], "source_bytes": source_bytes,
              "source_rows_scanned": scanned_rows, "psco_rows_selected": int(len(df)),
              "chunk_size_rows": 50_000}
    return df, ingest


def fixture(hours: int = 24 * 120) -> pd.DataFrame:
    """Deterministic synthetic data, used only for tests and demo mode."""
    ts = pd.date_range("2025-01-01", periods=hours, freq="h", tz="UTC")
    rng = np.random.default_rng(42)
    hour, weekday = ts.hour.to_numpy(), ts.dayofweek.to_numpy()
    demand = 4200 + 850 * np.sin((hour - 8) * np.pi / 12) + 320 * (weekday < 5) + rng.normal(0, 145, hours)
    df = pd.DataFrame({"timestamp": ts, "demand_mw_raw": demand.round(2),
                       "demand_mw": demand.round(2), "forecast_mw": (demand + rng.normal(0, 210, hours)).round(2),
                       "source": "SYNTHETIC TEST DATA", "is_synthetic": True})
    return df


def quality_report(df: pd.DataFrame) -> dict:
    ts = pd.DatetimeIndex(pd.to_datetime(df["timestamp"], utc=True))
    raw = pd.to_numeric(df["demand_mw_raw"], errors="coerce")
    return {"rows": int(len(df)), "duplicate_timestamps": int(ts.duplicated().sum()),
            "missing_demand_raw": int(raw.isna().sum()),
            "nonpositive_demand_raw": int((raw.notna() & (raw <= 0)).sum()),
            "missing_hour_slots": int(len(pd.date_range(ts.min(), ts.max(), freq="h").difference(ts))),
            "analysis_demand_rows_excluded": int(df["demand_mw"].isna().sum())}


def evaluate(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """One-hour-ahead holdout; compare ML to persistence and prior-day baselines."""
    f = df.copy().sort_values("timestamp")
    ts = pd.to_datetime(f["timestamp"], utc=True)
    f["hour"], f["weekday"], f["month"] = ts.dt.hour, ts.dt.dayofweek, ts.dt.month
    f = f.set_index("timestamp").asfreq("h")
    f["lag_1"] = f["demand_mw"].shift(1)
    f["lag_24"] = f["demand_mw"].shift(24)
    f["rolling_24"] = f["demand_mw"].shift(1).rolling(24, min_periods=24).mean()
    f = f.reset_index()
    features = ["hour", "weekday", "month", "lag_1", "lag_24", "rolling_24"]
    f = f.dropna(subset=features + ["demand_mw"])
    if len(f) < 200:
        raise ValueError("Need at least 200 complete hourly observations")
    cut = int(len(f) * 0.8)
    train, test = f.iloc[:cut], f.iloc[cut:]
    model = HistGradientBoostingRegressor(max_iter=100, max_leaf_nodes=15, random_state=42)
    model.fit(train[features], train["demand_mw"])
    has_eia = test["forecast_mw"].notna().any()
    scored = test.dropna(subset=["forecast_mw"]) if has_eia else test
    actual = scored["demand_mw"]
    predictions = {"lag_1_persistence_1h": scored["lag_1"],
                   "lag_24_same_hour_1h": scored["lag_24"],
                   "gradient_boosting_1h": model.predict(scored[features])}
    if has_eia:
        predictions["eia_day_ahead_different_horizon"] = scored["forecast_mw"]
    metrics = {name: {"mae_mw": round(float(mean_absolute_error(actual, pred)), 2),
                      "rmse_mw": round(float(np.sqrt(mean_squared_error(actual, pred))), 2),
                      "rows": int(len(scored))} for name, pred in predictions.items()}
    out = pd.DataFrame({"timestamp": scored["timestamp"], "actual_mw": actual,
                        "lag_1_mw": scored["lag_1"], "lag_24_mw": scored["lag_24"],
                        "model_mw": predictions["gradient_boosting_1h"]})
    if has_eia:
        out["eia_day_ahead_mw"] = scored["forecast_mw"].to_numpy()
    return metrics, out


def run_sql_analyses(db_path: Path, sql_dir: Path = ROOT / "sql") -> dict:
    results = {}
    with sqlite3.connect(db_path) as con:
        for path in sorted(sql_dir.glob("*.sql")):
            # Each file contains one SELECT; named results remain reviewable in SQL.
            results[path.stem] = pd.read_sql_query(path.read_text(), con).to_dict(orient="records")
    return results


def run(mode: str = "real", raw_dir: Path = RAW_DIR, db_path: Path = DB_PATH,
        out_dir: Path = OUT_DIR, start_year: int = 2025, end_year: int = 2025) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "demo":
        df, ingest = fixture(), {"source_files": [], "source_bytes": 0,
                                 "source_rows_scanned": 0, "psco_rows_selected": 0,
                                 "chunk_size_rows": 50_000}
        # Demo still exercises quality handling without misrepresenting data as real.
        df.loc[100, "demand_mw_raw"] = -1359
        df.loc[100, "demand_mw"] = np.nan
    else:
        df, ingest = load_psco(download_sources(raw_dir, start_year, end_year))
    quality = quality_report(df)
    with sqlite3.connect(db_path) as con:
        df.assign(timestamp=pd.to_datetime(df.timestamp, utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")) \
          .to_sql("grid_operations", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS idx_grid_timestamp ON grid_operations(timestamp)")
    metrics, pred = evaluate(df)
    pred.to_csv(out_dir / "predictions.csv", index=False)
    analyses = run_sql_analyses(db_path)
    result = {"mode": mode, "source": str(df.source.iloc[0]), "ingestion": ingest,
              "quality": quality, "start_utc": str(df.timestamp.min()),
              "end_utc": str(df.timestamp.max()), "metrics": metrics,
              "sql_analyses": analyses,
              "note": "One-hour model and persistence baselines; EIA forecast is day-ahead and not directly comparable."}
    (out_dir / "results.json").write_text(json.dumps(result, indent=2, default=str))
    # Convenient analysis extracts for spreadsheet review.
    for name, rows in analyses.items():
        pd.DataFrame(rows).to_csv(out_dir / f"{name}.csv", index=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("real", "demo"), default="real")
    parser.add_argument("--start-year", type=int, default=2025,
                        help="First year of EIA bulk files (default: 2025)")
    parser.add_argument("--end-year", type=int, default=2025,
                        help="Last year of EIA bulk files, inclusive (default: 2025)")
    args = parser.parse_args()
    print(json.dumps(run(args.mode, start_year=args.start_year, end_year=args.end_year), indent=2, default=str))

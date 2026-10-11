"""Compact Streamlit dashboard for the PSCo analysis outputs."""
import json
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "processed" / "grid.sqlite"
RESULTS = ROOT / "outputs" / "results.json"
PRED = ROOT / "outputs" / "predictions.csv"

st.set_page_config(page_title="PSCo Demand Analysis", page_icon="⚡", layout="wide")
st.title("PSCo | Hourly Demand Analysis")
st.caption("Independent analysis of EIA-930 public data. Not affiliated with Xcel Energy.")

if not (DB.exists() and RESULTS.exists()):
    st.info("Run `python -m src.pipeline --mode real` first. Use `--mode demo` for an offline synthetic preview.")
    st.stop()

result = json.loads(RESULTS.read_text())
with sqlite3.connect(DB) as con:
    data = pd.read_sql_query("SELECT * FROM grid_operations ORDER BY timestamp", con,
                             parse_dates=["timestamp"])
pred = pd.read_csv(PRED, parse_dates=["timestamp"])
if result["mode"] == "demo":
    st.warning("Synthetic test data is displayed. These charts are not real PSCo findings.")

valid = data.dropna(subset=["demand_mw"]).copy()
valid["timestamp"] = pd.to_datetime(valid["timestamp"], utc=True)
valid["month"] = valid.timestamp.dt.strftime("%b %Y")
valid["utc_hour"] = valid.timestamp.dt.hour
peak = valid.loc[valid.demand_mw.idxmax()]
mae = result["metrics"]["gradient_boosting_1h"]["mae_mw"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Valid demand hours", f"{len(valid):,}", f"{result['quality']['analysis_demand_rows_excluded']} excluded")
c2.metric("Peak reported demand", f"{peak.demand_mw:,.0f} MW", peak.timestamp.strftime("%b %d, %H:%M UTC"))
c3.metric("Average demand", f"{valid.demand_mw.mean():,.0f} MW")
c4.metric("Model one-hour MAE", f"{mae:,.1f} MW")

st.subheader("Reported hourly demand")
daily = valid.set_index("timestamp").resample("D").agg(demand_mw=("demand_mw", "mean")).reset_index()
st.plotly_chart(px.line(daily, x="timestamp", y="demand_mw", labels={"timestamp": "UTC date", "demand_mw": "Daily mean demand (MW)"},
                        template="plotly_white"), use_container_width=True)

left, right = st.columns(2)
with left:
    hourly = valid.groupby("utc_hour", as_index=False).demand_mw.mean()
    st.plotly_chart(px.bar(hourly, x="utc_hour", y="demand_mw", labels={"utc_hour": "Hour (UTC)", "demand_mw": "Mean demand (MW)"},
                           title="Average demand by UTC hour", template="plotly_white"), use_container_width=True)
with right:
    monthly = valid.groupby("month", as_index=False).agg(demand_mw=("demand_mw", "mean"), timestamp=("timestamp", "min")).sort_values("timestamp")
    st.plotly_chart(px.bar(monthly, x="month", y="demand_mw", labels={"month": "Month (UTC)", "demand_mw": "Mean demand (MW)"},
                           title="Average demand by month", template="plotly_white"), use_container_width=True)

st.subheader("Forecast evaluation")
st.caption("Chronological holdout, rolling one-hour-ahead test. EIA's day-ahead forecast has a different horizon and is listed separately.")
metrics = result["metrics"]
rows = [{"Comparison": name.replace("_", " "), "MAE (MW)": v["mae_mw"], "RMSE (MW)": v["rmse_mw"], "Scored hours": v["rows"]}
        for name, v in metrics.items()]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
fig = px.line(pred, x="timestamp", y=[c for c in ["actual_mw", "lag_1_mw", "model_mw"] if c in pred],
              labels={"timestamp": "UTC timestamp", "value": "Demand (MW)", "variable": "Series"}, template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

with st.expander("SQL findings and data-quality checks"):
    st.write("SQL scripts in `sql/` generate the detailed outputs below.")
    analyses = result["sql_analyses"]
    st.write("Top reported demand hours")
    st.dataframe(pd.DataFrame(analyses["02_peak_hours"]), hide_index=True, use_container_width=True)
    st.write("Monthly demand summary")
    st.dataframe(pd.DataFrame(analyses["04_monthly_demand"]), hide_index=True, use_container_width=True)
    st.json({"ingestion": result["ingestion"], "quality": result["quality"]})

st.caption("Source: U.S. EIA Form 930 public bulk files. Demand is balancing-authority reported demand, not customer-level usage.")

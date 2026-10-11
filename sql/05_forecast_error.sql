SELECT
  substr(timestamp, 1, 7) AS utc_month,
  ROUND(AVG(ABS(demand_mw - forecast_mw)), 1) AS eia_day_ahead_mae_mw,
  ROUND(SQRT(AVG((demand_mw - forecast_mw) * (demand_mw - forecast_mw))), 1) AS eia_day_ahead_rmse_mw,
  COUNT(*) AS observed_forecast_pairs
FROM grid_operations
WHERE demand_mw IS NOT NULL AND forecast_mw IS NOT NULL
GROUP BY utc_month
ORDER BY utc_month;

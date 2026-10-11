SELECT
  COUNT(*) AS psco_hourly_rows,
  COUNT(DISTINCT timestamp) AS distinct_timestamps,
  SUM(CASE WHEN demand_mw_raw <= 0 THEN 1 ELSE 0 END) AS nonpositive_raw_demand_rows,
  SUM(CASE WHEN demand_mw IS NULL THEN 1 ELSE 0 END) AS demand_rows_excluded,
  SUM(CASE WHEN forecast_mw IS NULL THEN 1 ELSE 0 END) AS missing_day_ahead_forecasts,
  MIN(timestamp) AS first_utc_hour,
  MAX(timestamp) AS last_utc_hour
FROM grid_operations;

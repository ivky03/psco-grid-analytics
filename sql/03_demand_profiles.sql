SELECT
  CAST(substr(timestamp, 12, 2) AS INTEGER) AS utc_hour,
  ROUND(AVG(demand_mw), 1) AS average_demand_mw,
  ROUND(MAX(demand_mw), 1) AS peak_demand_mw,
  COUNT(demand_mw) AS observed_hours
FROM grid_operations
WHERE demand_mw IS NOT NULL
GROUP BY utc_hour
ORDER BY utc_hour;

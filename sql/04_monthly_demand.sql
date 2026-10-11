SELECT
  substr(timestamp, 1, 7) AS utc_month,
  ROUND(AVG(demand_mw), 1) AS average_demand_mw,
  ROUND(MAX(demand_mw), 1) AS peak_demand_mw,
  COUNT(demand_mw) AS observed_hours
FROM grid_operations
WHERE demand_mw IS NOT NULL
GROUP BY utc_month
ORDER BY utc_month;

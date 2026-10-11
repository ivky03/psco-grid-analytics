SELECT timestamp, demand_mw
FROM grid_operations
WHERE demand_mw IS NOT NULL
ORDER BY demand_mw DESC
LIMIT 10;

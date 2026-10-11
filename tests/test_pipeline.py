import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.pipeline import fixture, load_psco, quality_report, run, source_files


class PipelineTests(unittest.TestCase):
    def test_source_file_range_covers_inclusive_years(self):
        self.assertEqual(source_files(2024, 2025), (
            "EIA930_BALANCE_2024_Jan_Jun.csv", "EIA930_BALANCE_2024_Jul_Dec.csv",
            "EIA930_BALANCE_2025_Jan_Jun.csv", "EIA930_BALANCE_2025_Jul_Dec.csv",
        ))
        with self.assertRaises(ValueError):
            source_files(2026, 2025)

    def test_demo_runs_and_sql_outputs_are_populated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run("demo", raw_dir=root / "raw", db_path=root / "grid.sqlite",
                         out_dir=root / "outputs")
            self.assertEqual(result["quality"]["rows"], 2880)
            self.assertEqual(result["quality"]["nonpositive_demand_raw"], 1)
            self.assertEqual(result["quality"]["analysis_demand_rows_excluded"], 1)
            self.assertEqual(len(result["sql_analyses"]["03_demand_profiles"]), 24)
            self.assertIn("gradient_boosting_1h", result["metrics"])
            self.assertTrue((root / "outputs" / "predictions.csv").exists())

    def test_fixture_is_explicitly_synthetic(self):
        df = fixture(240)
        self.assertTrue(df["is_synthetic"].all())
        self.assertEqual(quality_report(df)["rows"], 240)

    def test_chunked_loader_filters_balancing_authority_and_tracks_volume(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.csv"
            # CSV fixtures include thousands separators enclosed in quotes.
            path.write_text(
                'Balancing Authority,UTC Time at End of Hour,Demand (MW),Demand Forecast (MW)\n'
                'PSCO,01/01/2025 1:00:00 AM,"4,100","4,200"\n'
                'OTHER,01/01/2025 1:00:00 AM,"9,000","9,100"\n'
                'PSCO,01/01/2025 2:00:00 AM,-1,"4,100"\n'
            )
            df, ingest = load_psco([path], chunksize=2)
            self.assertEqual(ingest["source_rows_scanned"], 3)
            self.assertEqual(ingest["psco_rows_selected"], 2)
            self.assertEqual(df.loc[0, "demand_mw"], 4100)
            self.assertTrue(pd.isna(df.loc[1, "demand_mw"]))


if __name__ == "__main__":
    unittest.main()

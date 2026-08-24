from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from etl.api_transform import RECENT_PRICE_SNAPSHOT_COLUMNS
from etl.api_extract import KamisApiError
from etl.pipeline import run_pipeline, write_csv


class PipelineTests(unittest.TestCase):
    def test_run_pipeline_rejects_empty_kamis_data(self):
        response = {"body": {"items": {"item": []}}}
        with patch("etl.pipeline.fetch_recent_kamis_prices", return_value=response), \
            patch("etl.pipeline.ensure_schema") as ensure_schema:
            with self.assertRaisesRegex(
                KamisApiError,
                "KAMIS API returned no valid price rows",
            ):
                run_pipeline()

        ensure_schema.assert_not_called()

    def test_write_csv_preserves_bom_header_and_empty_output(self):
        with TemporaryDirectory() as temp_dir:
            output = write_csv(
                [], RECENT_PRICE_SNAPSHOT_COLUMNS, Path(temp_dir), "recent_price_snapshot.csv"
            )

            self.assertTrue(output.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertEqual(
                output.read_text(encoding="utf-8-sig").splitlines()[0],
                ",".join(RECENT_PRICE_SNAPSHOT_COLUMNS),
            )

    def test_run_pipeline_processes_only_kamis_outputs(self):
        response = {"body": {"items": {"item": [{
            "exmn_ymd": "20260821", "se_cd": "01", "se_nm": "소매",
            "ctgry_cd": "200", "ctgry_nm": "채소류", "item_cd": "211", "item_nm": "배추",
            "vrty_cd": "01", "vrty_nm": "여름", "grd_cd": "04", "grd_nm": "상품",
            "unit": "포기", "unit_sz": "1", "exmn_dd_prc": "3450",
        }]}}}
        with TemporaryDirectory() as temp_dir, \
            patch("etl.pipeline.API_OUTPUT_DIR", Path(temp_dir)), \
            patch("etl.pipeline.fetch_recent_kamis_prices", return_value=response), \
            patch("etl.pipeline.ensure_schema"), \
            patch("etl.pipeline.load_kamis_outputs", return_value={"snapshots_written": 1}):
            summary = run_pipeline()

        self.assertEqual(summary["recent_price_snapshot_rows"], 1)
        self.assertEqual(summary["category_rows"], 1)
        self.assertEqual(
            set(summary["outputs"]),
            {"recent_price_snapshot_csv", "category_csv", "product_csv", "product_variant_csv", "grade_csv"},
        )
        self.assertEqual(summary["load_summary"], {"snapshots_written": 1})


if __name__ == "__main__":
    unittest.main()

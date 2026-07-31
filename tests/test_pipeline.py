from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
from unittest.mock import patch

import pandas as pd

from etl.pipeline import apply_week_metadata, infer_week_metadata, run_pipeline


class PipelineTests(unittest.TestCase):
    def test_infer_week_metadata_uses_file_mtime(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.xlsx"
            path.write_text("x", encoding="utf-8")
            ts = datetime(2026, 7, 28, 9, 0, 0).timestamp()
            path.touch()
            os.utime(path, (ts, ts))

            result = infer_week_metadata(path)

            self.assertEqual(result["start_date"], "2026-07-27")
            self.assertEqual(result["end_date"], "2026-08-02")
            self.assertEqual(result["week_no"], 31)
            self.assertEqual(result["year"], 2026)
            self.assertEqual(result["month"], 7)

    def test_infer_week_metadata_prefers_file_name_range(self):
        path = Path("weekly__2025.09.04~2025.09.10.xlsx")
        result = infer_week_metadata(path)
        self.assertEqual(result["start_date"], "2025-09-04")
        self.assertEqual(result["end_date"], "2025-09-10")
        self.assertEqual(result["year"], 2025)
        self.assertEqual(result["month"], 9)

    def test_infer_week_metadata_can_use_header_range(self):
        path = Path("weekly.xlsx")
        frame = pd.DataFrame([["품목", "단위", "지난주(09.04~09.10)", "이번주(09.11~09.17)", "등락률(%)"]])
        result = infer_week_metadata(path, frame)
        self.assertEqual(result["start_date"], "2026-09-04")
        self.assertEqual(result["end_date"], "2026-09-10")

    def test_apply_week_metadata_appends_columns(self):
        frame = pd.DataFrame([[1]], columns=["value"])
        result = apply_week_metadata(frame, {"week_no": 31, "year": 2026, "month": 7})

        self.assertEqual(result.loc[0, "week_no"], 31)
        self.assertEqual(result.loc[0, "year"], 2026)
        self.assertEqual(result.loc[0, "month"], 7)

    def test_apply_week_metadata_preserves_pdf_derived_dates(self):
        frame = pd.DataFrame(
            [["파프리카", "2025-09-04", "2025-09-10", 36, 2025, 9]],
            columns=["item_name", "start_date", "end_date", "week_no", "year", "month"],
        )
        result = apply_week_metadata(
            frame,
            {"start_date": "2025-09-01", "end_date": "2025-09-07", "week_no": 35, "year": 2025, "month": 9},
        )

        self.assertEqual(result.loc[0, "start_date"], "2025-09-04")
        self.assertEqual(result.loc[0, "end_date"], "2025-09-10")
        self.assertEqual(result.loc[0, "week_no"], 36)

    def test_run_pipeline_can_skip_pdf_reports(self):
        with TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir)
            workbook = raw_dir / "weekly.xlsx"
            pd.DataFrame([["배추", "1포기", "1,000", "1,200", "20.0%"]]).to_excel(workbook, index=False, header=False)

            with patch("etl.pipeline.collect_report_files", return_value=[raw_dir / "report.pdf"]), \
                patch("etl.pipeline.ensure_schema"), \
                patch("etl.pipeline.load_pipeline_outputs", return_value={}), \
                patch("etl.pipeline.parse_weekly_report") as parse_weekly_report, \
                patch("etl.pipeline.parse_price_tables_from_pdf") as parse_price_tables_from_pdf:
                summary = run_pipeline(raw_dir=raw_dir, skip_pdfs=True)

            self.assertEqual(summary["reports_detected"], 0)
            self.assertEqual(summary["weekly_report_rows"], 0)
            self.assertEqual(parse_weekly_report.call_count, 0)
            self.assertEqual(parse_price_tables_from_pdf.call_count, 0)


if __name__ == "__main__":
    unittest.main()

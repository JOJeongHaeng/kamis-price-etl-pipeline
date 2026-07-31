from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unittest

from etl.extract import collect_report_files, collect_spreadsheet_files


class ExtractTests(unittest.TestCase):
    def test_collect_spreadsheet_files_finds_unzipped_excel(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_dir = root / "raw"
            extracted_dir = root / "extracted"
            raw_dir.mkdir()
            extracted_dir.mkdir()

            excel_path = raw_dir / "prices.xlsx"
            excel_path.write_bytes(b"placeholder")

            result = collect_spreadsheet_files(raw_dir, extracted_dir)
            self.assertIn(excel_path, result)

    def test_collect_spreadsheet_files_extracts_zip_archives(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_dir = root / "raw"
            extracted_dir = root / "extracted"
            raw_dir.mkdir()
            extracted_dir.mkdir()

            archive_path = raw_dir / "prices.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("nested/weekly.xlsx", b"placeholder")

            result = collect_spreadsheet_files(raw_dir, extracted_dir)
            self.assertTrue(any(path.name == "weekly.xlsx" for path in result))

    def test_collect_report_files_finds_pdf_inside_zip(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_dir = root / "raw"
            extracted_dir = root / "extracted"
            raw_dir.mkdir()
            extracted_dir.mkdir()

            archive_path = raw_dir / "reports.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("nested/report.pdf", b"pdf")

            result = collect_report_files(raw_dir, extracted_dir)
            self.assertTrue(any(path.name == "report.pdf" for path in result))


if __name__ == "__main__":
    unittest.main()

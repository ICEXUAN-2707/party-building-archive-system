from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from apps.imports import error_codes
from apps.imports.parser import parse_workbook
from scripts.generate_acceptance_excel import BRANCHES, generate_acceptance_dataset


class AcceptanceDatasetTests(SimpleTestCase):
    def test_main_dataset_has_1500_confirmable_rows_across_nine_branches(self) -> None:
        with TemporaryDirectory() as temporary:
            dataset = generate_acceptance_dataset(Path(temporary))
            result = parse_workbook(Path(dataset.first_workbook))
        self.assertEqual(dataset.student_count, 1500)
        self.assertEqual(dataset.warning_rows, 15)
        self.assertEqual(result.total_sheets, len(BRANCHES))
        self.assertEqual(result.success_sheets, len(BRANCHES))
        self.assertEqual(result.failed_sheets, 0)
        self.assertEqual(result.total_rows, 1500)
        self.assertEqual(result.success_rows, 1500)
        self.assertEqual(result.skipped_rows, 0)
        self.assertEqual(result.warning_rows, 15)
        self.assertEqual(len({row.student_number for row in result.valid_rows}), 1500)

    def test_seed_produces_byte_identical_workbooks(self) -> None:
        with TemporaryDirectory() as first, TemporaryDirectory() as second:
            first_set = generate_acceptance_dataset(Path(first), student_count=45, seed=17)
            second_set = generate_acceptance_dataset(Path(second), student_count=45, seed=17)
            first_hash = hashlib.sha256(Path(first_set.first_workbook).read_bytes()).hexdigest()
            second_hash = hashlib.sha256(Path(second_set.first_workbook).read_bytes()).hexdigest()
        self.assertEqual(first_hash, second_hash)

    def test_negative_workbooks_cover_errors_unknown_sheet_and_duplicate_conflict(self) -> None:
        with TemporaryDirectory() as temporary:
            dataset = generate_acceptance_dataset(Path(temporary), student_count=45)
            invalid = parse_workbook(Path(dataset.invalid_workbook))
            duplicate = parse_workbook(Path(dataset.duplicate_workbook))
        invalid_codes = {error.code for error in invalid.errors}
        self.assertIn(error_codes.ERROR_ROW_INVALID_STAGE, invalid_codes)
        self.assertIn(error_codes.ERROR_ROW_INVALID_APPLIED_DATE, invalid_codes)
        self.assertIn(error_codes.ERROR_ROW_MISSING_REQUIRED, invalid_codes)
        self.assertIn(error_codes.ERROR_UNKNOWN_SHEET, invalid_codes)
        self.assertIn(error_codes.ERROR_HEADER_NOT_FOUND, invalid_codes)
        numbers = [row.student_number for row in duplicate.valid_rows]
        self.assertEqual(len(numbers), 2)
        self.assertEqual(len(set(numbers)), 1)

    def test_second_workbook_changes_business_values_without_changing_identities(self) -> None:
        with TemporaryDirectory() as temporary:
            dataset = generate_acceptance_dataset(Path(temporary), student_count=45)
            first = parse_workbook(Path(dataset.first_workbook))
            second = parse_workbook(Path(dataset.second_workbook))
        first_by_number = {row.student_number: row for row in first.valid_rows}
        second_by_number = {row.student_number: row for row in second.valid_rows}
        self.assertEqual(first_by_number.keys(), second_by_number.keys())
        sample_number = sorted(first_by_number)[0]
        self.assertNotEqual(
            first_by_number[sample_number].position,
            second_by_number[sample_number].position,
        )
        self.assertNotEqual(
            first_by_number[sample_number].report_items[0].submitted_at,
            second_by_number[sample_number].report_items[0].submitted_at,
        )

from django.test import SimpleTestCase

from apps.imports.parser import (
    ERROR_HEADER_NOT_FOUND,
    ColumnMapping,
    HeaderParseResult,
    ReportColumn,
    parse_header_row,
)


class ParseHeaderRowStandardOrderTests(SimpleTestCase):
    def test_standard_column_order(self) -> None:
        header = [
            "学号",
            "姓名",
            "发展阶段",
            "职务",
            "申请入党时间",
            "思想汇报总篇数",
            "第1次思想汇报",
            "第2次思想汇报",
            "第3次思想汇报",
        ]
        result = parse_header_row(header)

        self.assertIsInstance(result, HeaderParseResult)
        self.assertIsInstance(result.mapping, ColumnMapping)
        self.assertTrue(result.ok)
        self.assertIsNone(result.error_code)
        self.assertIsNone(result.error_message)

        m = result.mapping
        self.assertEqual(m.student_number_col, 0)
        self.assertEqual(m.name_col, 1)
        self.assertEqual(m.development_stage_col, 2)
        self.assertEqual(m.position_col, 3)
        self.assertEqual(m.applied_at_col, 4)
        self.assertEqual(m.reported_total_count_col, 5)

        report_seqs = [(r.sequence_number, r.column_index) for r in m.report_columns]
        self.assertEqual(report_seqs, [(1, 6), (2, 7), (3, 8)])
        self.assertEqual(m.report_columns[0].source_column_name, "第1次思想汇报")


class ParseHeaderRowReorderedTests(SimpleTestCase):
    def test_columns_in_reversed_order_still_map_correctly(self) -> None:
        header = [
            "第1次思想汇报",
            "思想汇报总篇数",
            "职务",
            "申请入党时间",
            "发展阶段",
            "姓名",
            "学号",
            "第2次思想汇报",
        ]
        result = parse_header_row(header)

        self.assertTrue(result.ok)
        m = result.mapping
        self.assertEqual(m.name_col, 5)
        self.assertEqual(m.student_number_col, 6)
        self.assertEqual(m.development_stage_col, 4)
        self.assertEqual(m.position_col, 2)
        self.assertEqual(m.applied_at_col, 3)
        self.assertEqual(m.reported_total_count_col, 1)

        self.assertEqual(len(m.report_columns), 2)
        by_seq = {r.sequence_number: r.column_index for r in m.report_columns}
        self.assertEqual(by_seq[1], 0)
        self.assertEqual(by_seq[2], 7)

    def test_columns_in_random_order(self) -> None:
        header = [
            "思想汇报总篇数",
            "姓名",
            "第10次思想汇报",
            "学号",
            "职务",
            "发展阶段",
            "第1次思想汇报",
            "申请入党时间",
        ]
        result = parse_header_row(header)
        self.assertTrue(result.ok)
        m = result.mapping
        self.assertEqual(m.name_col, 1)
        self.assertEqual(m.student_number_col, 3)
        self.assertEqual(m.development_stage_col, 5)
        self.assertEqual(m.position_col, 4)
        self.assertEqual(m.applied_at_col, 7)
        self.assertEqual(m.reported_total_count_col, 0)
        by_seq = {r.sequence_number: r.column_index for r in m.report_columns}
        self.assertEqual(by_seq[10], 2)
        self.assertEqual(by_seq[1], 6)


class ParseHeaderRowAliasTests(SimpleTestCase):
    def test_student_number_aliases(self) -> None:
        for alias in ("学生学号", "学生编号", "学号/工号"):
            with self.subTest(alias=alias):
                header = [alias, "姓名", "发展阶段"]
                result = parse_header_row(header)
                self.assertTrue(result.ok, result.error_message)
                self.assertEqual(result.mapping.student_number_col, 0)
                self.assertEqual(result.mapping.name_col, 1)

    def test_name_aliases(self) -> None:
        for alias in ("学生姓名", "名字"):
            with self.subTest(alias=alias):
                header = ["学号", alias, "发展阶段"]
                result = parse_header_row(header)
                self.assertTrue(result.ok, result.error_message)
                self.assertEqual(result.mapping.name_col, 1)

    def test_other_field_aliases(self) -> None:
        header = [
            "学号",
            "姓名",
            "身份",
            "党内职务",
            "入党申请时间",
            "思想汇报篇数",
        ]
        result = parse_header_row(header)
        self.assertTrue(result.ok, result.error_message)
        m = result.mapping
        self.assertEqual(m.development_stage_col, 2)
        self.assertEqual(m.position_col, 3)
        self.assertEqual(m.applied_at_col, 4)
        self.assertEqual(m.reported_total_count_col, 5)


class ParseHeaderRowCoreMissingTests(SimpleTestCase):
    def test_missing_student_number_returns_header_not_found(self) -> None:
        header = ["姓名", "发展阶段", "第1次思想汇报"]
        result = parse_header_row(header)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, ERROR_HEADER_NOT_FOUND)
        self.assertIsNotNone(result.error_message)
        self.assertIn("学号", result.error_message or "")

        self.assertIsNone(result.mapping.student_number_col)
        self.assertEqual(result.mapping.name_col, 0)

    def test_missing_name_returns_header_not_found(self) -> None:
        header = ["学号", "发展阶段", "第1次思想汇报"]
        result = parse_header_row(header)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, ERROR_HEADER_NOT_FOUND)
        self.assertIn("姓名", result.error_message or "")

        self.assertIsNone(result.mapping.name_col)
        self.assertEqual(result.mapping.student_number_col, 0)

    def test_missing_both_name_and_number(self) -> None:
        header = ["发展阶段", "职务", "第1次思想汇报"]
        result = parse_header_row(header)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, ERROR_HEADER_NOT_FOUND)
        self.assertIn("姓名", result.error_message or "")
        self.assertIn("学号", result.error_message or "")

    def test_student_data_row_is_not_misidentified_as_header(self) -> None:
        data_row = ["20230001", "张三", "ACTIVIST", "支部书记", "2025/01/10", "3"]
        result = parse_header_row(data_row)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, ERROR_HEADER_NOT_FOUND)
        self.assertIsNone(result.mapping.name_col)
        self.assertIsNone(result.mapping.student_number_col)


class ParseHeaderRowReportColumnTests(SimpleTestCase):
    def test_report_columns_with_whitespace_and_numbers(self) -> None:
        header = [
            "学号",
            "姓名",
            "发展阶段",
            " 第 3 次思想汇报 ",
            "第10次思想汇报",
            "第 20 次思想汇报",
        ]
        result = parse_header_row(header)
        self.assertTrue(result.ok)
        by_seq = {r.sequence_number: r for r in result.mapping.report_columns}
        self.assertIn(3, by_seq)
        self.assertIn(10, by_seq)
        self.assertIn(20, by_seq)
        self.assertEqual(by_seq[3].column_index, 3)
        self.assertEqual(by_seq[10].column_index, 4)
        self.assertEqual(by_seq[20].column_index, 5)

    def test_report_columns_preserve_source_name(self) -> None:
        header = ["学号", "姓名", "发展阶段", " 第 5 次思想汇报 "]
        result = parse_header_row(header)
        self.assertTrue(result.ok)
        report = result.mapping.report_columns[0]
        self.assertEqual(report.sequence_number, 5)
        self.assertEqual(report.source_column_name, "第 5 次思想汇报")
        self.assertIsInstance(report, ReportColumn)

    def test_non_report_column_is_not_included(self) -> None:
        header = ["学号", "姓名", "发展阶段", "备注", "其他信息"]
        result = parse_header_row(header)
        self.assertTrue(result.ok)
        self.assertEqual(result.mapping.report_columns, [])


class ParseHeaderRowNormalizationTests(SimpleTestCase):
    def test_whitespace_and_none_handling(self) -> None:
        header = [None, " 学号\n", " 姓名 ", "\u3000发展阶段\u3000"]
        result = parse_header_row(header)
        self.assertTrue(result.ok)
        m = result.mapping
        self.assertEqual(m.student_number_col, 1)
        self.assertEqual(m.name_col, 2)
        self.assertEqual(m.development_stage_col, 3)

    def test_empty_list(self) -> None:
        result = parse_header_row([])
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, ERROR_HEADER_NOT_FOUND)
        self.assertTrue(result.mapping.has_core_fields() is False)
        self.assertEqual(result.mapping.report_columns, [])

    def test_optional_fields_missing_but_core_present(self) -> None:
        header = ["学号", "姓名"]
        result = parse_header_row(header)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, ERROR_HEADER_NOT_FOUND)
        m = result.mapping
        self.assertIsNone(m.development_stage_col)
        self.assertIsNone(m.position_col)
        self.assertIsNone(m.applied_at_col)
        self.assertIsNone(m.reported_total_count_col)
        self.assertEqual(m.report_columns, [])


class ParseHeaderNoDatabaseSideEffectsTests(SimpleTestCase):
    def test_parse_does_not_import_models(self) -> None:
        import sys

        module = sys.modules["apps.imports.parser"]
        module_globals = set(vars(module).keys())
        self.assertNotIn("models", module_globals)
        self.assertNotIn("Student", module_globals)
        self.assertNotIn("ImportBatch", module_globals)

from dataclasses import dataclass, field
from datetime import date


@dataclass
class ParseError:
    code: str
    message: str
    sheet_name: str
    excel_row_number: int | None = None
    student_name: str = ""
    student_number: str = ""
    field_name: str = ""
    source_value: str = ""


@dataclass
class ParseWarning:
    code: str
    message: str
    sheet_name: str
    excel_row_number: int | None = None
    student_name: str = ""
    student_number: str = ""
    field_name: str = ""
    source_value: str = ""
    parsed_value: str = ""


@dataclass
class ParsedReportItem:
    sequence_number: int
    submitted_at: date
    source_column_name: str


@dataclass
class ParsedStudentRow:
    sheet_name: str
    excel_row_number: int
    branch_code: str
    branch_name: str
    name: str
    student_number: str
    development_stage: str
    position: str
    applied_at: date | None = None
    reported_total_count: int | None = None
    calculated_date_count: int = 0
    report_items: list[ParsedReportItem] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)


@dataclass
class SheetResult:
    sheet_name: str
    branch_code: str | None
    branch_name: str | None
    status: str
    total_rows: int = 0
    valid_row_count: int = 0
    error_count: int = 0
    warning_count: int = 0


@dataclass
class ParseResult:
    total_sheets: int = 0
    success_sheets: int = 0
    failed_sheets: int = 0
    total_rows: int = 0
    success_rows: int = 0
    skipped_rows: int = 0
    warning_rows: int = 0
    valid_rows: list[ParsedStudentRow] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    sheet_results: list[SheetResult] = field(default_factory=list)

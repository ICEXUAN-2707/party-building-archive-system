from __future__ import annotations

import re
from dataclasses import dataclass

from apps.imports.error_codes import (
    ERROR_REPORT_COLUMN_NO_MATCH,
    ERROR_REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE,
    ERROR_REPORT_COLUMN_INVALID_CHINESE,
)

_MSG_NO_MATCH = "无法匹配“第X次思想汇报”列名格式"
_MSG_SEQUENCE_OUT_OF_RANGE = "思想汇报序号超出支持范围（1~99）"
_MSG_INVALID_CHINESE = "中文次数无法识别（仅支持“第一”~“第二十”）"

CHINESE_NUM_MAP: dict[str, int] = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
    "十三": 13,
    "十四": 14,
    "十五": 15,
    "十六": 16,
    "十七": 17,
    "十八": 18,
    "十九": 19,
    "二十": 20,
}

_ARABIC_PATTERN = re.compile(r"^\s*第\s*(\d{1,3})\s*次\s*(?:思想汇报)?\s*$")
_CHINESE_PATTERN = re.compile(r"^\s*第\s*([\u4e00-\u9fff]{1,8})\s*次\s*(?:思想汇报)?\s*$")


@dataclass
class ReportColumnParseResult:
    source_column_name: str
    sequence_number: int | None = None
    ok: bool = False
    error_code: str | None = None
    error_message: str | None = None


def _fail(name: str, code: str, message: str) -> ReportColumnParseResult:
    return ReportColumnParseResult(
        source_column_name=name,
        ok=False,
        error_code=code,
        error_message=message,
    )


def parse_report_sequence(column_name: str) -> ReportColumnParseResult:
    name = "" if column_name is None else column_name.strip()
    if not name:
        return _fail(name or "", ERROR_REPORT_COLUMN_NO_MATCH, _MSG_NO_MATCH)

    arabic = _ARABIC_PATTERN.match(name)
    if arabic:
        try:
            number = int(arabic.group(1))
        except ValueError:
            return _fail(name, ERROR_REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE, _MSG_SEQUENCE_OUT_OF_RANGE)
        if number < 1 or number > 99:
            return _fail(name, ERROR_REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE, _MSG_SEQUENCE_OUT_OF_RANGE)
        return ReportColumnParseResult(
            source_column_name=column_name,
            sequence_number=number,
            ok=True,
        )

    chinese = _CHINESE_PATTERN.match(name)
    if chinese:
        token = chinese.group(1)
        if token not in CHINESE_NUM_MAP:
            return _fail(name, ERROR_REPORT_COLUMN_INVALID_CHINESE, _MSG_INVALID_CHINESE)
        return ReportColumnParseResult(
            source_column_name=column_name,
            sequence_number=CHINESE_NUM_MAP[token],
            ok=True,
        )

    return _fail(name, ERROR_REPORT_COLUMN_NO_MATCH, _MSG_NO_MATCH)

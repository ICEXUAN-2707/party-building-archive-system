from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass

ERROR_DATE_UNSUPPORTED_FORMAT = "DATE_UNSUPPORTED_FORMAT"
ERROR_DATE_INVALID_CALENDAR = "DATE_INVALID_CALENDAR"
ERROR_DATE_VALUE_TYPE = "DATE_VALUE_TYPE"

_MSG_UNSUPPORTED_FORMAT = "日期格式不支持，仅允许：Excel 原生日期、YYYY/MM/DD、YYYY-MM-DD、YYYY.MM.DD、YYYY年M月D日"
_MSG_INVALID_CALENDAR = "日期格式正确但日历不存在（如 2025/02/30）"
_MSG_VALUE_TYPE = "单元格类型无法解析为日期"

_RE_SLASH = re.compile(r"^\s*(\d{4})\s*/\s*(1[0-2]|0?[1-9])\s*/\s*(3[01]|[12][0-9]|0?[1-9])\s*$")
_RE_DASH = re.compile(r"^\s*(\d{4})\s*-\s*(1[0-2]|0?[1-9])\s*-\s*(3[01]|[12][0-9]|0?[1-9])\s*$")
_RE_DOT = re.compile(r"^\s*(\d{4})\s*\.\s*(1[0-2]|0?[1-9])\s*\.\s*(3[01]|[12][0-9]|0?[1-9])\s*$")
_RE_CN = re.compile(r"^\s*(\d{4})\s*年\s*(1[0-2]|0?[1-9])\s*月\s*(3[01]|[12][0-9]|0?[1-9])\s*日\s*$")


@dataclass
class DateParseResult:
    value: _dt.date | None
    ok: bool
    error_code: str | None = None
    error_message: str | None = None
    source_value: str = ""


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _safe_build_date(year: int, month: int, day: int, raw: str) -> DateParseResult:
    try:
        parsed = _dt.date(year, month, day)
    except ValueError:
        return DateParseResult(
            value=None,
            ok=False,
            error_code=ERROR_DATE_INVALID_CALENDAR,
            error_message=_MSG_INVALID_CALENDAR,
            source_value=raw,
        )
    return DateParseResult(value=parsed, ok=True, source_value=raw)


def _parse_string(text: str) -> DateParseResult:
    patterns = (_RE_SLASH, _RE_DASH, _RE_DOT, _RE_CN)
    for pattern in patterns:
        match = pattern.match(text)
        if match:
            year, month, day = (int(x) for x in match.groups())
            return _safe_build_date(year, month, day, text)
    return DateParseResult(
        value=None,
        ok=False,
        error_code=ERROR_DATE_UNSUPPORTED_FORMAT,
        error_message=_MSG_UNSUPPORTED_FORMAT,
        source_value=text,
    )


def parse_date(value: object) -> DateParseResult:
    if _is_blank(value):
        return DateParseResult(value=None, ok=True)

    if isinstance(value, _dt.datetime):
        result = value.date()
        return DateParseResult(value=result, ok=True, source_value=str(value))

    if isinstance(value, _dt.date):
        return DateParseResult(value=value, ok=True, source_value=str(value))

    if isinstance(value, str):
        return _parse_string(value)

    return DateParseResult(
        value=None,
        ok=False,
        error_code=ERROR_DATE_VALUE_TYPE,
        error_message=_MSG_VALUE_TYPE,
        source_value=str(value),
    )

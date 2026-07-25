"""
学院学生材料信息查询系统 —— Excel 导入错误码与警告码集中定义。

所有 parser/date_utils/report_column_utils 中使用的错误码与警告码都应当在此集中
登记，禁止在业务代码内散落未登记的魔法字符串。

注意：
1. 错误码：触发后整行/整表失败，数据进入错误集合，不会进入 valid_rows。
2. 警告码：仅提示疑似问题，不阻止该行进入 valid_rows。
"""

from __future__ import annotations

# ----------------------------------------------------------------------
# 一、表头级别错误码
# ----------------------------------------------------------------------
ERROR_HEADER_NOT_FOUND = "HEADER_NOT_FOUND"
HEADER_NOT_FOUND = ERROR_HEADER_NOT_FOUND  # 别名

# ----------------------------------------------------------------------
# 二、行级别错误码
# ----------------------------------------------------------------------
ERROR_ROW_MISSING_REQUIRED = "ROW_MISSING_REQUIRED"
ERROR_ROW_INVALID_STAGE = "ROW_INVALID_STAGE"
ERROR_ROW_INVALID_APPLIED_DATE = "ROW_INVALID_APPLIED_DATE"
ERROR_ROW_COLUMN_SHIFT_SUSPECTED = "ROW_COLUMN_SHIFT_SUSPECTED"

# ----------------------------------------------------------------------
# 三、单元格/字段级别错误码
# ----------------------------------------------------------------------
ERROR_DATE_UNSUPPORTED_FORMAT = "DATE_UNSUPPORTED_FORMAT"
ERROR_DATE_INVALID_CALENDAR = "DATE_INVALID_CALENDAR"
ERROR_DATE_VALUE_TYPE = "DATE_VALUE_TYPE"

ERROR_REPORT_COLUMN_NO_MATCH = "REPORT_COLUMN_NO_MATCH"
ERROR_REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE = "REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE"
ERROR_REPORT_COLUMN_INVALID_CHINESE = "REPORT_COLUMN_INVALID_CHINESE"

# ----------------------------------------------------------------------
# 四、行/单元格级别警告码
# ----------------------------------------------------------------------
WARNING_REPORT_COUNT_MISMATCH = "REPORT_COUNT_MISMATCH"
WARNING_REPORT_TOTAL_COLUMN_MISSING = "REPORT_TOTAL_COLUMN_MISSING"
WARNING_REPORT_DATE_INVALID = "REPORT_DATE_INVALID"


# ----------------------------------------------------------------------
# 五、统一的错误/警告消息映射（方便生成用户可读的错误/警告说明）
# ----------------------------------------------------------------------
ERROR_MESSAGES: dict[str, str] = {
    ERROR_HEADER_NOT_FOUND: "无法识别表头核心字段（姓名/学号）",
    ERROR_ROW_MISSING_REQUIRED: "缺少必填字段（姓名/学号/发展阶段）",
    ERROR_ROW_INVALID_STAGE: "发展阶段非法，仅允许入党积极分子/中共预备党员/正式党员 或对应英文代码",
    ERROR_ROW_INVALID_APPLIED_DATE: "申请入党时间非法，仅允许 Excel 原生日期、YYYY/MM/DD、YYYY-MM-DD、YYYY.MM.DD、YYYY年M月D日",
    ERROR_ROW_COLUMN_SHIFT_SUSPECTED: "疑似列错位，本行跳过，禁止自动修复；请人工核对 Excel 列顺序",
    ERROR_DATE_UNSUPPORTED_FORMAT: "日期格式不支持",
    ERROR_DATE_INVALID_CALENDAR: "日期格式正确但该日历不存在（例如 2025/02/30）",
    ERROR_DATE_VALUE_TYPE: "单元格类型无法解析为日期",
    ERROR_REPORT_COLUMN_NO_MATCH: "该列名无法匹配第X次思想汇报格式",
    ERROR_REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE: "思想汇报序号超出范围 1~99",
    ERROR_REPORT_COLUMN_INVALID_CHINESE: "中文次数无法识别，仅支持第一~第二十",
}

WARNING_MESSAGES: dict[str, str] = {
    WARNING_REPORT_COUNT_MISMATCH: "思想汇报总篇数填报值与系统计算的有效日期数量不一致",
    WARNING_REPORT_TOTAL_COLUMN_MISSING: "缺少【思想汇报总篇数】列，无法进行总篇数校验",
    WARNING_REPORT_DATE_INVALID: "某一次思想汇报日期无法解析，本次记录跳过",
}


ALL_ERROR_CODES: frozenset[str] = frozenset(ERROR_MESSAGES.keys())
ALL_WARNING_CODES: frozenset[str] = frozenset(WARNING_MESSAGES.keys())

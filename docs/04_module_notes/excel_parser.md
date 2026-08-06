# Excel 解析模块（apps/imports.parser 系列）

负责人：角色六 - Excel 解析与导入预览模块

Branch: feature/excel-parser-new

---

# 1. 模块目标

负责把党务材料 Excel（多工作表，每表原则上对应一个党支部，前两行为表头、第三行起学生数据、思想汇报列为「第X次思想汇报」）纯解析为内存数据结构，为后续成员七编写"导入预览/正式入库/回滚"等业务提供稳定的解析层。

模块重点：
- 只负责"读 Excel → 产生 Python dataclass"的纯数据转换；
- 不写数据库，不自动修复列错位；
- 提供统一、可枚举的错误码 / 警告码，便于成员七在 UI 中逐条展示。

---

# 2. 唯一生产入口

成员七只需调用一个函数：

    from pathlib import Path
    from apps.imports.parser import parse_workbook

    result = parse_workbook(Path("/path/to/excel.xlsx"))

- 输入：pathlib.Path（本地已保存的 Excel 文件）
- 输出：apps.imports.datatypes.ParseResult
- 异常：文件不存在抛 FileNotFoundError；IO/损坏/openpyxl 不可读属系统异常
- 副作用：不访问 request/Session，不创建/修改数据库记录，不保存/创建文件

成员七不得复制工作簿遍历、表头识别、日期解析、支部映射或错误识别代码。

---

# 3. 目录 / 文件划分

    apps/imports/
    ├── datatypes.py              冻结的 Excel 解析结果 dataclass
    ├── error_codes.py            所有错误码 / 警告码集中定义
    ├── date_utils.py             日期解析：5 种格式
    ├── report_column_utils.py    「第 X 次思想汇报」列名解析
    └── parser.py                 主接口 parse_workbook + 表头/行解析工具

---

# 4. ParseResult 冻结结构

    @dataclass
    class ParseResult:
        total_sheets: int          # 工作表总数
        success_sheets: int        # 成功工作表数
        failed_sheets: int         # 失败工作表数
        total_rows: int            # 正式工作表中的非空数据行数（不含表头）
        success_rows: int          # 进入 valid_rows 的行数
        skipped_rows: int          # 因行级错误未进入 valid_rows 的行数
        warning_rows: int          # 至少有一个警告的不同行数
        valid_rows: list[ParsedStudentRow]
        errors: list[ParseError]
        warnings: list[ParseWarning]
        sheet_results: list[SheetResult]

统计语义：
- valid_rows：允许进入预览和后续确认流程的学生行
- errors：工作表级或行级错误；对应错误行不得进入 valid_rows
- warnings：不阻断对应有效行的可追踪问题
- warning_rows：至少包含一个警告的不同 Excel 数据行数量，不是警告对象总数
- skipped_rows：因行级错误未进入 valid_rows 的数据行数量
- total_rows：所有被识别正式工作表中的非空数据行数量，不包含两行表头

未知工作表记录 UNKNOWN_SHEET，不产生有效学生行；其状态和计数反映在 sheet_results 中。

---

# 5. ParsedStudentRow 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| sheet_name | str | 工作表名称 |
| excel_row_number | int | Excel 行号 |
| branch_code | str | 支部代码 |
| branch_name | str | 支部名称 |
| name | str | 姓名 |
| student_number | str | 学号 |
| development_stage | str | 发展阶段 |
| position | str | 职务 |
| applied_at | date | None | 申请入党时间 |
| reported_total_count | int | None | Excel 原始总篇数，允许为空 |
| calculated_date_count | int | 有效思想汇报日期条数 |
| report_items | list[ParsedReportItem] | 思想汇报明细 |
| warnings | list[ParseWarning] | 行级警告 |

reported_total_count 保存 Excel 原始值并允许为空；calculated_date_count 根据有效思想汇报日期计算，前者不得被后者覆盖。

---

# 6. 九支部冻结映射

| 支部名称 | 代码 |
|---------|------|
| 明理党支部 | MINGLI |
| 德理党支部 | DELI |
| 惟理党支部 | WEILI |
| 求理党支部 | QIULI |
| 知理党支部 | ZHILI |
| 昭理党支部 | ZHAOLI |
| 学理党支部 | XUELI |
| 博理党支部 | BOLI |
| 艺理党支部 | YILI |

工作表名称必须与上表完全匹配，否则记录 UNKNOWN_SHEET 错误且不产生有效学生行。

---

# 7. 工作表与边界规则

1. 九个支部名称和代码必须与 docs/spec.md 一致。
2. 正式表头位于前两行范围，第二行为标准位置；不得扫描普通学生行作为表头。
3. 核心表头字段：姓名、学号、发展阶段（三者缺一则表头识别失败）。
4. 思想汇报列动态识别，不固定列数量。
5. 中文次数临时支持第一至第二十。
6. sequence_number 临时支持 1 至 99。
7. 第二十一次和第 100 次必须产生集中登记的明确错误，不得被备用正则绕过。
8. 非法总篇数不能与空值混为 None，产生 ERROR_REPORT_TOTAL_INVALID 错误。
9. 缺少总篇数列属于工作表级警告，只记录一次。
10. 错误行整行跳过；警告行仍可进入 valid_rows。

---

# 8. 支持的日期格式（5 种）

统一入口：apps.imports.date_utils.parse_date

| # | 格式 | 示例 |
|---|------|------|
| 1 | Excel 原生日期 | datetime.date(2025,1,10) |
| 2 | YYYY/MM/DD | 2025/01/10 |
| 3 | YYYY-MM-DD | 2025-02-28 |
| 4 | YYYY.MM.DD | 2024.09.18 |
| 5 | YYYY年M月D日 | 2024年12月1日 |

---

# 9. 错误码和警告码

全部集中登记在 apps/imports/error_codes.py。

## 错误码（触发该行/该表不进入 valid_rows）

| 常量名 | code 值 | 含义 |
|--------|---------|------|
| ERROR_HEADER_NOT_FOUND | HEADER_NOT_FOUND | 无法识别核心表头（姓名/学号/发展阶段任一缺失） |
| ERROR_ROW_MISSING_REQUIRED | ROW_MISSING_REQUIRED | 行内姓名/学号/发展阶段为空 |
| ERROR_ROW_INVALID_STAGE | ROW_INVALID_STAGE | 发展阶段非法 |
| ERROR_ROW_INVALID_APPLIED_DATE | ROW_INVALID_APPLIED_DATE | 申请入党时间无法解析 |
| ERROR_ROW_COLUMN_SHIFT_SUSPECTED | ROW_COLUMN_SHIFT_SUSPECTED | 疑似列错位 |
| ERROR_DATE_UNSUPPORTED_FORMAT | DATE_UNSUPPORTED_FORMAT | 日期格式不支持 |
| ERROR_DATE_INVALID_CALENDAR | DATE_INVALID_CALENDAR | 日期不存在 |
| ERROR_DATE_VALUE_TYPE | DATE_VALUE_TYPE | 单元格类型无法解析为日期 |
| ERROR_REPORT_COLUMN_NO_MATCH | REPORT_COLUMN_NO_MATCH | 列名不匹配思想汇报格式 |
| ERROR_REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE | REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE | 序号超出 1~99 |
| ERROR_REPORT_COLUMN_INVALID_CHINESE | REPORT_COLUMN_INVALID_CHINESE | 中文次数不在第一~第二十 |
| ERROR_REPORT_TOTAL_INVALID | REPORT_TOTAL_INVALID | 思想汇报总篇数为非法值 |
| ERROR_UNKNOWN_SHEET | UNKNOWN_SHEET | 工作表名称不在九个党支部映射中 |

## 警告码（该行仍进入 valid_rows）

| 常量名 | code 值 | 含义 |
|--------|---------|------|
| WARNING_REPORT_COUNT_MISMATCH | REPORT_COUNT_MISMATCH | 总篇数与有效日期数不一致 |
| WARNING_REPORT_TOTAL_COLUMN_MISSING | REPORT_TOTAL_COLUMN_MISSING | 缺少总篇数列（工作表级，只一次） |
| WARNING_REPORT_DATE_INVALID | REPORT_DATE_INVALID | 思想汇报日期无法解析 |

---

# 10. 列错位检测

位于 parser.py 的 detect_column_shift(row_values, mapping)。

启发式信号命中 >= 2 条时产生 ROW_COLUMN_SHIFT_SUSPECTED 并跳过整行。严禁自动修复。

---

# 11. 明确声明：本模块不写数据库

- apps/imports 代码树没有导入任何 Django Model，没有 .save()/.create() 调用。
- 所有测试继承 SimpleTestCase，不访问数据库。
- 数据库写入统一留给成员七在获得用户确认导入后完成。

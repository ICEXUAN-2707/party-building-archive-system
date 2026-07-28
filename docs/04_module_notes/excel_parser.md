
---

# Excel 解析模块（apps/imports.parser 系列）


负责人：角色六 - Excel 解析与导入预览模块


Branch: `feature/project-foundation`


完成时间: 2026-07-25


---

# 1. 模块目标

负责把党务材料 Excel（多工作表，每表原则上对应一个党支部，前两行为表头、第三行起学生数据、思想汇报列为「第X次思想汇报」）**纯解析为内存数据结构**，为后续成员七编写"导入预览/正式入库/回滚"等业务提供稳定的解析层。

模块重点：
- 只负责"读 Excel → 产生 Python dataclass"的纯数据转换；
- **不写数据库**，不自动修复列错位；
- 提供统一、可枚举的错误码 / 警告码，便于成员七在 UI 中逐条展示。

---

# 2. 业务流程

```
成员七（导入业务层）
   │
   ▼
openpyxl.load_workbook(xlsx_path, data_only=True)
   │  sheet_names 按顺序迭代
   ▼
1）按党支部匹配：sheet_title 是否属于 明理/德理/惟理/求理/知理/昭理/学理/博理/艺理 九支部之一
   │  未知支部：记录 UNKNOWN_SHEET（仍可继续解析，但业务层建议不入库）
   ▼
2）取 sheet 第二行（索引 1）作为正式字段名 → parse_header_row(row2_values)
   │ 失败：HEADER_NOT_FOUND，该 sheet 不再解析学生行
   ▼
3）第三行（索引 2）开始到最后一行为学生数据 → parse_sheet_rows(data_rows, mapping, sheet_name, start_excel_row_number=3)
   │  每行产出：
   │    · 有效行 → ParsedStudentRow（带该行行级 warnings）
   │    · 错误行 → ParseError（含 excel_row_number）
   ▼
4）聚合工作表结果 → SheetResult
   ▼
5）所有工作表汇总为 ParseResult（纯 dataclass，未写数据库）
   │
   ▼
成员七：预览 UI 展示 / 点击确认正式入库 / 回滚 等（成员七后续任务，不在本模块）
```

---

# 3. 目录 / 文件划分

```
apps/imports/
├── datatypes.py              冻结的 Excel 解析结果 dataclass（ParseResult / SheetResult / ParsedStudentRow / ParsedReportItem / ParseError / ParseWarning）
├── error_codes.py            所有错误码 / 警告码集中定义 + ERROR_MESSAGES / WARNING_MESSAGES
├── date_utils.py             日期解析：5 种格式 → datetime.date / 结构化错误
├── report_column_utils.py    「第 X 次思想汇报」列名解析：阿拉伯数字 + 中文「第一~第二十」
└── parser.py                 主接口：表头识别、发展阶段中文映射、行级解析、行错位启发式检测、整张表批量解析
```

---

# 4. 解析主接口（成员七调用入口）

所有接口位于 [apps.imports.parser](file:///c:/Users/HUAWEI/Desktop/party-building-archive-system/apps/imports/parser.py)：

### 4.1 单张工作表级解析

```python
from apps.imports.parser import (
    parse_header_row,
    parse_sheet_rows,
    ERROR_HEADER_NOT_FOUND,
    ERROR_ROW_COLUMN_SHIFT_SUSPECTED,
)
from apps.imports.datatypes import ParseError, ParseWarning, ParsedStudentRow
```

- `parse_header_row(row2_values: list[object]) -> HeaderParseResult`
  - 输入：工作表第二行的单元格值列表（从 openpyxl 读 values_only=True 即可）
  - 输出：含 `ColumnMapping`（各字段列号映射）+ 错误码
  - 若姓名或学号无法识别 → `ok=False, error_code=HEADER_NOT_FOUND`

- `parse_sheet_rows(data_rows, mapping, sheet_name, *, start_excel_row_number=3) -> SheetParseResult`
  - 输入：data_rows 是「第三行起」的所有学生数据（二维 list）
  - 输出：
    - `valid_rows: list[ParsedStudentRow]` — 仅通过基础校验的行（警告行也在其中）
    - `errors: list[ParseError]`
    - `warnings: list[ParseWarning]`

### 4.2 单行级解析（调试/逐行 UI 高亮）

`parse_student_row(row_values, mapping, sheet_name, excel_row_number) -> RowParseResult`

当 `student_row is None` 时，`errors` 一定非空；当有警告但成功时，`warnings` 非空 + `student_row.warnings` 已同内容回填（便于单条渲染）。

### 4.3 辅助工具

```python
from apps.imports.date_utils import parse_date            # 5 种日期格式统一解析
from apps.imports.report_column_utils import parse_report_sequence  # 第X次思想汇报→序号
```

---

# 5. 结果结构（datatypes）

所有结构定义在 [apps.imports.datatypes](file:///c:/Users/HUAWEI/Desktop/party-building-archive-system/apps/imports/datatypes.py)：

| 结构 | 说明 |
|---|---|
| `ParseResult` | 整体文件结果：sheet 统计 + valid_rows + errors + warnings + sheet_results |
| `SheetResult` | 单工作表汇总：sheet_name、branch_code/branch_name、status、行列统计 |
| `ParsedStudentRow` | 单学生解析结果：name / student_number(str) / development_stage / applied_at(date) / report_items / warnings（行级警告全部回填在这里，方便预览页直接展示） |
| `ParsedReportItem` | 单条思想汇报明细：sequence_number(int) / submitted_at(date) / source_column_name（保留原始列名） |
| `ParseError` | 8 字段：code / message / sheet_name / excel_row_number / student_name / student_number / field_name / source_value |
| `ParseWarning` | 9 字段（Error 基础上 + `parsed_value`） |

> 注意：`ParsedStudentRow.reported_total_count` 永远是 Excel 列中"思想汇报总篇数"的原始值；`calculated_date_count` 是实际能解析到的有效思想汇报日期条数。**永远不会用 calculated 覆盖 reported**。若二者不相等，会产生 `REPORT_COUNT_MISMATCH` 警告。

---

# 6. 支持的日期格式（5 种；其余一律报错，不做模糊猜测）

统一入口：[parse_date](file:///c:/Users/HUAWEI/Desktop/party-building-archive-system/apps/imports/date_utils.py#L90)。返回 `DateParseResult(value: date | None, ok, error_code, error_message, source_value)`。

| # | 格式 | 示例 |
|---|---|---|
| 1 | Excel 原生日期（`datetime.datetime` / `datetime.date`） | `datetime.date(2025,1,10)` |
| 2 | `YYYY/MM/DD`（支持补 0 或不补 0） | `2025/01/10`、`2024/3/7` |
| 3 | `YYYY-MM-DD` | `2025-02-28` |
| 4 | `YYYY.MM.DD` | `2024.09.18`、`2024.9.9` |
| 5 | `YYYY年M月D日`（支持补 0 / 不补 0 / 中文字段间空格） | `2024年12月1日`、`2025年07月20日` |

不支持的情况（严格报错，不做缺省猜测）：
- 缺少年份（`3月15日` / `2025年1月`）
- 自然语言（`昨天` / `上周一` / `2025年春节后`）
- 带时间的 ISO（`2025-03-01T10:20:30`）
- `DD/MM/YYYY` / `MM/DD/YYYY` 等

对应的错误码：`DATE_UNSUPPORTED_FORMAT` / `DATE_INVALID_CALENDAR` / `DATE_VALUE_TYPE`（详见第 7 节）。

---

# 7. 错误码和警告码

全部集中登记在 [apps.imports.error_codes](file:///c:/Users/HUAWEI/Desktop/party-building-archive-system/apps/imports/error_codes.py)，并暴露 `ERROR_MESSAGES / WARNING_MESSAGES` 字典做国际化/UI 翻译。

**7.1 错误码（触发该行/该表不进入 valid_rows）**

| 常量名 | code 值 | 含义 |
|---|---|---|
| `ERROR_HEADER_NOT_FOUND` | `HEADER_NOT_FOUND` | 无法识别核心表头（姓名 / 学号任一缺失） |
| `ERROR_ROW_MISSING_REQUIRED` | `ROW_MISSING_REQUIRED` | 行内姓名 / 学号 / 发展阶段为空 |
| `ERROR_ROW_INVALID_STAGE` | `ROW_INVALID_STAGE` | 发展阶段不是 ACTIVIST / PROBATIONARY / FULL_MEMBER 或其中文同义 |
| `ERROR_ROW_INVALID_APPLIED_DATE` | `ROW_INVALID_APPLIED_DATE` | 申请入党时间非空但无法解析为 5 种合法日期格式 |
| `ERROR_ROW_COLUMN_SHIFT_SUSPECTED` | `ROW_COLUMN_SHIFT_SUSPECTED` | 疑似列错位（≥2 个启发式信号命中，且**不会自动修复**） |
| `ERROR_DATE_UNSUPPORTED_FORMAT` | `DATE_UNSUPPORTED_FORMAT` | 单元格字符串不匹配 5 种格式 |
| `ERROR_DATE_INVALID_CALENDAR` | `DATE_INVALID_CALENDAR` | 格式正确但该日历不存在（如 `2025/02/30`） |
| `ERROR_DATE_VALUE_TYPE` | `DATE_VALUE_TYPE` | 单元格类型既不是 str / date / datetime（int / list 等） |
| `ERROR_REPORT_COLUMN_NO_MATCH` | `REPORT_COLUMN_NO_MATCH` | 列名格式不是「第X次思想汇报」（report_column_utils 内使用） |
| `ERROR_REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE` | `REPORT_COLUMN_SEQUENCE_OUT_OF_RANGE` | 阿拉伯序号超出 1~99 范围 |
| `ERROR_REPORT_COLUMN_INVALID_CHINESE` | `REPORT_COLUMN_INVALID_CHINESE` | 中文次数不在「第一~第二十」 |

集成测试驱动层还会把下面 1 个登记到 ParseError：
- `UNKNOWN_SHEET` — 工作表名称不在 9 个党支部映射表中；是否入库由成员七决定。

**7.2 警告码（该行仍进入 valid_rows，但 UI 需要醒目展示）**

| 常量名 | code 值 | 含义 |
|---|---|---|
| `WARNING_REPORT_COUNT_MISMATCH` | `REPORT_COUNT_MISMATCH` | Excel「思想汇报总篇数」与实际有效思想汇报日期条数不一致 |
| `WARNING_REPORT_TOTAL_COLUMN_MISSING` | `REPORT_TOTAL_COLUMN_MISSING` | 工作表缺少「思想汇报总篇数」列，无法做总篇数校验 |
| `WARNING_REPORT_DATE_INVALID` | `REPORT_DATE_INVALID` | 某一次「思想汇报」单元格有值但无法解析，本次不生成 ParsedReportItem |

**字段完整性保证**：
- 每个 `ParseError` 和 `ParseWarning` 都至少具备：code、message、sheet_name、excel_row_number、student_name、student_number、field_name、source_value；
- `ParseWarning` 额外提供 `parsed_value`（如 REPORT_COUNT_MISMATCH：source_value=填报值，parsed_value=系统计算值）。

---

# 8. 列错位检测 & 禁止自动修复

位于 [parser.py](file:///c:/Users/HUAWEI/Desktop/party-building-archive-system/apps/imports/parser.py) 的 `detect_column_shift(row_values, mapping)`。

启发式信号有四类，命中≥2条 → 产生 `ERROR_ROW_COLUMN_SHIFT_SUSPECTED` 并跳过整行：
1. 姓名列为空，但右邻列疑似姓名（2~4 个纯汉字 CJK Unified Ideographs）
2. 发展阶段列非法，但左邻或右邻列出现合法阶段（中文 6 种 / 英文 3 种任一）
3. 学号列字符串像日期格式，或姓名列像 6~12 位纯数字学号
4. 多个字段类型与表头大范围不匹配（≥ 2 处）：申请时间像姓名/学号、阶段像日期/学号、姓名像学号、学号像日期

**严禁自动修复**：模块永远不会把「右邻列的值移动到姓名列」或类似猜测动作，避免把错误数据静默写库。成员七在 UI 中看到 `ROW_COLUMN_SHIFT_SUSPECTED` 后应提示导出老师重新导出 Excel 或手工修该行。

---

# 9. 成员七如何调用（建议代码骨架）

> 建议成员七封装一次 `parse_excel_to_result(xlsx_path) -> ParseResult`。以下伪代码可直接复制：

```python
from openpyxl import load_workbook

from apps.imports.datatypes import ParseResult, SheetResult, ParseError
from apps.imports.error_codes import ERROR_MESSAGES
from apps.imports.parser import (
    parse_header_row,
    parse_sheet_rows,
    ERROR_HEADER_NOT_FOUND,
)
from apps.students.choices import NINE_PARTY_BRANCHES  # 九支部 code → name（假设存在于学生模块冻结字典；若不存在请向学生模块负责人索取）

# sheet_title → (branch_code, branch_name)
BRANCH_BY_TITLE = {name: (code, name) for code, name in NINE_PARTY_BRANCHES.items()}


def parse_excel_to_result(xlsx_path: str, *, imported_by_id: int | None = None) -> ParseResult:
    """
    成员七建议入口：
    - 调用：views/imports.py 的 Excel 上传 POST 处理器
    - 返回：ParseResult（完全在内存；未写入导入批次数据库 / 学生数据库）
    """
    wb = load_workbook(xlsx_path, data_only=True, read_only=False)
    try:
        sheet_names = wb.sheetnames
        parse_result = ParseResult()
        parse_result.total_sheets = len(sheet_names)

        for title in sheet_names:
            ws = wb[title]
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            errors: list[ParseError] = []
            warnings: list = []
            valid_rows = []
            status = "skipped"
            total_rows = max(0, len(rows) - 2)
            branch = BRANCH_BY_TITLE.get(title)
            if branch is None:
                branch_code, branch_name = "", title
                errors.append(ParseError(
                    code="UNKNOWN_SHEET",
                    message=f"工作表名称未在 9 个支部映射中：{title}",
                    sheet_name=title,
                    excel_row_number=1,
                    student_name="",
                    student_number="",
                    field_name="sheet",
                    source_value=title,
                ))
            else:
                branch_code, branch_name = branch

            if len(rows) >= 2:
                header_result = parse_header_row(rows[1])
                if not header_result.ok:
                    errors.append(ParseError(
                        code=header_result.error_code or ERROR_HEADER_NOT_FOUND,
                        message=header_result.error_message or ERROR_MESSAGES[ERROR_HEADER_NOT_FOUND],
                        sheet_name=title,
                        excel_row_number=2,
                        student_name="",
                        student_number="",
                        field_name="header",
                        source_value=" | ".join(str(c) for c in rows[1]),
                    ))
                    status = "failed"
                else:
                    sheet_result = parse_sheet_rows(
                        data_rows=rows[2:],
                        mapping=header_result.mapping,
                        sheet_name=title,
                        start_excel_row_number=3,
                    )
                    errors.extend(sheet_result.errors)
                    warnings.extend(sheet_result.warnings)
                    valid_rows = sheet_result.valid_rows
                    # 回填支部信息（纯解析层数据，未写库）
                    for row in valid_rows:
                        row.branch_code = branch_code or ""
                        row.branch_name = branch_name or title
                    status = "success" if not any(
                        e.code == ERROR_HEADER_NOT_FOUND for e in errors
                    ) else "failed"

            # 构造 SheetResult 并填入 ParseResult（字段顺序按 AGENTS.md 冻结）
            sheet = SheetResult(
                sheet_name=title,
                branch_code=branch_code,
                branch_name=branch_name,
                status=status,
                total_rows=total_rows,
                valid_row_count=len(valid_rows),
                error_count=len(errors),
                warning_count=len(warnings),
            )
            parse_result.sheet_results.append(sheet)
            parse_result.valid_rows.extend(valid_rows)
            parse_result.errors.extend(errors)
            parse_result.warnings.extend(warnings)

        # 填入整体文件统计（成员七后续可直接给 UI 展示）
        parse_result.total_rows = sum(s.total_rows for s in parse_result.sheet_results)
        parse_result.success_rows = len(parse_result.valid_rows)
        # skipped_rows = 错误行数（ROW_MISSING_REQUIRED / ROW_INVALID_STAGE / ... / ROW_COLUMN_SHIFT_SUSPECTED 等行级错误，不含 sheet 级）
        row_level_error_count = sum(
            1 for e in parse_result.errors if e.code != ERROR_HEADER_NOT_FOUND and e.code != "UNKNOWN_SHEET"
        )
        parse_result.skipped_rows = row_level_error_count
        parse_result.warning_rows = len({
            (w.sheet_name, w.excel_row_number) for w in parse_result.warnings
        })
        parse_result.success_sheets = sum(1 for s in parse_result.sheet_results if s.status == "success")
        parse_result.failed_sheets = sum(1 for s in parse_result.sheet_results if s.status == "failed")
        return parse_result
    finally:
        wb.close()
```

---

# 10. 明确声明：本模块不写数据库

- 导入的 `apps.imports.*` 代码树（`datatypes.py / error_codes.py / date_utils.py / report_column_utils.py / parser.py`）**没有一处导入任何 Django Model**，也没有任何 `.save()` / `.create()` / `.bulk_create()` 调用。
- 所有测试继承 `django.test.SimpleTestCase`，运行时会跳过 `default` 数据库初始化（`Skipping setup of unused database(s): default`），佐证"不写数据库"的实现事实。
- 数据库写入（创建 ImportBatch / Student / ApplicationRecord / IdeologicalReport / OperationLog 等）统一留给**成员七（导入业务层 / 入库 / 回滚）**在获得用户在 UI 的"确认导入"后完成。

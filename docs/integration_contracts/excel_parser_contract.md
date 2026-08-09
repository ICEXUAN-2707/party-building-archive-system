# Excel 解析器接口契约

## 1. 契约状态

| 项目 | 内容 |
| --- | --- |
| 状态 | 修复阶段冻结契约 |
| 提供方 | 成员6，`imports` 解析模块 |
| 调用方 | 成员7，上传、预览与正式导入模块 |
| 依据 | `docs/spec.md`、成员6任务Spec、PR Review Report |

## 2. 唯一生产入口

```python
from pathlib import Path

def parse_workbook(file_path: Path) -> ParseResult:
    ...
```

最终导入路径：

```text
apps.imports.parser.parse_workbook
```

调用方不得复制工作簿遍历、表头识别、日期解析、支部映射或错误识别代码。

## 3. 输入、输出与副作用

输入：已经保存到本地的 Excel 文件 `Path`。

输出：`apps.imports.datatypes.ParseResult`。

副作用约束：

- 不访问 request 或 Session。
- 不创建或修改数据库记录。
- 不保存或创建文件。
- 无论成功或异常均关闭工作簿。

系统级异常：

- 文件不存在：抛出 `FileNotFoundError`。
- IO错误、文件损坏或 openpyxl 无法读取：允许相应的系统/openpyxl异常向调用方传播，不转换成普通行错误。

普通数据问题进入 `errors` 或 `warnings`，不得导致整个接口因单行问题崩溃。

## 4. ParseResult 冻结结构

```python
@dataclass
class ParseResult:
    total_sheets: int
    success_sheets: int
    failed_sheets: int
    total_rows: int
    success_rows: int
    skipped_rows: int
    warning_rows: int
    valid_rows: list[ParsedStudentRow]
    errors: list[ParseError]
    warnings: list[ParseWarning]
    sheet_results: list[SheetResult]
```

字段语义：

- `valid_rows`：允许进入预览和后续确认流程的学生行。
- `errors`：工作表级或行级错误；对应错误行不得进入 `valid_rows`。
- `warnings`：不阻断对应有效行的可追踪问题。
- `warning_rows`：至少包含一个警告的不同 Excel 数据行数量，不是警告对象总数；表头或工作表级警告不计入。
- `skipped_rows`：因行级错误未进入 `valid_rows` 的数据行数量。
- `total_rows`：所有被识别正式工作表中的非空数据行数量，不包含两行表头。

未知工作表记录 `UNKNOWN_SHEET`，不产生有效学生行；其状态为 `unknown` 并计入 `failed_sheets`，不得被当作正式支部数据。始终满足 `success_sheets + failed_sheets == total_sheets`。

## 5. 行结构

`ParsedStudentRow` 至少包含：

```text
sheet_name
excel_row_number
branch_code
branch_name
name
student_number
development_stage
position
applied_at
reported_total_count
calculated_date_count
report_items
warnings
```

日期类型统一为 `datetime.date`。

`reported_total_count` 保存 Excel 原始值并允许为空；`calculated_date_count` 根据有效思想汇报日期计算，前者不得被后者覆盖。

## 6. 工作表与边界规则

1. 九个支部名称和代码必须与 `docs/spec.md` 一致。
2. 正式表头位于前两行范围，第二行为标准位置；不得扫描普通学生行作为表头。
3. 思想汇报列动态识别，不固定列数量。
4. 中文次数临时支持第一至第二十。
5. `sequence_number` 临时支持1至99。
6. 第二十一次和第100次必须产生集中登记的明确错误，不得被备用正则绕过或静默忽略；含越界思想汇报列的工作表解析失败，但不阻断其他工作表。
7. 非法总篇数不能与空值混为 `None`。
8. 缺少总篇数列属于工作表级警告，只记录一次。
9. 错误行整行跳过；警告行仍可进入 `valid_rows`。

## 7. 错误码契约

错误码和警告码只在：

```text
apps/imports/error_codes.py
```

集中定义。解析器、日期工具和次数工具必须导入同一常量，不得重复定义不同字符串。

至少包含任务Spec冻结的：

```text
ROW_COLUMN_SHIFT_SUSPECTED
REPORT_TOTAL_COLUMN_MISSING
REPORT_COUNT_MISMATCH
REPORT_DATE_SEQUENCE_INCONSISTENT
UNKNOWN_SHEET
HEADER_NOT_FOUND
```

新增错误码必须先同步契约和 Module Notes。

## 8. 调用方约束

成员7：

1. 只调用 `parse_workbook(Path)`。
2. 预览阶段不得写 Student 和材料业务表。
3. `valid_rows` 是后续确认导入的候选输入。
4. `errors` 不得进入正式导入。
5. `warnings` 必须展示或记录，不得静默丢弃。
6. 不在测试或业务代码中创建第二套 ParseResult 或解析驱动。

## 9. 契约测试

1. 所有端到端测试直接调用 `parse_workbook()`。
2. 九个支部、多工作表和部分工作表失败可正确聚合。
3. 未知工作表没有有效学生行。
4. 前两行之外的普通数据不被识别为表头。
5. 第99次成功，第100次错误。
6. 第二十次成功，第二十一次错误。
7. 非法总篇数产生明确问题。
8. 缺少总篇数列只产生一次工作表警告。
9. 文件不存在、损坏和不可读文件产生系统级异常。
10. 解析前后核心数据库记录逐项不变。

## 10. 变更规则

主接口、dataclass字段、统计语义、错误码、次数边界或异常行为发生变化时，必须同步更新本契约、成员6/7 Module Notes 和消费测试，并由提供方与调用方共同确认。

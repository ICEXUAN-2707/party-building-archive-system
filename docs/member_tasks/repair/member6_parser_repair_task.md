# Task Card

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 成员 | 成员6 |
| 模块 | `imports` Excel纯解析模块 |
| 关联PR | `feature/excel-parser-new`，Review SHA `eaecdd4` |
| 优先级 | P0 |
| 预计工作量 | 1.5～2个工作日 |
| 提供契约 | `docs/integration_contracts/excel_parser_contract.md` |
| 调用方 | 成员7导入模块 |

## 2. Original Problem

### PARSER-01：生产主接口不存在

- 文件位置：`apps/imports/parser.py:1-601`
- 当前行为：没有 `parse_workbook(file_path: Path) -> ParseResult`，也没有生产级工作簿遍历和结果聚合。
- 实际风险：成员7没有可调用的冻结入口，核心任务未完成。

### PARSER-02：测试自行实现解析驱动

- 文件位置：`tests/test_excel_parser.py:963-1040`
- 当前行为：测试定义 `_load_row2_and_data()`、`_drive_sheet_parse()`和支部映射。
- 实际风险：129项测试没有验证应交付的生产接口，形成假集成测试。

### PARSER-03：要求调用方复制解析代码

- 文件位置：`docs/04_module_notes/excel_parser.md:207-314`
- 当前行为：建议成员7复制 `parse_excel_to_result()`伪代码。
- 实际风险：产生第二套解析器和接口漂移。

### PARSER-04：备用正则绕过序号边界

- 文件位置：`apps/imports/parser.py:180-199`
- 当前行为：正式次数解析失败后，备用正则仍可构造列且不校验1～99。
- 实际风险：第100次等越界列可能被接受。

### PARSER-05：非法总篇数静默变空

- 文件位置：`apps/imports/parser.py:493`
- 当前行为：非法值被转换为 `None`，没有错误或警告。
- 实际风险：无法区分空值和损坏数据。

### PARSER-06：核心表头判断不足

- 文件位置：`apps/imports/parser.py:109-118,245-246`
- 当前行为：只要求姓名和学号，缺少发展阶段仍判定表头成功。
- 实际风险：工作表结构问题被放大为大量行错误，统计失真。

### PARSER-07：错误码重复且不一致

- 文件位置：`apps/imports/report_column_utils.py:9`、`apps/imports/error_codes.py:34`
- 当前行为：同一中文次数错误使用不同字符串。
- 实际风险：成员7无法稳定消费错误码。

### PARSER-08：格式检查失败

- 文件位置：`tests/test_excel_parser.py:1453`
- 当前行为：`git diff --check`报告文件尾部多余空行。
- 实际风险：仓库质量门禁不完整通过。

## 3. Why It Is Wrong

- Spec：解析器必须支持多工作表、九支部、动态列和可追踪错误，且不写数据库。
- PRD/成员任务：唯一主要交付是 `parse_workbook(Path) -> ParseResult`。
- Interface Contract：成员7只能消费生产入口，不能复制解析器。
- Engineering Rule：解析、业务校验和写入分离；测试必须调用真实生产代码；错误码集中定义。

当前底层函数虽有测试，但没有形成可集成产品接口，因此属于合并阻塞。

## 4. Repair Scope

允许修改：

```text
apps/imports/parser.py
apps/imports/datatypes.py（仅契约确需）
apps/imports/error_codes.py
apps/imports/date_utils.py
apps/imports/report_column_utils.py
tests/test_excel_parser.py
tests/test_imports_parser_header.py
docs/04_module_notes/excel_parser.md
docs/integration_contracts/excel_parser_contract.md（仅实现校准）
```

## 5. Forbidden Modification Scope

禁止：

- 写入任何数据库模型；
- 创建 `ImportBatch`、错误记录或警告记录；
- 保存上传文件；
- 实现上传、预览、确认导入、回滚或页面；
- 修改 `apps/imports/models.py`和迁移；
- 要求成员7复制聚合或解析代码；
- 扩大中文第一至第二十、序号1～99的临时边界；
- 提交真实Excel；
- 修改 `docs/spec.md`。

## 6. Implementation Guidance

1. 在 `apps.imports.parser` 实现唯一 `parse_workbook(Path)`。
2. 验证路径后使用 openpyxl 打开工作簿，并在所有路径关闭。
3. 集中定义九支部映射，遍历所有工作表。
4. 只在前两行范围识别正式表头；未知表不生成有效学生行。
5. 复用现有日期、表头和行解析函数，聚合 `SheetResult` 与 `ParseResult`。
6. 删除测试侧工作簿驱动，让端到端测试直接调用主接口。
7. 删除次数备用解析路径；所有次数通过同一工具和错误码。
8. 空总篇数保持 `None`；非法值生成明确问题。
9. 缺少总篇数列只生成一次工作表级警告。
10. 统一 `warning_rows`、`skipped_rows`、`total_rows`统计语义。
11. Module Notes只提供调用示例，不包含可复制的第二套实现。

## 7. Interface Contract Update

更新文件：

```text
docs/integration_contracts/excel_parser_contract.md
```

接口名称：`apps.imports.parser.parse_workbook`。

输入：本地Excel文件 `pathlib.Path`。

输出：`apps.imports.datatypes.ParseResult`。

异常：文件不存在抛 `FileNotFoundError`；IO、损坏或openpyxl不可读属于系统异常；普通数据问题进入 errors/warnings。

提供方：成员6。调用方：成员7。

任何 dataclass 字段或统计语义调整，必须先同步契约并通知成员7。

## 8. Required Tests

测试文件：

```text
tests/test_excel_parser.py
tests/test_imports_parser_header.py
```

必须覆盖：

1. 九个支部全部识别。
2. 多工作表结果和统计聚合。
3. 单个工作表失败不阻止其他表进入结果。
4. 未知工作表不产生有效行。
5. 前两行合法表头识别，普通数据行不被识别为表头。
6. 第99次成功、第100次明确失败。
7. 第二十次成功、第二十一次使用统一错误码失败。
8. 非法总篇数与空值结果不同。
9. 缺总篇数列只产生一次工作表警告。
10. 文件不存在、损坏和不可读文件行为。
11. 所有端到端测试直接调用 `parse_workbook()`。
12. 解析前后 Student、材料和 ImportBatch 数据逐项不变。
13. `git diff --check`通过。

## 9. Acceptance Criteria

Given：一个包含九个正式支部和一个未知工作表的Excel。
When：调用 `parse_workbook(Path)`。
Then：正式支部正确聚合，未知表记录问题且不产生有效学生行。

Given：列名为“第100次思想汇报”。
When：解析工作簿。
Then：产生统一越界错误，任何备用路径都不能接受该列。

Given：思想汇报总篇数单元格为非法文本。
When：解析学生行。
Then：产生可追踪问题，不得静默转换成合法空值。

Given：成员7导入解析器。
When：需要预览Excel。
Then：只调用一个生产入口即可获得完整 `ParseResult`。

## 10. PR提交要求

提交前必须：

- 从最新 `develop` 整理修复，PR目标为 `develop`；
- 四项Django命令和 `git diff --check`通过；
- 删除测试侧解析驱动和Module Notes伪实现；
- Module Notes与 Interface Contract字段一致；
- 向成员7提供最终接口SHA和调用示例；
- README无需修改时说明原因；
- PR描述列出主接口、统计定义、异常和错误码；
- 最终SHA通过仓库策略及Windows/Ubuntu CI。

## Integration Risk

ParseResult直接影响成员7预览和正式导入的全部统计、错误落库和警告展示。dataclass、错误码或统计语义变化必须通知成员7和负责人；成员7在最终SHA前不得创建兼容层。

## PR界面的comment

```text
Block：当前生产代码没有 parse_workbook(Path) -> ParseResult，工作簿级测试由测试文件自身实现驱动，因此现有129项通过不能证明主接口可用。请实现唯一生产入口，删除测试侧解析器，统一九支部、统计与错误码，并修复序号备用路径和非法总篇数静默降级。契约与成员7确认前不得合并。
```

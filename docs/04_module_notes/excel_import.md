# Excel上传与服务端预览模块（PR1）

负责人：开发者A（成员7）

Branch：`feature/excel-import`

开发基线：`develop@b4d8779604b503cc0508842e7603b7030e1c45c1`

状态：PR1实现候选，等待开发者B确认公共接口、Review和CI

---

## 1. 本PR范围

本PR实现：

- data_admin安全上传`.xlsx`并生成服务端预览；
- 10 MiB精确边界、随机服务端文件名和批次隔离目录；
- 原始Excel SHA-256、`preview.json`和`preview.sha256`；
- 唯一调用`apps.imports.parser.parse_workbook(Path)`；
- 保存`ImportBatch`、`ImportErrorRecord`和`ImportWarningRecord`；
- 预览、历史、批次详情和data_admin受控原文件下载；
- 上传成功审计；
- 预览阶段四类业务表零写入。

本PR不实现`confirm_import`、正式业务表写入、`rollback_snapshot.json`、SQLite备份或回滚入口，不修改模型、迁移、解析器和权限模块。

## 2. URL与权限

| URL名称 | 路径 | 方法 | 权限 |
| --- | --- | --- | --- |
| `imports:upload` | `/imports/upload/` | GET/POST | data_admin |
| `imports:preview` | `/imports/<batch_id>/preview/` | GET | data_admin |
| `imports:history` | `/imports/history/` | GET | viewer_admin/data_admin |
| `imports:batch_detail` | `/imports/history/<batch_id>/` | GET | viewer_admin/data_admin |
| `imports:download_file` | `/imports/<batch_id>/file/` | GET | data_admin |

未登录请求由统一权限工具跳转`accounts:admin_login`，角色不符返回403。不存在批次或证据返回404；证据存在但哈希/schema/绑定校验失败返回409且不展示或下载内容。

## 3. 批次目录与写入顺序

```text
MEDIA_ROOT/imports/batch_<id>/
├── original_<32位随机hex>.xlsx
├── preview.json
└── preview.sha256
```

原始文件名只经过净化后写入`ImportBatch.original_filename`用于展示和安全下载，不参与服务端路径生成。原文件先经`ImportBatch.stored_file`配置的Django存储后端写入同批次临时名，再进行flush/fsync和原子替换；最终名称由服务端随机生成。所有服务端路径均通过批次ID、固定证据名或随机名生成，并在`Path.resolve()`后验证仍位于对应批次目录。

上传在单个数据库事务中执行：

```text
创建尚未提交的ImportBatch
→ 同目录临时文件写入原文件、flush/fsync、原子替换
→ 计算并冻结原文件SHA-256
→ 调用parse_workbook(Path)
→ 映射批次统计、错误和警告
→ 构造并字段级校验preview.json
→ 同目录临时写入JSON及SHA、flush/fsync、原子替换
→ 写upload_excel审计
→ 提交数据库事务
```

任一步骤失败时数据库事务回滚，并删除本次精确的`batch_<id>`目录，不留下可确认的`previewed`批次。测试通过临时`MEDIA_ROOT`验证，不写仓库`media/`。

## 4. PR2必须消费的公共接口

PR2不得自行拼接路径、重复计算可信路径或从客户端重建预览：

```python
from apps.imports.snapshots import load_preview_snapshot
from apps.imports.storage import open_verified_original, verified_original_path

verified_original_path(batch: ImportBatch) -> Path
open_verified_original(batch: ImportBatch) -> BinaryIO
load_preview_snapshot(batch: ImportBatch) -> dict[str, Any]
```

- `verified_original_path`验证路径归属、文件存在、批次哈希格式和完整文件SHA-256后返回本地路径，供只接受`Path`的解析/备份流程使用。
- `open_verified_original`返回重新校验过SHA的只读文件对象，调用方负责关闭。
- `load_preview_snapshot`依次校验原文件、preview文件、`preview.sha256`、JSON、schema、batch ID、原文件哈希、字段类型、日期、统计一致性、重复学号冲突和`can_confirm`，成功后才返回字典。

异常统一来自`apps.imports.storage`：

```python
ImportEvidenceNotFound
ImportEvidenceIntegrityError
```

开发者B确认PR2可直接消费上述三个接口后再开始正式导入实现；如需变更，应先更新冻结契约并由A Review。

## 5. `preview.json`字段级schema（version 1）

顶层：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `schema_version` | integer | 固定为`1` |
| `import_batch_id` | integer | 必须等于当前`ImportBatch.id` |
| `file_sha256` | string | 必须等于批次及原文件实际SHA-256 |
| `created_at` | string | ISO-8601时间 |
| `statistics` | object | 七项非负整数统计 |
| `sheet_results` | array | 每个解析Sheet一项 |
| `valid_rows` | array | 只含解析器确认的有效候选行 |
| `conflicts` | array | 当前只允许`DUPLICATE_STUDENT_NUMBER` |
| `can_confirm` | boolean | `valid_rows`非空且无冲突时才为true |

`statistics`：

```json
{
  "total_sheets": 1,
  "success_sheets": 1,
  "failed_sheets": 0,
  "total_rows": 1,
  "success_rows": 1,
  "skipped_rows": 0,
  "warning_rows": 0
}
```

约束：七项均为非负整数；`total_sheets == len(sheet_results)`；成功Sheet与失败Sheet之和等于总Sheet；各Sheet有效行之和、`success_rows`和`len(valid_rows)`三者相等；各Sheet总行之和等于`total_rows`。

`sheet_results[]`：

| 字段 | 类型 |
| --- | --- |
| `sheet_name` | string |
| `branch_code` | string或null |
| `branch_name` | string或null |
| `status` | string |
| `total_rows` | 非负integer |
| `valid_row_count` | 非负integer |
| `error_count` | 非负integer |
| `warning_count` | 非负integer |

`valid_rows[]`完整保存`ParsedStudentRow`可确认字段：

| 字段 | 类型/格式 |
| --- | --- |
| `sheet_name` | 非空string |
| `excel_row_number` | 正integer |
| `branch_code` | 非空string |
| `branch_name` | string |
| `name` | 非空string |
| `student_number` | 非空string |
| `development_stage` | 非空string |
| `position` | string，允许空字符串 |
| `applied_at` | ISO `YYYY-MM-DD`或null |
| `reported_total_count` | 非负integer或null |
| `calculated_date_count` | 非负integer |
| `report_items` | array |
| `warnings` | array，保存该行解析警告 |

`report_items[]`：

```json
{
  "sequence_number": 1,
  "submitted_at": "2025-02-03",
  "source_column_name": "第一次思想汇报"
}
```

次数必须为正整数，日期必须为ISO `YYYY-MM-DD`。`warnings[]`保存`code`、`message`、`sheet_name`、`excel_row_number`、`student_name`、`student_number`、`field_name`、`source_value`和`parsed_value`。

重复学号示例：

```json
{
  "code": "DUPLICATE_STUDENT_NUMBER",
  "student_number": "20260001",
  "message": "同一工作簿中学号20260001出现多次，后续确认必须拒绝。"
}
```

`conflicts`必须与`valid_rows`实际重复学号集合完全一致，禁止通过同时修改`can_confirm`绕过。

## 6. ParseResult映射

- 七项同名统计写入`ImportBatch`。
- `errors`映射到`ImportErrorRecord`，`warnings`映射到`ImportWarningRecord`；字符串按模型字段上限安全截断，说明正文完整保存。
- `REPORT_COUNT_MISMATCH`、`UNKNOWN_SHEET`、`ROW_INVALID_STAGE`和`ROW_COLUMN_SHIFT_SUSPECTED`按Sheet/行去重写入批次专项统计。
- 当前`ImportErrorRecord.excel_row_number`和`ImportWarningRecord.excel_row_number`均为非空正整数字段。若解析结果提供`None`或非正数，本PR不会编造0或其他业务行号，而是拒绝本次预览并完整清理批次。当前生产解析器对Sheet/表头级问题使用真实的1或2行，因此正常流程可无损保存；后续若解析器需要真正无行号的Sheet错误，必须先由负责人批准模型兼容方案。

## 7. 安全边界

- MIME只作为浏览器提示；扩展名和openpyxl实际解析共同决定是否可用。
- 原文件、preview及SHA不接受客户端路径或客户端回传内容。
- `pickle`、`eval`和客户端Session大对象均未使用。
- viewer_admin只能读历史和详情；模板不显示下载入口，后端权限仍独立校验。
- 下载响应只使用净化后的原文件名，不输出服务器路径。
- 原文件或preview被删除返回404；内容被篡改返回409。
- 预览只写导入证据表，`Student`、`ApplicationRecord`、`IdeologicalReportSummary`和`IdeologicalReport`逐字段保持不变。

## 8. 测试

测试文件：`tests/test_excel_import_preview.py`

当前31项PR1测试覆盖权限、方法、CSRF、扩展名、空文件、10 MiB边界、随机名、路径净化、SHA、schema、统计一致性、日期、错误警告映射、真实解析器、空预览、重复学号、原文件/preview篡改、历史详情下载、成功审计、失败清理和四类业务表零写入。2026-08-19在当前工作树执行全量测试共265项，全部通过；空临时SQLite迁移、`check`、迁移漂移检查、`git diff --check`和Repository policy均通过。

正式候选SHA提交后仍需在该SHA重跑门禁和三项CI，并由开发者B确认本文件第4、5节接口可消费。

# Excel上传、预览与确认导入接口契约

## 1. 契约状态

| 项目 | 内容 |
| --- | --- |
| 契约状态 | 冻结；以2026-08-12决策为准 |
| 实现状态 | 未实现；管理员依赖已于PR #3合入，等待PR 1 |
| 最后核验 | 2026-08-13 |
| 版本 | Sprint 2 / 1.0 |
| 冻结日期 | 2026-08-09 |
| 提供方 | 成员7，`imports`模块 |
| 消费方 | 导入模板、成员2集成测试、管理员查询页面 |
| 依据基线 | `develop@d2868b43e9126041226b58fbc2aef1d9e259a07f` |
| 依赖 | `excel_parser_contract.md`、`admin_permission_contract.md`、`docs/spec.md` V1.2 |

本契约冻结上传、预览、确认、批次和业务写入语义；不冻结视图类型、表单类或私有服务拆分方式。

## 2. 权限与公共入口

所有入口独立执行后端权限检查：未登录跳转`accounts:admin_login`。上传、预览、确认和原文件下载仅允许`data_admin`，`viewer_admin`返回403；历史列表和批次详情允许`viewer_admin`与`data_admin`读取。

| 功能 | 方法 | 路径 | URL名称 |
| --- | --- | --- | --- |
| 上传 | GET、POST | `/imports/upload/` | `imports:upload` |
| 预览 | GET | `/imports/<int:batch_id>/preview/` | `imports:preview` |
| 确认导入 | POST | `/imports/<int:batch_id>/confirm/` | `imports:confirm` |
| 历史列表 | GET | `/imports/history/` | `imports:history` |
| 批次详情 | GET | `/imports/history/<int:batch_id>/` | `imports:batch_detail` |
| 原文件下载 | GET | `/imports/<int:batch_id>/file/` | `imports:download_file` |

历史和详情允许`viewer_admin`与`data_admin`；原文件下载仅允许`data_admin`。第一版不向`viewer_admin`开放原始学生文件。

## 3. 上传文件

1. 只接受扩展名大小写不敏感的`.xlsx`文件。
2. 最大文件大小为10 MiB，即`10 * 1024 * 1024`字节；空文件拒绝。
3. 保留`original_filename`用于展示，但不得将其直接作为存储路径。
4. `stored_file`使用框架存储后端生成的不可预测名称；必须避免路径穿越和同名覆盖。
5. 保存后计算完整文件内容的SHA-256，并以64位小写十六进制写入`file_hash`。
6. 保存后的批次文件不可原地替换；重新上传必须创建新批次。
7. 文件保存或哈希失败不得创建可确认批次，并应清理本次不完整文件。

## 4. 解析与预览

唯一解析调用：

```python
apps.imports.parser.parse_workbook(file_path: Path) -> ParseResult
```

规则：

1. 上传成功后创建`ImportBatch`，初始状态为`previewed`。
2. 将`ParseResult`统计字段映射到批次同名字段：`total_sheets`、`success_sheets`、`failed_sheets`、`total_rows`、`success_rows`、`skipped_rows`、`warning_rows`。
3. `errors`保存为`ImportErrorRecord`，`warnings`保存为`ImportWarningRecord`；只映射现有模型具备的字段，不编造缺失字段。
4. `valid_rows`由服务端序列化为带`schema_version`的预览快照，用于跨请求展示和确认；不得由客户端重建。
5. GET预览和POST确认必须校验原始文件哈希、预览快照哈希、批次ID和schema；确认直接消费校验通过的服务端快照，不信任客户端提交的预览行。
6. 系统级文件或openpyxl异常不伪装成普通行错误；本次上传失败并向管理员显示安全错误信息。
7. 预览阶段允许写入上传文件、`ImportBatch`、错误和警告记录，但`Student`、`ApplicationRecord`、`IdeologicalReportSummary`、`IdeologicalReport`必须零写入。
8. 行级或工作表级错误必须展示并排除其对应数据，但不阻断其他`valid_rows`确认；系统级文件/工作簿异常阻断整个流程。
9. 没有`valid_rows`时仍允许形成可查看预览，但不允许确认，确认请求返回409。确认事务中的“整批”仅指本次`valid_rows`候选集合，禁止该集合内部部分成功；解析器已排除的错误行不属于候选集合。
10. 同一工作簿中出现重复`student_number`时确认被阻断，并反馈批次数据冲突，不选择任意一行覆盖。

## 5. ParseResult写入映射

确认只处理`valid_rows`，按`student_number`识别学生：

| 解析字段 | 目标 | 新建规则 | 已存在规则 | 空值规则 |
| --- | --- | --- | --- | --- |
| `branch_code` | `Student.branch` | 必须匹配现存支部 | 更新为该支部 | 不允许空 |
| `name` | `Student.name` | 写入 | 更新 | 不允许空 |
| `student_number` | `Student.student_number` | 写入并作为匹配键 | 不修改匹配键 | 不允许空 |
| `development_stage` | `Student.development_stage` | 写入 | 更新 | 不允许空 |
| `position` | `Student.position` | 空值写为空字符串 | 非空时更新 | 空值不清空已有值 |
| `applied_at` | `ApplicationRecord.applied_at` | 非空时创建记录 | 非空时更新 | 空值不创建、不清空已有值 |
| `reported_total_count` | `IdeologicalReportSummary.reported_total_count` | 创建汇总时允许`None` | 非空时更新 | `None`不覆盖已有填报值 |
| `calculated_date_count` | `IdeologicalReportSummary.calculated_date_count` | 写入 | 始终更新 | 由解析结果提供非负整数 |
| `report_items` | 有效`IdeologicalReport`集合 | 创建全部明细 | 完整替换该学生原有效明细 | 空集合表示替换为无有效明细 |

附加规则：

1. 新建学生的`status`使用模型默认`active`；更新学生时不得根据Excel缺失字段改变`status`。
2. 未出现在本批`valid_rows`中的学生及材料逐字段保持不变。
3. 错误行对应的既有学生及材料保持不变。
4. 有效行确认成功后更新相关记录的`source_import_batch`或`import_batch`。
5. 思想汇报的导入前状态由服务端`rollback_snapshot.json`完整留痕；正式写入时删除该学生旧有效明细，再创建本批有效明细。业务表不依赖多份`is_active=False`记录承担版本历史，避免与现有`(student, sequence_number, is_active)`唯一约束冲突。
6. 同一学生同一日期重复的思想汇报只保留一次并保留警告；不得补造缺失次数或日期。
7. `reported_total_count`与计算数不一致允许确认，保留两者并保留警告。

## 6. 确认事务与幂等

1. 确认只接受带CSRF保护的POST。
2. 确认前重新读取文件并计算SHA-256；与`ImportBatch.file_hash`不一致时拒绝且业务表零写入。
3. 批次必须处于`previewed`；`success`、`failed`或`rolled_back`均不得再次确认。
4. `ImportBatch.id`是确认幂等标识；重复请求不得重复创建或更新业务数据。
5. 所有学生和材料写入必须位于单一`transaction.atomic()`中，禁止部分成功。
6. 业务事务成功后批次转为`success`，设置`imported_at`、`imported_by`和各写入统计。
7. 业务事务失败时全部业务写入回滚；随后在独立可提交步骤将批次标为`failed`。失败批次不可重试，需重新上传创建新批次。
8. 成功确认记录`confirm_import`；失败确认不记录成功事件，可在批次状态和页面反馈中说明失败。

## 7. 状态机

现有冻结值：

```text
previewed
success
failed
rolled_back
```

允许转换：

```text
新上传 -> previewed
previewed -> success
previewed -> failed
success -> rolled_back（仅服从import_rollback_contract.md）
```

其他转换全部禁止。`failed`和`rolled_back`为终态。

## 8. 历史、详情与下载

1. 历史按`ImportBatch`模型默认顺序展示。
2. 详情展示文件名、哈希、上传/导入人、状态、统计、错误、警告、导入及回滚时间。
3. 原文件下载必须按批次读取保存文件，不接受客户端文件路径。
4. 响应使用安全下载文件名，并防止目录穿越。
5. 文件不存在返回404，不得泄露服务器路径。
6. 成功上传记录`upload_excel`；下载事件本版不扩展`OperationLog`冻结事件，若需记录必须先更新权限审计契约。

## 9. 契约测试

1. 匿名重定向、`viewer_admin`为403、`data_admin`允许。
2. 扩展名、空文件、大小边界、随机文件名、哈希和同名文件。
3. 解析统计、错误、警告映射正确。
4. 预览前后四类业务表逐项不变。
5. 错误行不进入确认候选，其他有效行仍可确认；空结果和重复学号不能确认。
6. 警告行可确认且警告保留。
7. 哈希变化拒绝确认。
8. 同批次重复确认不重复写入。
9. 中途异常导致业务事务完整回滚且批次标记失败。
10. 新建、更新、普通空值和思想汇报完整替换规则正确。
11. 未出现在Excel中的学生保持不变。
12. 错误行不修改旧数据。
13. 历史、详情和文件下载权限及404正确。
14. 上传和成功确认生成正确审计。

## 10. 禁止行为

- 不复制解析、权限或审计服务。
- 不信任客户端回传的预览数据。
- 不允许部分成功。
- 不删除未出现在Excel中的学生。
- 不使用模板隐藏代替后端权限。
- 不在回滚契约之外实现临时回滚。

## 11. 变更规则

上传限制、URL、`ParseResult`映射、字段覆盖、状态机、事务、幂等或审计事件变化时，必须同步更新本契约、成员7 Module Notes和成员2集成测试，并由成员7、成员2、受影响提供方和成员1共同确认。

# 开发者A独立任务卡：PR1上传预览与PR3安全回滚

## 1. 身份与总体目标

开发者A负责Excel文件与服务端证据链的首尾两端：先在PR1建立上传、预览、历史、下载及公共快照基础；待开发者B的PR2合入后，再在PR3实现最近成功批次回滚、SQLite灾难恢复工具和最终恢复验证。

不得在PR1提前实现正式导入，不得在PR3重写PR2的导入算法。

## 2. 分支与提交规则

### PR1

- 远端分支：`feature/excel-import`
- 基线：当前最新`develop@5765e54`，开发前再次fetch确认
- PR目标：`develop`
- 推荐提交拆分：文件验证与存储、预览快照、View/模板、历史下载、测试文档

### PR3

- 分支：`feature/excel-import-rollback`
- 只能在PR2合并后的最新`develop`创建
- PR目标：`develop`
- 禁止从PR1旧分支继续开发或携带未合并提交

## 3. PR1目标和非目标

### 必须交付

```text
data_admin上传.xlsx
→ 安全保存原文件
→ SHA-256
→ 调用parse_workbook
→ 保存批次/错误/警告
→ 原子生成preview.json及preview.sha256
→ 跨请求预览
→ 管理员历史/详情
→ data_admin受控下载原文件
```

### PR1严禁

- 不写`Student`、`ApplicationRecord`、`IdeologicalReportSummary`、`IdeologicalReport`。
- 不实现`confirm_import`业务写入。
- 不生成`rollback_snapshot.json`或SQLite备份。
- 不实现回滚入口。
- 不修改parser、管理员权限、学生认证、模型或迁移。
- 不新增数据库快照模型。

## 4. PR1允许文件

- `apps/imports/forms.py`
- `apps/imports/views.py`
- `apps/imports/urls.py`
- `apps/imports/storage.py`或职责等价的私有模块
- `apps/imports/snapshots.py`或职责等价的私有模块
- `templates/imports/upload.html`
- `templates/imports/preview.html`
- `templates/imports/history.html`
- `templates/imports/batch_detail.html`
- `tests/test_excel_import_preview.py`及必要的导入集成测试
- `docs/04_module_notes/excel_import.md`
- 对应契约实现状态和任务状态文档

对`config/settings.py`、`templates/base.html`或测试辅助文件的修改必须最小化，并在PR描述逐项说明理由。

## 5. 上传表单与输入验证

1. 只接受扩展名大小写不敏感的`.xlsx`。
2. 空文件返回400或带表单错误的HTTP 200，不创建可确认批次。
3. 上限严格为`10 * 1024 * 1024`字节：等于上限允许，超过1字节拒绝。
4. MIME只能辅助判断，不能代替扩展名和openpyxl实际解析。
5. `original_filename`只展示，必须去除路径成分和控制字符，不能参与服务端路径拼接。
6. 同名上传必须形成不同存储对象，不覆盖旧文件。
7. 文件保存、哈希或解析发生系统级异常时，清理本次不完整文件，不留下可确认的`previewed`批次。
8. 上传成功记录`upload_excel`审计；失败不得伪造成功事件。

## 6. 批次目录与文件安全

第一版约定目录：

```text
MEDIA_ROOT/imports/batch_<id>/
├── original_<random>.xlsx
├── preview.json
└── preview.sha256
```

要求：

- 所有路径由批次ID和服务端随机名生成。
- 使用`Path.resolve()`或等价机制证明目标位于批次目录内。
- JSON与SHA先写同目录临时文件，flush/关闭后以原子重命名替换。
- SHA-256为完整文件字节的64位小写十六进制。
- 提供单一安全读取接口，PR2/PR3不得自行拼路径。
- 测试使用临时`MEDIA_ROOT`并验证清理，禁止污染仓库`media/`。

## 7. preview.json冻结schema

建议版本`schema_version = 1`，至少包含：

```json
{
  "schema_version": 1,
  "import_batch_id": 1,
  "file_sha256": "64位小写十六进制",
  "created_at": "ISO-8601时间",
  "statistics": {
    "total_sheets": 0,
    "success_sheets": 0,
    "failed_sheets": 0,
    "total_rows": 0,
    "success_rows": 0,
    "skipped_rows": 0,
    "warning_rows": 0
  },
  "sheet_results": [],
  "valid_rows": []
}
```

每个`valid_rows`元素必须完整保存`ParsedStudentRow`全部可确认字段；`report_items.submitted_at`和`applied_at`使用ISO `YYYY-MM-DD`。Excel输入标准仍为Spec规定的`YYYY/MM/DD`，JSON内部ISO格式不构成冲突。

读取快照时必须校验：schema、batch ID、原文件SHA、快照SHA、字段类型、日期、非负整数、思想汇报正整数次数。禁止pickle、`eval`或客户端回传快照。

PR1必须在Module Notes中提供字段级schema，并由B在PR2开工前签字确认可消费。

## 8. ParseResult映射

- 唯一调用`parse_workbook(Path)`，不复制解析规则。
- 批次统计映射现有同名字段。
- `ParseError`写入`ImportErrorRecord`，`excel_row_number=None`时需采用契约允许且模型可表达的安全策略；不得编造业务行号。
- `ParseWarning`只映射模型已有字段。
- 系统级openpyxl/文件异常不能伪装为普通错误行。
- 错误行和失败Sheet不进入`valid_rows`，其他有效行仍可预览。
- 空`valid_rows`仍形成可读预览，但页面明确不可确认。
- 同批重复学号可以在PR1标记冲突并展示；最终后端确认阻断由PR2再次执行。

如发现`excel_row_number`现有非空模型无法保存Sheet级错误，必须先形成最小兼容方案供负责人审核；不得擅自新增迁移。

## 9. URL、权限与响应

严格实现冻结URL：

| 入口 | 方法 | 权限 |
| --- | --- | --- |
| `imports:upload` | GET/POST | data_admin |
| `imports:preview` | GET | data_admin |
| `imports:history` | GET | viewer_admin/data_admin |
| `imports:batch_detail` | GET | viewer_admin/data_admin |
| `imports:download_file` | GET | data_admin |

- 未登录跳转`accounts:admin_login`。
- 未授权管理员返回403。
- 不存在批次或文件返回404。
- 下载只按批次读取，使用安全`Content-Disposition`，不泄露服务器路径。
- 历史与详情不能通过模板链接间接暴露原文件下载给viewer。
- 预览按钮可隐藏，但后端权限是唯一安全边界。

## 10. 页面要求

预览至少展示：

- 工作表总数、成功/失败工作表；
- 每个Sheet对应支部及状态；
- 总行、有效、跳过、警告；
- 缺少总篇数列、列错位、日期顺序异常等警告；
- Excel行号和可人工修正的信息；
- 原始总篇数与计算日期数不一致；
- 明确提示被跳过的Sheet/行；
- 空有效结果不可确认提示；
- 后续确认入口的预留只能指向冻结URL，不得实现写入。

页面日期使用中文格式；不得把服务端路径、异常堆栈或敏感学生原文件地址输出到页面。

## 11. PR1测试清单

至少覆盖：

1. 匿名、viewer、data_admin的所有入口矩阵。
2. GET/POST方法限制和CSRF。
3. `.xlsx`大小写、错误扩展名、双扩展名、空文件。
4. 10 MiB边界和超1字节。
5. 同名上传、随机文件名、路径穿越文件名。
6. SHA-256正确性和文件被篡改后的预览拒绝。
7. preview schema、日期、统计、快照SHA。
8. preview JSON缺失、损坏、schema错误、batch ID错误。
9. parser系统异常与普通行错误的区别。
10. 错误/警告/Sheet统计完整映射。
11. 空结果可预览。
12. 四类业务表上传前后逐项零变化。
13. 历史默认排序、详情404和关联错误/警告展示。
14. viewer可读历史但不能下载；data_admin可下载。
15. 文件缺失404、下载名安全、响应不泄露路径。
16. upload审计只在成功后生成。
17. 临时媒体文件清理和仓库污染检查。

## 12. PR1验收与交接B

PR1描述必须附：

- 最终SHA及三项CI链接；
- URL和权限矩阵；
- preview schema完整示例；
- 批次目录和原子写入说明；
- 预览业务表零写入证据；
- 已知限制和PR2消费接口列表。

A必须Review B的PR2，重点检查B是否绕过安全读取、重复实现哈希或从客户端重建快照。

---

## 13. PR3开工条件

只有以下条件全部满足才开工：

- PR1已合入develop；
- PR2已合入develop；
- B已在Module Notes冻结`rollback_snapshot.json` schema；
- PR2的字段覆盖、思想汇报替换和来源批次语义已有测试；
- 最新develop三项CI成功。

## 14. PR3必须交付

```text
data_admin查看回滚影响
→ 校验最新success批次及全部证据
→ 二次确认POST
→ transaction.atomic整批恢复
→ 成功后rolled_back和审计
```

另提供受控SQLite灾难恢复管理命令，只用于停机运维，不提供Web恢复入口。

## 15. PR3回滚判定

批次必须同时满足：

1. 状态为`success`且未回滚。
2. 是当前最新成功批次，无后续成功批次。
3. JSON快照、SHA、schema、batch ID、记录数全部有效。
4. 当前Student及材料来源仍能安全归属本批。
5. 没有无法解释的后续修改或外键依赖。

任一失败返回409，批次保持success，数据库零变化。格式错误返回400；匿名重定向；viewer/未知角色403。

## 16. PR3恢复算法

在单个`transaction.atomic()`内：

- 已有学生恢复快照中的可恢复字段和原来源批次；
- 导入前不存在的ApplicationRecord/Summary删除本批创建记录；原有记录按快照恢复；
- 删除本批思想汇报，按快照重建原有效集合；
- 不新增inactive版本历史，不修改唯一约束；
- 本批新建学生只有在所有来源、关联、后续变化和外键检查安全时删除；
- 任一对象冲突则抛出领域冲突并撤销整批；
- 成功后设置`rolled_back_at`、`rolled_back_by`和状态；
- 事务成功后记录`rollback_import`。

原始Excel、预览、回滚快照、SQLite备份、错误、警告和审计记录继续保留。

## 17. SQLite灾难恢复命令

建议命令：

```text
python manage.py restore_import_backup --batch-id <id> --verify-only
python manage.py restore_import_backup --batch-id <id> --confirm
```

必须：

- 仅支持SQLite；
- 校验备份文件、来源批次及`PRAGMA integrity_check`；
- 默认只验证，不执行恢复；
- 明确要求停机；
- 恢复前再次备份当前数据库；
- 使用同文件系统临时文件和原子替换；
- 恢复后提示执行migrate、check和一致性检查；
- 绝不由Web View在线替换数据库。

## 18. PR3测试与最终验收

至少覆盖权限、GET/POST、CSRF、非最新批次、重复回滚、快照缺失/篡改/schema错误、已有学生恢复、新建学生安全删除、删除冲突、申请/汇总恢复、思想汇报唯一约束、事务中途失败、审计、灾难恢复verify-only及安全拒绝。

PR3合入后，A与B共同使用约1500条合成数据完成：上传、预览、确认、管理员查询、学生查询、第二次导入、最近批次回滚、查询恢复和证据保留的端到端验收。


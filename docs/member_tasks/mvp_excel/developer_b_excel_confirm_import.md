# 开发者B独立任务卡：PR2正式事务导入

## 1. 身份与目标

开发者B负责PR2，将A在PR1生成并校验的服务端预览快照转换为一次可审计、可回滚、整批原子的正式导入。B同时负责冻结回滚快照schema，供A的PR3严格逆向恢复。

PR2不实现回滚页面或恢复命令。

## 2. 开工条件与分支

- A的PR1已经Review、CI通过并合入`develop`。
- 从PR1合并后的最新`develop`新建`feature/excel-import-confirm`。
- 禁止基于A的未合并分支开发。
- 开工前核对PR1 Module Notes中的目录、preview schema、安全读取和哈希接口。
- 如PR1接口不足，先提出契约变更并由A与负责人确认，不得复制一套替代实现。

## 3. 必须交付

```text
data_admin POST确认批次
→ 校验状态/原文件/preview证据
→ 校验候选集合
→ 原子生成rollback_snapshot及SHA
→ SQLite一致性备份
→ transaction.atomic写入全部候选
→ success/统计/审计
```

失败时业务写入全部撤销，批次在独立可提交步骤标为failed，文件、批次、错误、警告、预览、回滚快照和备份继续保留。

## 4. 允许文件

- `apps/imports/views.py`中的确认入口
- `apps/imports/urls.py`中的冻结确认URL
- `apps/imports/services.py`、`import_service.py`或职责等价的业务服务
- `apps/imports/snapshots.py`中回滚快照部分；不得破坏PR1 preview接口
- `apps/imports/storage.py`中经A Review的必要扩展
- 确认相关模板最小修改
- `tests/test_excel_import_confirm.py`
- 导入后管理员/学生跨模块集成测试
- `docs/04_module_notes/excel_import.md`
- 契约实现状态和任务表

禁止修改parser、学生认证、管理员权限、思想汇报唯一约束、模型和迁移；禁止新增快照模型。

## 5. 确认入口与响应语义

冻结入口：

```text
POST /imports/<int:batch_id>/confirm/
URL name: imports:confirm
```

- 未登录重定向管理员登录。
- viewer_admin、未知角色和停用管理员返回403。
- GET返回405。
- 普通格式错误返回400。
- 状态冲突、重复确认、空候选、重复学号、证据冲突返回409。
- 批次不存在返回404。
- 必须启用CSRF；模板隐藏按钮不能替代权限。

## 6. 确认前校验顺序

必须在任何业务写入前完成：

1. 权限、方法和批次存在性。
2. 批次状态严格为`previewed`。
3. 原文件存在且完整SHA-256等于`ImportBatch.file_hash`。
4. `preview.json`及`preview.sha256`存在且匹配。
5. schema版本、batch ID、file SHA和所有字段类型有效。
6. `valid_rows`非空。
7. 本批`student_number`无重复；重复时整批409，不任选覆盖。
8. 学号、姓名、支部、阶段等必填字段有效。
9. branch_code精确匹配现有且启用的九支部。
10. 日期可由ISO安全还原；次数为正整数；计数为非负整数。
11. 不接受任何客户端回传的学生行或ParseResult。

确认不得重新调用parser重建候选；只消费PR1保存并完整校验的服务端快照。

## 7. rollback_snapshot.json schema

B负责冻结版本1，至少包含：

```json
{
  "schema_version": 1,
  "import_batch_id": 1,
  "preview_sha256": "...",
  "created_at": "ISO-8601时间",
  "record_count": 1,
  "students": [
    {
      "student_number": "...",
      "student_existed_before": true,
      "student": {},
      "application_record": null,
      "report_summary": null,
      "active_reports": []
    }
  ]
}
```

必须保存可完整恢复的业务字段和原来源批次主键；不得保存密码、Session、文件内容、Python对象或服务器绝对路径。日期使用ISO格式。`record_count`与students长度一致。

快照由数据库当前状态服务端生成，按稳定顺序序列化，以临时文件+原子重命名写入，并生成SHA-256。任一证据生成失败不得开始业务事务。

## 8. SQLite导入前备份

- 使用SQLite backup API或能证明一致性的等价方式，不能在数据库活跃时直接普通文件复制。
- 保存为批次目录`pre_import.sqlite3`。
- 备份后执行`PRAGMA integrity_check`并校验文件非空。
- 失败时禁止正式写入。
- 备份只作灾难恢复，不用于Web回滚。
- 测试数据库及内存SQLite需要明确、可测试的安全策略；不得写入仓库真实数据库路径。

## 9. 并发与幂等

第一版是单机、单Django实例、SQLite，但仍必须防重复请求：

- `ImportBatch.id`是幂等标识。
- 在事务中重新读取并锁定批次；SQLite限制需在测试和Module Notes说明。
- 第一个确认成功后状态变为success。
- 后续同批请求返回409，不重复更新Student或创建Report。
- 两个近同时请求最终只能有一个成功；如SQLite锁冲突，不能形成半导入。
- failed和rolled_back均不可确认。

## 10. Student写入规则

按`student_number`匹配：

- 新建：写name、student_number、branch、development_stage、position，status使用默认active，source_import_batch设本批。
- 更新：更新name、branch、development_stage；Excel position非空才覆盖，空值保留旧值；不得根据Excel改变status；source_import_batch设本批。
- 学号是匹配键，不修改既有学号。
- 同一学号对应冲突姓名仍按冻结导入映射更新name，但本批内部重复学号必须阻断。
- 未出现在valid_rows中的学生完全不变。
- 错误行对应的既有学生完全不变。

## 11. ApplicationRecord规则

- 新学生且`applied_at`非空：创建。
- 新学生且为空：不创建。
- 既有记录且非空：更新日期和source_import_batch。
- 既有记录且为空：保持原记录不变。
- 没有旧记录且为空：不创建。

## 12. IdeologicalReportSummary规则

- 新学生需要汇总时创建，允许`reported_total_count=None`。
- `reported_total_count`非空时更新；None不得覆盖旧Excel填报值。
- `calculated_date_count`始终写解析快照值。
- source_import_batch设为本批。
- 原始填报值0是有效值，不能按False回退。
- 原始值与计算值不一致允许导入并保留警告，不相互覆盖。

## 13. IdeologicalReport规则

- 仅处理本批valid_rows学生。
- 导入前状态已写入rollback snapshot后，删除该学生旧有效明细，再创建本批有效明细。
- 不依赖多份`is_active=False`记录保存版本历史。
- 不修改现有唯一约束。
- `sequence_number`保持Excel列真实次数，不重编号。
- 日期重复只保留解析器已去重后的结果，不补造缺失日期或次数。
- `report_items=[]`表示替换为无有效明细。
- 新记录`import_batch`设为本批、`is_active=True`。
- 任何创建冲突导致整批事务失败。

## 14. 统计、状态和审计

成功时：

- 批次状态转`success`；
- 设置`imported_at`和`imported_by`；
- 准确更新`created_students`、`updated_students`、`created_reports`、`updated_applications`及现有警告分类统计；
- 记录一次`confirm_import`审计，target指向批次；
- 审计必须在业务成功后，不能在事务回滚时留下成功日志。

失败时：

- 业务表全部回滚；
- 在独立步骤把批次标为failed；
- 不记录成功confirm审计；
- 保留全部服务器证据；
- 页面只显示安全错误，不泄露堆栈或路径；
- failed批次不能重试，需重新上传。

## 15. PR2测试矩阵

### 权限和状态

- 匿名重定向；viewer/未知/停用403；data_admin允许；GET 405；CSRF拒绝。
- previewed可确认；success/failed/rolled_back均409。
- 重复确认数据零变化。

### 证据链

- 原文件缺失、哈希变化。
- preview缺失、SHA错误、schema错误、batch ID错误、file SHA错误。
- rollback快照或SQLite备份生成失败时业务零写入。
- SQLite备份完整性检查。

### 候选校验

- 空valid_rows 409。
- 重复学号409。
- 未知/停用支部、非法阶段、非法日期和计数类型。
- 客户端附带伪造行被完全忽略。

### 字段覆盖

- 新建学生、更新学生、status保持。
- position空值不清空旧值。
- applied_at空值不创建/不清空。
- reported_total_count的正数、0、None。
- calculated_date_count始终更新。
- 未出现学生和错误行学生保持不变。

### 思想汇报

- 有效集合完整替换、空集合清空。
- 真实sequence_number与升序查询。
- 重复日期不重复创建。
- 唯一约束冲突整批回滚。
- 连续两次导入同一学生不会因inactive历史冲突。

### 原子性和并发

- 多学生候选中最后一行故障，前面写入全部撤销。
- Student成功但材料失败时全部撤销。
- 两个近同时确认只有一个成功。
- failed状态在业务回滚后可见，文件证据仍存在。

### 跨模块

- 导入后管理员列表/筛选/详情正确。
- 管理员详情同时展示原始值、计算值、当前值和来源。
- 学生凭姓名学号登录后只看到自己的导入数据。
- 最近更新时间反映导入后的系统记录时间。

## 16. 与A的交接和Review

PR2描述必须提供：

- rollback schema字段级说明和完整示例；
- 每个模型的新建、更新、空值、删除规则；
- 导入前证据生成顺序；
- 事务边界、失败状态更新和审计时点；
- 幂等及并发策略；
- 导入统计定义；
- PR3恢复所需的不变量；
- 最终SHA和三项CI链接。

A是PR2必需Reviewer，重点审查PR1接口消费和快照证据。PR2合并后，B是PR3必需Reviewer，必须逐字段验证回滚能逆转PR2，且冲突时整批零变化。

## 17. PR2验收标准

- 候选集合在单一事务内全成功或全失败。
- 重复确认和所有状态冲突返回409。
- 失败证据保留且没有半导入。
- JSON快照和SQLite备份在写入前完整生成并校验。
- 字段覆盖完全符合Spec及冻结契约。
- 管理员和学生页面可正确消费导入结果。
- 不修改模型、迁移、唯一约束、parser或认证权限实现。
- 全量测试和三项CI基于同一最终SHA成功。

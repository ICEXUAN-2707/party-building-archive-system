# Excel最近成功批次回滚（PR3阶段一至五）

开发基线：`develop@5c896a1a4fa69d2953cd8a82a2e79b578e978022`

分支：`feature/excel-import-rollback`

## 当前范围

本阶段只实现只读评估，不增加页面、不修改批次状态、不恢复或删除业务数据：

- 复用PR2的preview、rollback snapshot和SQLite备份公共校验接口；
- 选择当前最新`success`批次；
- 拒绝previewed、failed、rolled_back及非最新成功批次；
- 计算既有学生恢复、新学生删除及材料恢复影响数；
- 以preview冻结导入后期望状态；
- 以rollback snapshot冻结导入前恢复状态；
- 检测Student、申请记录、汇总和有效思想汇报的后续修改；
- 返回结构化冲突，不强制覆盖或部分通过。

## 公共接口

```python
get_rollback_candidate() -> ImportBatch | None
assess_rollback(batch_id: int) -> RollbackAssessment
```

`assess_rollback`不存在批次时抛出`RollbackBatchNotFound`；其他资格、证据或数据问题作为`RollbackConflict`集合返回，供后续回滚预览页面映射为HTTP 409语义。

## 冲突代码

- `BATCH_STATUS_NOT_SUCCESS`
- `BATCH_NOT_LATEST_SUCCESS`
- `ROLLBACK_EVIDENCE_INVALID`
- `PRE_IMPORT_BACKUP_INVALID`
- `SNAPSHOT_CANDIDATE_MISMATCH`
- `CURRENT_STUDENT_MISSING`
- `STUDENT_MODIFIED_AFTER_IMPORT`
- `APPLICATION_MODIFIED_AFTER_IMPORT`
- `SUMMARY_MODIFIED_AFTER_IMPORT`
- `REPORTS_MODIFIED_AFTER_IMPORT`

## 阶段四与五

`GET/POST /imports/<batch_id>/rollback/`仅允许data_admin。GET展示结构化冲突和影响统计；POST要求CSRF及精确的`confirm_batch_id`二次确认。正式恢复获取与确认导入共用的项目级跨进程锁，并在单一`transaction.atomic()`内重新执行全部评估、恢复Student及三类材料、标记`rolled_back`并写入`rollback_import`审计。任何恢复或审计失败均整批撤销，批次保持`success`。

恢复规则：导入前存在的学生逐字段恢复原来源批次及时间；申请和汇总按快照恢复或删除本批创建记录；删除当前有效思想汇报并按原主键重建旧有效集合；导入前不存在的学生仅在评估确认当前状态完全属于本批后级联删除。原文件、preview、rollback快照、SQLite备份、错误、警告和历史审计全部保留。

锁超时、重复回滚、非最新批次、证据冲突或后续修改返回409；二次确认格式错误返回400；批次不存在返回404。回滚页面不提供强制覆盖或部分恢复。

## 验证结果

阶段一至五专项覆盖资格、证据、后续修改、权限、CSRF、二次确认、新学生删除、既有学生及全部材料恢复、冲突零变化、重复回滚、审计失败原子撤销和真实双请求并发回滚。全量回归共 323 项测试通过，`manage.py check` 与迁移漂移检查均通过。

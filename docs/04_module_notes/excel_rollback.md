# Excel最近成功批次回滚（PR3阶段一至三）

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

## 后续阶段

阶段四增加仅data_admin可访问的回滚影响预览；阶段五在项目级锁和单一事务中重新评估后执行恢复。本阶段的`eligible=True`只是当前只读检查结果，正式POST仍必须重新校验全部证据和业务状态。

## 验证结果

2026-08-21当前候选通过12项阶段一至三专项测试和315项全仓库测试；`manage.py check`、迁移漂移检查和`git diff --check`通过。专项覆盖最新成功批次、各终态、非最新批次、证据缺失、四类业务数据后续修改、当前学生缺失、修改后恢复原值的时间戳检测及回滚影响统计。

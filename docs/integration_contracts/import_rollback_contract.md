# Excel导入回滚接口契约

## 1. 契约状态

| 项目 | 内容 |
| --- | --- |
| 状态 | FROZEN_SPEC / NEED_MODEL_IMPLEMENTATION |
| 版本 | Sprint 2 / 1.0 |
| 冻结日期 | 2026-08-09 |
| 提供方 | 成员1定义规则、成员7实现`imports`模块 |
| 消费方 | 回滚页面、审计、成员2集成测试 |
| 依据基线 | `develop@068c27fb7e41ec6f77299ebf3bbac68162714f63` |
| 依赖 | `excel_import_contract.md`、`admin_permission_contract.md`、`docs/spec.md` V1.2 |

业务语义已冻结；当前`develop`尚无满足本契约的变更记录模型。成员7必须先提交模型与迁移评审，评审通过后方可实现正式回滚，不得以SQLite整库覆盖或临时删除替代。

## 2. 公共入口与权限

| 功能 | 方法 | 路径 | URL名称 |
| --- | --- | --- | --- |
| 回滚预览与确认 | GET、POST | `/imports/<int:batch_id>/rollback/` | `imports:rollback` |

1. 未登录跳转管理员登录。
2. `viewer_admin`返回403。
3. 只有`data_admin`允许。
4. POST必须带CSRF并要求页面二次确认。

## 3. 拟新增变更记录模型

成员7应在`apps/imports/models.py`中提出单一模型，建议命名：

```text
ImportChangeRecord
```

冻结的最小字段语义：

| 字段 | 类型语义 | 说明 |
| --- | --- | --- |
| `import_batch` | ForeignKey | 所属批次，批次删除时级联删除仅限开发数据；生产不得随意删除批次 |
| `model_label` | 字符串 | Django模型标签，如`students.Student` |
| `object_pk` | 字符串 | 对象主键的稳定文本形式 |
| `operation_type` | 枚举 | `create`、`update`、`deactivate` |
| `before_data` | JSON | 本批写入前需要恢复的字段和值；新建对象为空对象 |
| `after_digest` | 字符串 | 本批成功后受控字段的规范化SHA-256摘要 |
| `sequence` | 正整数 | 正向写入顺序；回滚按降序执行 |
| `created_at` | 时间 | 记录创建时间 |

必须建立`import_batch + sequence`唯一约束，并为`import_batch`、`model_label + object_pk`建立查询索引。

`before_data`只允许保存契约列出的业务字段，不保存密码、Session、文件内容或任意反序列化对象。日期使用ISO `YYYY-MM-DD`，外键保存目标主键。

## 4. 记录时机与原子性

1. 变更记录必须与确认导入业务写入处于同一数据库事务。
2. 每次创建、更新或停用对象前先构造`before_data`，完成写入后计算`after_digest`。
3. 如果业务事务失败，变更记录必须一并回滚；失败批次不得留下可执行回滚记录。
4. 成功批次的变更记录不可修改或删除。
5. 仅数据库备份不构成本契约的业务回滚记录。

## 5. 可回滚批次判定

批次必须同时满足：

1. `status == success`。
2. `rolled_back_at is None`且`rolled_back_by is None`。
3. 它是按`imported_at`、`id`判定的最新成功批次。
4. 不存在时间或ID更晚的`success`批次。
5. 具备完整的`ImportChangeRecord`。
6. 每个受影响对象当前受控字段摘要与`after_digest`一致。

任一条件不满足时，GET预览必须显示不可回滚原因，POST必须拒绝且业务数据零写入。

## 6. 影响预览

GET只读展示：

- 批次和文件信息；
- 新建、更新、停用对象数量；
- 按模型分类的影响数量；
- 冲突对象数量及安全标识；
- 是否为最新成功批次；
- 是否允许正式回滚。

预览不得修改批次、变更记录或业务表。

## 7. 恢复规则

正式回滚在单一`transaction.atomic()`中按`sequence`降序处理：

1. `create`：当前摘要一致且对象没有本批之后新增的受保护依赖时删除本批创建对象；存在后续依赖则冲突并整体拒绝。
2. `update`：先校验当前摘要，再逐字段恢复`before_data`。
3. `deactivate`：恢复原`is_active`及记录的受控字段。
4. 外键恢复前必须确认目标对象仍存在，否则整体拒绝。
5. 本批替换的思想汇报按变更记录恢复旧有效状态并删除本批新建明细。
6. 不删除`ImportBatch`、上传文件、错误、警告、变更记录或`OperationLog`。
7. 不执行字段级自动合并。

## 8. 冲突策略

1. 当前摘要与`after_digest`不一致即认定存在后续人工或系统变化。
2. 发现任一冲突时整批拒绝自动回滚，不能只恢复无冲突对象。
3. 拒绝时保留当前数据和批次状态，并向管理员展示冲突摘要。
4. 本契约不提供“强制覆盖”参数。

## 9. 成功与失败行为

成功时：

1. 所有业务数据恢复完成。
2. 批次状态从`success`变为`rolled_back`。
3. 设置`rolled_back_at`和`rolled_back_by`。
4. 记录`rollback_import`，目标类型为`import_batch`，目标ID为批次主键字符串。

失败或拒绝时：

1. 业务数据和批次状态保持回滚前状态。
2. 不记录成功的`rollback_import`事件。
3. 返回不泄露内部路径或敏感数据的原因。

已回滚批次重复POST必须稳定拒绝，不重复恢复。

## 10. 契约测试

1. 匿名重定向、`viewer_admin`为403、`data_admin`允许。
2. GET只预览且数据库零写入，POST才执行。
3. 只有最新成功且未回滚批次可回滚。
4. 失败、旧成功、已回滚和无变更记录批次拒绝。
5. 新建、更新、停用及思想汇报替换可完整恢复。
6. 回滚按逆序执行并保持外键完整性。
7. 当前摘要变化、后续依赖或外键缺失时整批拒绝。
8. 中途异常使整个回滚事务撤销。
9. 成功后批次字段和审计正确。
10. 文件、错误、警告、变更记录和历史日志保留。
11. 重复回滚幂等拒绝。

## 11. 禁止行为

- 不使用SQLite文件覆盖作为Web业务回滚。
- 不删除批次、原文件、错误、警告或审计证据。
- 不跳过冲突继续部分回滚。
- 不提供强制回滚绕过摘要校验。
- 不在模型与迁移评审前编写正式回滚服务。

## 12. 实现解锁门槛

成员7开始回滚代码前必须提交并通过：

1. `ImportChangeRecord`模型设计。
2. 迁移文件及`makemigrations --check`证据。
3. JSON字段白名单和摘要规范。
4. 确认导入与变更记录同事务测试。
5. 回滚外键顺序和冲突测试方案。

在上述门槛通过前，状态保持`FROZEN_SPEC / NEED_MODEL_IMPLEMENTATION`，表示规则稳定但代码尚未获准开始。

## 13. 变更规则

可回滚判定、记录模型、恢复范围、摘要算法、冲突或事务语义变化时，必须同步更新本契约、`excel_import_contract.md`、成员7 Module Notes和成员2集成测试，并由成员1、成员7和成员2共同确认。

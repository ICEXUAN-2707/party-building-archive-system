# 历史任务卡：成员7 第二轮迭代Excel导入闭环（已废止）

> 本卡包含“确认时重新解析”“ImportChangeRecord模型”等已被2026-08-12/13决策替代的旧方案，不得继续作为开发依据。当前执行入口为[`../mvp_excel/README.md`](../mvp_excel/README.md)及两位开发者独立任务卡。

## 任务目标

实现`data_admin`专用的上传→解析→预览→确认导入→历史→审计；`ImportChangeRecord`模型、迁移和同事务证据通过评审后，再实现最近一次成功批次回滚。

## 任务背景

解析器和导入契约已稳定，但当前上传POST为405，预览和历史均为占位；正式写库依赖成员5管理员权限实现，回滚代码依赖变更记录模型与迁移评审。

## 前置依赖

- `excel_parser_contract.md`
- `admin_permission_contract.md`及成员5最终实现SHA
- 已冻结的`excel_import_contract.md`
- `import_rollback_contract.md`（`FROZEN_SPEC / NEED_MODEL_IMPLEMENTATION`）

## 允许范围

- `apps/imports/`上传、预览、确认、历史和回滚服务/视图/路由
- imports模板
- 必要且获批的导入快照或变更记录模型/迁移
- 导入与回滚测试
- `docs/04_module_notes/excel_import.md`
- `docs/integration_contracts/excel_import_contract.md`

## 禁止范围

- 不复制`parse_workbook`、角色判断或审计服务。
- 不允许viewer_admin写入或回滚。
- 不在预览阶段写Student/materials业务表。
- 不提交真实Excel、固定绝对路径或共享管理员账号。
- `ImportChangeRecord`模型、迁移和同事务测试设计评审通过前不实现临时回滚。
- 不修改学生认证和管理员查询业务。

## 接口契约

严格实现`excel_import_contract.md`冻结的上传类型、10 MiB上限、随机文件名、SHA-256、批次状态、`ParseResult`映射、预览零写入、确认幂等和事务、模型更新、错误警告落库及审计事件。回滚严格服从`import_rollback_contract.md`。

建议服务边界：

```text
create_import_preview(uploaded_file, operator)
confirm_import(batch_id, operator)
rollback_latest_import(batch_id, operator)
```

服务返回结构如需成为跨模块公共接口，必须先补充契约并经提供方、消费者和成员1确认；不得在实现中形成未记录的第二套接口。

## 实施建议

### 阶段一：上传与预览

校验`.xlsx`和10 MiB上限，随机化存储名，计算SHA-256，创建预览批次，调用`parse_workbook(Path)`并展示全部统计、错误和警告。每次GET预览重新校验哈希并解析；预览阶段业务表零写入。

### 阶段二：确认导入

重新验证文件哈希和批次状态；以`ImportBatch.id`保证幂等，全部`valid_rows`候选在单一事务内成功或失败。错误行不进入候选但不阻断其他有效行；有效行按学号新增或更新；普通可选标量空值不覆盖旧值；缺席学生不变；思想汇报明细按有效行完整替换。

### 阶段三：日志与历史

持久化错误/警告、统计和结果，调用成员5审计服务记录upload/confirm，限制原文件下载权限。

### 阶段四：回滚

先提交`ImportChangeRecord`模型、迁移、JSON白名单、SHA-256摘要规范和同事务测试设计供评审。通过后只允许回滚最新成功、未回滚且摘要无冲突的批次；二次确认；事务逆序恢复；保留文件、批次、错误、警告、变更记录和审计记录。

## 必须测试

- 非xlsx、超限、同名文件、随机存储名和哈希。
- viewer_admin 403、data_admin允许。
- 预览前后业务表逐项不变。
- ParseResult错误/警告/统计完整展示。
- 错误行被排除但其他`valid_rows`可确认；重复学号和空有效结果阻断确认。
- 重复确认幂等或明确拒绝。
- 新增学生、更新学生、空值保留、错误行保留旧数据、缺席学生不变。
- 思想汇报汇总与明细规则。
- 系统异常事务回滚，无半导入状态。
- 原文件下载权限和OperationLog。
- 模型评审通过后测试最近一次回滚、非最新拒绝、摘要冲突整批拒绝、重复回滚拒绝、证据保留及回滚后查询一致。

## 验收标准

- data_admin可完成经确认的导入闭环。
- 预览零业务写入，确认无半成功状态。
- 所有统计与ParseResult语义一致。
- 查询页面能看到导入后的数据。
- 回滚只有在契约和恢复证据完整时标记完成。

# 任务卡：成员1 第二轮迭代技术负责人

## 任务目标

冻结第二轮迭代跨模块接口，控制合并顺序，并对最终发布候选版本给出可追溯结论。

## 任务背景

认证和解析已稳定，但查询、权限和导入仍未形成闭环；旧任务与旧分支不可继续作为开发基线。

## 前置依赖

- `student_session_contract.md`
- `excel_parser_contract.md`
- `admin_permission_contract.md`
- 成员4/5/7接口确认

## 允许范围

- `docs/sprint/`
- `docs/integration_contracts/`
- `docs/member_tasks/sprint2/`
- `docs/code_review/`索引文档
- 代码审查、集成计划和发布报告

## 禁止范围

- 不代替成员修改业务代码。
- 不绕过持续集成检查或代码审查进行合并。
- 不修改冻结模型来迁就旧分支。

## 接口契约

第二阶段已冻结`student_profile_contract.md`、`admin_query_contract.md`和`excel_import_contract.md`；`import_rollback_contract.md`为`FROZEN_SPEC / NEED_MODEL_IMPLEMENTATION`。后续职责转为控制契约变更、审查成员7的`ImportChangeRecord`模型与迁移方案，并确保现有契约只在提供方和消费者共同确认后更新。

## 实施建议

先确认字段、异常和副作用，再允许编码；每个契约记录提供方、消费者、最终导入路径、状态和变更规则。

## 必须测试

- 文档路径和链接检查。
- 契约字段与实际模型/接口一致性检查。
- 最终候选版本全量测试和持续集成链接核验。

## 验收标准

- 所有跨模块调用只有一个正式来源。
- 合并顺序和最终SHA可追溯。
- 回滚模型、迁移和同事务证据未通过评审前，回滚代码不会进入业务实现。

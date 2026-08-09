# Sprint 2 评审索引

## 1. 使用原则

本索引是Sprint 2评审入口，不迁移或改写历史评审结论。发生冲突时，以最新`develop`代码、冻结契约和`docs/member_tasks/sprint2/`任务卡为准；旧分支与旧任务文档仅用于追溯问题，不能作为实现接口来源。

## 2. 当前基线与计划

| 文档 | 用途 |
| --- | --- |
| `docs/sprint/sprint2_baseline.md` | 启动SHA、稳定接口、模块状态和启动规则 |
| `docs/sprint/sprint2_plan.md` | Sprint目标、Gate、成员职责和发布门禁 |
| `docs/member_tasks/sprint2/` | Sprint 2唯一成员任务目录 |

## 3. 冻结契约

| 契约 | 状态 | 提供方 | 消费方 | 评审结论 |
| --- | --- | --- | --- | --- |
| `student_session_contract.md` | STABLE | 成员3 | 成员4 | 唯一学生身份接口，禁止建立同义契约或第二套Session解析 |
| `excel_parser_contract.md` | STABLE | 成员6 | 成员7 | 唯一解析入口，纯解析且数据库零写入 |
| `admin_permission_contract.md` | FROZEN_SPEC / NEED_IMPLEMENTATION | 成员5 | 成员5、7 | 角色与权限矩阵已冻结，成员5仍须实现正式代码 |
| `student_profile_contract.md` | FROZEN | 成员4 | 模板、成员2 | 展示语义已冻结，不冻结查询实现代码；总篇数按V1.2回退规则 |
| `admin_query_contract.md` | FROZEN | 成员5 | 模板、成员2 | 登录、POST退出、认证隔离、筛选、分页和详情语义已冻结 |
| `excel_import_contract.md` | FROZEN | 成员7 | 页面、服务、成员2 | 上传、预览零写入、确认事务、幂等和状态机已冻结 |
| `import_rollback_contract.md` | FROZEN_SPEC / NEED_MODEL_IMPLEMENTATION | 成员1、7 | 回滚服务、成员2 | 规则已冻结；通过变更记录模型与迁移评审后解锁实现 |

## 4. 成员启动检查

### 成员4：学生个人页

- [ ] 已同步并记录最新`origin/develop`完整SHA。
- [ ] 只使用`@student_required`和`request.current_student`。
- [ ] 不直接解析`student_id`，不接受目标学生ID参数。
- [ ] 不修改模型或迁移。
- [ ] 按已冻结`student_profile_contract.md`实现展示字段、空数据和更新时间语义。

### 成员5：管理员权限与查询

- [ ] 已同步并记录最新`origin/develop`完整SHA。
- [ ] 实现`admin_permission_contract.md`的唯一权限工具。
- [ ] 管理员认证使用Django Auth，不读取`student_id`。
- [ ] 管理员退出保留`student_id`；学生退出保留管理员认证。
- [ ] 不整体合并旧`feature/admin-query`。
- [ ] 按已冻结`admin_query_contract.md`实现登录、退出、筛选、分页和详情语义。

### 成员7：Excel导入

- [ ] 已同步并记录最新`origin/develop`完整SHA。
- [ ] 只调用冻结的`parse_workbook()`。
- [ ] 只消费成员5提供的权限和审计服务。
- [ ] 不复制角色判断、解析或聚合逻辑。
- [ ] 按已冻结`excel_import_contract.md`实现上传、预览和确认。
- [ ] 回滚代码等待`ImportChangeRecord`模型与迁移评审通过后开始。

## 5. PR评审门禁

每个候选PR必须检查：

1. 同步基线SHA和最终候选SHA均可追溯。
2. 修改文件全部位于任务卡允许范围。
3. 没有重复认证、权限、解析或审计实现。
4. 没有为迁就旧分支修改冻结模型。
5. 契约、Module Notes和测试引用同一正式接口。
6. `check`、`makemigrations --check`、迁移、相关测试和全量测试完成。
7. Repository policy、Ubuntu和Windows检查属于同一最终SHA。
8. PR说明列出接口变化、迁移、测试结果和未完成事项。

## 6. 历史资料路由

| 路径 | 用途 | Sprint 2约束 |
| --- | --- | --- |
| `docs/reviews/` | 历史代码审查 | 只读参考 |
| `docs/member_tasks/repair/` | PR修复任务 | 只读参考，不继续作为新任务 |
| `docs/member_tasks/review_followup_20260727/` | 旧后续规格 | 用于识别遗留缺陷，不作为最终接口 |
| 旧远端功能分支 | 历史实现 | 禁止整体合并，只可人工核对小段业务逻辑 |

## 7. 第一阶段评审结论

第一阶段允许成员继续使用既定协作分支或工作环境，不要求额外创建分支。进入编码前仍必须同步并记录最新`develop`。学生认证与Excel解析已具备唯一正式来源；管理员权限只有冻结规范、没有实现。

## 8. 第二阶段评审结论

`student_profile_contract.md`、`admin_query_contract.md`和`excel_import_contract.md`已冻结，可分别作为成员4、5、7的开发依据。`import_rollback_contract.md`业务规则已冻结，但当前模型不能提供可靠恢复证据；成员7须先通过`ImportChangeRecord`模型、迁移和事务测试设计评审，方可进入回滚实现。

交叉核查发现旧成员任务资料中“`reported_total_count=None`显示未知”与`docs/spec.md` V1.2冲突。正式契约以V1.2为准：填报值为空时展示`calculated_date_count`并标注计算来源。后续任务卡同步不得反向修改冻结契约。

# Excel三PR双人协作任务索引

## 当前效力

| 项目 | 内容 |
| --- | --- |
| 生效日期 | 2026-08-13 |
| 开发基线 | `develop@5765e54c1cbe69d7521cff1e6aa09396d313429e` |
| 目标 | 完成Excel上传预览、正式导入、最近批次回滚闭环；之后进入上线收尾 |
| 业务依据 | `docs/spec.md` V1.2 |
| 阶段方案 | `docs/sprint/mvp_convergence_governance_plan.md` |
| 导入契约 | `docs/integration_contracts/excel_import_contract.md` |
| 回滚契约 | `docs/integration_contracts/import_rollback_contract.md` |

本目录任务卡是当前Excel阶段的直接作业入口。旧的`sprint2/07_excel_import_task.md`保留为历史记录，其中“重新解析”“ImportChangeRecord模型”等与现行决策冲突的内容不再适用。

## 人员与PR分工

| 开发者 | 主责 | 交叉责任 |
| --- | --- | --- |
| 开发者A | PR1上传/预览/历史/下载；PR3回滚/备份/恢复工具 | 审查PR2对存储、快照和哈希接口的消费 |
| 开发者B | PR2正式导入、事务、导入前证据和跨模块验证 | 审查PR3是否完整逆转PR2写入语义 |

任务卡：

- [开发者A任务卡](developer_a_excel_preview_rollback.md)
- [开发者B任务卡](developer_b_excel_confirm_import.md)

## 强制执行顺序

```text
PR1（A）合入develop
→ PR2（B）从最新develop开始并合入
→ PR3（A）从最新develop开始并合入
→ A/B共同完成全链路验收
→ 进入上线收尾
```

不得并行开发尚未具备基线的后序PR，不得通过复制未合并代码、临时兼容层或跨分支cherry-pick形成隐性依赖。

## 公共接口归属

1. PR1由A冻结批次目录、预览JSON schema、SHA校验和安全文件读取接口。
2. PR2只能消费PR1合入后的公共接口；如确需变更，先在PR2中更新契约并由A Review。
3. PR2由B冻结回滚JSON schema、业务字段覆盖算法和导入统计语义。
4. PR3只能消费PR2合入后的快照和写入语义；如无法完整逆转，必须退回PR2修正，禁止在PR3猜测。
5. 权限统一来自`apps.accounts.permissions`，审计统一来自`apps.audit.services`，解析统一来自`apps.imports.parser.parse_workbook`。

## 三PR共同门禁

每个候选最终SHA必须满足：

- 基于前序PR合并后的最新`develop`；
- `python manage.py check`；
- `python manage.py makemigrations --check --dry-run`；
- 在空临时SQLite执行`migrate --noinput`；
- 全量测试通过；
- `git diff --check`通过；
- Repository policy、Ubuntu、Windows三项CI成功；
- Module Notes、契约实现状态、任务表与最终SHA一致；
- 不提交真实Excel、真实学生数据、数据库、备份、快照、上传文件或`.env`。

## 阶段完成定义

只有以下条件全部满足，才可声明Excel阶段完成并进入上线收尾：

1. data_admin可完成上传、预览、确认和最近成功批次回滚。
2. viewer_admin只能读取历史与详情，不能上传、下载原文件、确认或回滚。
3. 预览跨请求完全依赖服务端快照，且四类业务表零写入。
4. 确认候选集合整批原子，失败证据保留，重复确认返回409。
5. 最近成功批次可在无冲突时整批恢复，冲突时数据库零变化。
6. 管理员页和学生页能正确查询导入及回滚后的数据。
7. 约1500条合成数据完成端到端性能与正确性验收。
8. 全仓库测试和双平台CI通过，文档状态全部回填。

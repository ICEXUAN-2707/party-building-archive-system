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

发生冲突时按以下顺序裁决：`docs/spec.md`、最新冻结契约、`sprint2_contract_decisions.md`、`mvp_convergence_governance_plan.md`、本目录任务卡、历史任务文件。历史任务文件不得恢复为当前作业入口，也不得形成兼容旧方案的第二套接口。

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

## PR2事务与证据一致性门禁

PR2必须把“导入前证据”和“正式写入”纳入同一个串行化保护窗口，冻结执行顺序为：

```text
权限/方法/批次检查
→ 获取导入串行化控制
→ 重新读取previewed批次
→ 校验原文件、preview及全部候选
→ 读取导入前业务状态
→ 原子生成rollback_snapshot.json及SHA
→ 生成SQLite一致性备份并执行integrity_check
→ 进入正式业务事务并再次校验状态与证据
→ 写入全部业务数据、统计、批次状态和confirm_import审计
→ 提交事务
→ 释放串行化控制
```

要求：

1. 快照、SQLite备份和正式写入之间不得允许另一确认请求改变受控数据。
2. 同一批次或不同批次的近同时确认不得形成交叉快照、半导入或双成功；SQLite锁限制必须在Module Notes和测试中说明。
3. `confirm_import`成功审计与业务写入处于同一成功事务；审计失败不得留下已成功但无审计的导入。
4. 业务事务失败后，在独立可提交步骤将批次标为`failed`并保存安全错误摘要；不得覆盖原始文件、preview、rollback快照、SHA或SQLite备份。
5. `failed`批次不得重试确认，只能重新上传。
6. 任一保护文件生成、刷盘、原子替换、哈希或完整性检查失败时，业务表必须零写入。

## 阶段完成定义

只有以下条件全部满足，才可声明Excel阶段完成并进入上线收尾：

1. data_admin可完成上传、预览、确认和最近成功批次回滚。
2. viewer_admin只能读取历史与详情，不能上传、下载原文件、确认或回滚。
3. 预览跨请求完全依赖服务端快照，且四类业务表零写入。
4. 确认候选集合整批原子，失败证据保留，重复确认返回409。
5. 最近成功批次可在无冲突时整批恢复，冲突时数据库零变化。
6. 管理员页和学生页能正确查询导入及回滚后的数据。
7. 约1500条合成数据完成端到端性能、正确性、失败恢复与重启后持久性验收。
8. 全仓库测试和双平台CI通过，文档状态全部回填。

## 约1500条联合验收门禁

A/B必须在PR3合入后的同一`develop`候选SHA上共同执行。合成数据不得包含真实学生信息，并须记录生成脚本版本和随机种子。

数据至少覆盖九个支部、新增与更新学生、空值和0、总篇数不一致、多次及空思想汇报、重复日期、重复学号、非法日期、未知支部、非法阶段、多Sheet、空Sheet、失败Sheet、列错位、同名上传、错误扩展名和超限文件。

完整链路必须覆盖：

```text
上传→预览→确认→管理员查询→学生本人查询
→ 第二次导入→最近成功批次回滚
→ 管理员/学生查询恢复→审计与证据检查→服务重启后复查
```

验收报告必须绑定最终SHA，并记录实际输入量、有效/跳过/错误/警告统计、新建/更新数量、导入与回滚前后断言、文件哈希、批次状态、审计事件、总耗时和失败场景。只验证HTTP状态码、只提供截图或使用不同SHA的测试结果均不通过。

## 上线门禁

联合验收通过只表示可以进入上线收尾，不等于可以直接上线。最终Go/No-Go前必须完成：

1. 生产环境`DEBUG=False`，密钥、主机、CSRF和路径配置全部来自环境变量；
2. 使用生产级WSGI服务，不以`runserver`作为上线方式；
3. 静态文件、数据库、上传、快照、备份和日志目录具备明确持久化及权限方案；
4. 在干净Windows/Linux环境按文档完成安装、迁移、九支部初始化、管理员创建和启动；
5. 服务重启后数据库、历史、原文件、快照和备份仍可用；
6. 执行数据库备份、`restore_import_backup --verify-only`和受控停机恢复演练；
7. 同一最终SHA通过Repository policy、Ubuntu、Windows、全量测试、迁移检查、污染检查和浏览器冒烟测试；
8. 发布报告列明版本SHA、配置项、部署步骤、备份恢复证据、已知限制、回退方案和最终Go/No-Go结论。

任何一项未通过，状态保持“上线收尾/阻塞”，不得标记“已上线”。

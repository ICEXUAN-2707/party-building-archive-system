# 当前项目状态

## 状态基线

| 项目 | 内容 |
| --- | --- |
| 核验日期 | 2026-08-21 |
| 集成分支 | `develop` |
| 核验 SHA | `c113c1e18a3c018afc7f584d3eba4506acd74dbb`（PR2候选基线） |
| 最新合并 | PR #19，Excel上传、服务端预览、历史与受控下载 |
| 本地验证 | `check`通过；无迁移变化；298项测试通过；`git diff --check`通过 |
| 业务规范 | `docs/spec.md` |
| 当前作业方案 | `docs/sprint/mvp_convergence_governance_plan.md` |

本文件是项目当前状态的唯一入口。历史 Review、返工单和旧 Sprint 计划只说明当时情况，不覆盖本文件。

## 模块状态

| 模块 | 状态 | 正式入口或说明 |
| --- | --- | --- |
| 工程基础、模型、迁移、CI | 已完成/持续维护 | Django五App、双平台CI |
| 学生认证与Session | 已合入且稳定 | `apps.accounts.student_access` |
| 学生个人档案 | 已合入且稳定 | `students:student_profile` |
| Excel纯解析 | 已合入且稳定 | `apps.imports.parser.parse_workbook` |
| 管理员认证、查询、权限、审计 | 已合入且稳定 | PR #3；管理员专项59项通过 |
| Excel上传、服务端预览、历史、下载 | 已合入 | PR #19；`develop@c113c1e` |
| Excel正式导入 | PR2实现候选 | 权限、证据、快照、备份、原子写入、审计已实现，等待Review和CI |
| 最近成功批次回滚与备份 | 部分完成 | PR2已生成回滚证据；PR3恢复入口待开发 |
| Docker与生产部署 | 未开始 | 业务闭环后推进 |

## 契约实现矩阵

| 契约 | 契约状态 | 实现状态 |
| --- | --- | --- |
| `student_session_contract.md` | 冻结 | 已实现 |
| `student_profile_contract.md` | 冻结 | 已实现 |
| `excel_parser_contract.md` | 冻结 | 已实现 |
| `admin_permission_contract.md` | 冻结 | 已实现 |
| `admin_query_contract.md` | 冻结 | 已实现 |
| `excel_import_contract.md` | 现行决策已冻结并完成规则校准 | PR1已合入；PR2实现候选 |
| `import_rollback_contract.md` | 现行决策已冻结 | PR2证据生成已实现；PR3恢复未实现 |

## 已确认决策

1. 导入历史允许 `viewer_admin` 和 `data_admin` 查看。
2. 原始 Excel 仅允许 `data_admin` 通过受控 View 下载。
3. 管理员退出同时清除管理员认证和 `student_id`。
4. 预览跨请求采用服务端快照，不信任客户端重建结果。
5. 空解析结果允许形成预览，但不得确认导入。
6. 重复确认、空预览确认和状态冲突返回 HTTP 409；普通输入错误返回400。
7. 第一版使用服务端 JSON 业务快照完成最近成功批次回滚，SQLite 导入前备份作为灾难恢复保障。
8. 第一版不新增数据库快照模型或快照迁移，不修改思想汇报唯一约束。
9. 导入失败仍保留原始文件、批次和错误记录。
10. Excel工作拆成上传预览、正式导入、回滚备份三个PR。

## 当前边界

管理员模块和Excel PR1已经合入；PR2从最新`develop@c113c1e`完成正式事务导入候选。下一步是完成交叉Review、全量测试和CI并合入develop；PR2合入前不得从候选分支并行开发PR3。

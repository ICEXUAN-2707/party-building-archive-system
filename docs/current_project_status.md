# 当前项目状态

## 状态基线

| 项目 | 内容 |
| --- | --- |
| 核验日期 | 2026-08-21 |
| 集成分支 | `develop` |
| 核验 SHA | `197d240844dc5d4c34ca7ccc17ebf96578958b3d` |
| 最新合并 | PR #21，最近成功批次安全回滚阶段一至五 |
| 本地验证 | PR #21双平台CI通过；阶段六15项专项及全仓库338项测试通过；系统检查和迁移漂移检查通过 |
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
| Excel正式导入 | 已合入 | PR #20；`develop@5c896a1` |
| 最近成功批次回滚与备份 | PR3阶段一至六实现候选 | 业务回滚已合入；灾难恢复命令、恢复前保护备份及原子替换已实现，待全量门禁和Review |
| Docker与生产部署 | 未开始 | 业务闭环后推进 |

## 契约实现矩阵

| 契约 | 契约状态 | 实现状态 |
| --- | --- | --- |
| `student_session_contract.md` | 冻结 | 已实现 |
| `student_profile_contract.md` | 冻结 | 已实现 |
| `excel_parser_contract.md` | 冻结 | 已实现 |
| `admin_permission_contract.md` | 冻结 | 已实现 |
| `admin_query_contract.md` | 冻结 | 已实现 |
| `excel_import_contract.md` | 现行决策已冻结并完成规则校准 | PR1、PR2已合入 |
| `import_rollback_contract.md` | 现行决策已冻结 | PR3阶段一至六实现候选 |

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

管理员模块、Excel PR1、PR2及PR3业务回滚已经合入。阶段六灾难恢复命令完成实现候选后，下一步是开发者B正式Review及约1500条合成数据联合验收；真实数据到达前以合成Excel完成同路径预演。

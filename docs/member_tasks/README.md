# 成员任务总索引

## 当前基线

| 项目 | 内容 |
| --- | --- |
| 更新日期 | 2026-08-13 |
| 集成分支 | `develop` |
| 基线提交 | `5765e54c1cbe69d7521cff1e6aa09396d313429e` |
| 当前状态入口 | `docs/current_project_status.md` |
| 第一版作业方案 | `docs/sprint/mvp_convergence_governance_plan.md` |

业务规则以`docs/spec.md`为准，协作规则以`docs/02_git_workflow.md`为准。本目录中`repair/`和`review_followup_20260727/`记录历史Review与返工过程，不代表当前develop状态。

## 当前任务状态

Excel三PR已拆分为两位开发者的当前有效独立任务卡，见[`mvp_excel/README.md`](mvp_excel/README.md)。`sprint2/07_excel_import_task.md`中的旧方案仅保留历史参考，不覆盖2026-08-13已审核决策。

| 成员 | 模块 | 当前状态 | 当前职责 | 直接依赖 |
| --- | --- | --- | --- | --- |
| 成员1 | 技术与文档治理 | 进行中 | 契约、Review、作业边界和集成门禁 | 全员交付 |
| 成员2 | 配置、CI、集成测试 | 基础完成/持续维护 | 双平台CI、跨模块回归、发布候选验证 | 各功能候选SHA |
| 成员3 | 学生认证 | 已完成/维护 | 维护Session冻结接口和消费者支持 | 无 |
| 成员4 | 学生个人档案 | 已完成/维护 | 学生页面回归及导入后数据验证 | 学生认证 |
| 成员5 | 管理员查询与权限 | 已完成/维护 | 维护管理员认证、统一权限、查询和审计冻结接口 | 无 |
| 成员6 | Excel解析 | 已完成/维护 | 维护`parse_workbook`及消费者支持 | 无 |
| 开发者A/B | Excel导入与回滚 | 待开始 | 按三个串行PR完成上传预览、正式导入、回滚备份 | 管理员权限、解析器；详见mvp_excel任务卡 |

## 执行顺序

```text
文档治理
→ 管理员认证、权限、查询与审计
→ Excel上传、服务端预览、历史与下载
→ Excel正式事务导入
→ 最近成功批次回滚与SQLite备份
→ 全链路集成及文档封板
```

## 作业边界

- 文档治理不得修改业务代码、模板、测试、模型、迁移或Spec。
- 管理员模块不得进入Excel业务，不得修改学生认证契约。
- Excel导入模块只消费统一管理员权限、审计服务和`parse_workbook`，不得复制权限或解析逻辑。
- 第一版不新增数据库快照模型或迁移，不修改思想汇报唯一约束。
- 历史任务卡不得作为当前接口状态依据；当前状态以状态页和契约状态头为准。

## CI门禁

每个最终候选SHA必须通过：

```text
Repository policy
Django tests (ubuntu-latest)
Django tests (windows-latest)
```

并执行`check`、迁移检查、`migrate`、全量测试及`git diff --check`。旧SHA、其他分支或截图不能替代当前候选证据。

# 成员任务总索引

## 1. 文档基线

本索引依据以下基线更新：

```text
更新日期：2026-07-28
集成分支：develop
基线提交：3a0e41b
CI修复：PR #7，测试SHA 30941da6
CI成功运行：30328443814
```

业务规则以`docs/spec.md`为准，Git协作以`docs/02_git_workflow.md`为准。详细任务卡位于`review_followup_20260727/`，CSV汇总位于`member_task_summary.csv`。

## 2. 当前总体结论

1. Sprint 0骨架已经形成`develop`基线。
2. CI已可用，所有新PR必须通过Repository policy、Ubuntu和Windows三项检查。
3. PR #3指向`develop`，但仍为Request Changes且功能分支落后当前基线。
4. PR #4错误指向`main`，必须由成员6基于最新`develop`返工。
5. PR #6错误指向`main`、分支源头错误且存在冲突，必须由成员3基于最新`develop`返工。
6. 成员4依赖成员3认证接口，成员7依赖成员5权限接口和成员6解析接口。
7. 当前不能把PR #3、#4或#6直接作为Sprint 1集成候选。

## 3. 成员任务总览

| 成员 | 角色 | 当前任务 | 状态 | 分支/PR | 直接依赖 | 详细任务卡 |
| --- | --- | --- | --- | --- | --- | --- |
| 成员1 | 项目负责人 | 接口冻结、Review与集成门禁 | 进行中 | `docs/sprint1-integration-contracts` | 全员交付 | [01_lead_spec.md](review_followup_20260727/01_lead_spec.md) |
| 成员2 | 技术架构 | 配置基线、CI维护 | 基础完成/持续维护 | `develop@3a0e41b`、PR #7 | 成员1审批分支保护 | [02_architecture_spec.md](review_followup_20260727/02_architecture_spec.md) |
| 成员3 | 学生认证 | 登录、Session和访问保护 | 打回重做 | 关闭/转Draft PR #6；新建返工PR | 成员1接口冻结 | [03_student_auth_spec.md](review_followup_20260727/03_student_auth_spec.md) |
| 成员4 | 学生展示 | 本人档案页与联调 | 阻塞 | `feature/student-profile`尚无远端PR | 成员3合格认证接口 | [04_student_profile_spec.md](review_followup_20260727/04_student_profile_spec.md) |
| 成员5 | 管理员查询 | 权限、筛选、详情和审计修复 | Request Changes | PR #3 | 最新`develop`、成员1接口冻结 | [05_admin_query_fix_spec.md](review_followup_20260727/05_admin_query_fix_spec.md) |
| 成员6 | Excel解析 | 生产解析入口和契约修复 | 打回重做 | 关闭/转Draft PR #4；新建返工PR | 冻结Excel规则 | [06_excel_parser_fix_spec.md](review_followup_20260727/06_excel_parser_fix_spec.md) |
| 成员7 | Excel导入 | 消费契约与测试设计 | 阻塞 | 正式开发后使用`feature/excel-import` | 成员5、成员6 | [07_excel_import_preparation_spec.md](review_followup_20260727/07_excel_import_preparation_spec.md) |

## 4. 推荐执行顺序

```text
成员1冻结跨模块接口
├── 成员3基于最新develop重做认证
│   └── 成员4实现个人页并完成学生端联调
├── 成员5同步develop并修复PR #3
│   └── 成员7确认导入权限消费方式
└── 成员6基于最新develop重做解析器
    └── 成员7确认ParseResult消费方式

成员2持续维护CI，覆盖所有成员PR
成员1在依赖完成后组织最终集成
```

## 5. 统一Git要求

1. 开发前执行`git fetch origin`并从最新`origin/develop`创建功能或返工分支。
2. 功能PR目标必须为`develop`，不得直接向`main`提交业务功能。
3. 不得使用强推、历史重写或删除迁移文件处理返工。
4. 旧分支基线错误时应建立干净返工分支，只迁移人工复核后的任务范围内改动。
5. PR必须记录基线SHA、最终测试SHA、执行命令和CI链接。

## 6. 统一CI门禁

最终待合并SHA必须同时通过：

```text
Repository policy
Django tests (ubuntu-latest)
Django tests (windows-latest)
```

规则：

1. PR新增提交、解决冲突或同步`develop`后，必须以新SHA重新完成全部检查。
2. 旧SHA、其他分支、截图或本地测试不能替代当前PR的CI。
3. 任一检查失败、取消、跳过或仍在运行时不得合并。
4. CI成功不替代人工Review、接口审查和任务范围审查。

## 7. 集成门禁

形成Sprint 1集成候选前必须满足：

1. 成员3的新返工PR完成并与成员4联调。
2. 成员5的PR #3完成Request Changes。
3. 学生身份只能来自Session键`student_id`。
4. `viewer_admin`和`data_admin`权限由后端验证。
5. 所有候选PR绑定最终SHA并通过三项CI检查。
6. 成员1输出明确的Demo可用性结论。

## 8. 待负责人决策

1. 是否将三项CI检查设置为`develop`分支保护必需项。
2. 是否要求PR #4、PR #6立即关闭，或先转为Draft保留审查记录。
3. `docs/member_tasks/00_integration_contracts.md`由成员1何时补齐。
4. 成员5是继续修复PR #3，还是基于最新`develop`建立干净返工分支。

# Sprint 2 启动基线

## 1. 基线记录

| 项目 | 内容 |
| --- | --- |
| 记录日期 | 2026-08-09 |
| 远端分支 | `origin/develop` |
| 启动基线SHA | `068c27fb7e41ec6f77299ebf3bbac68162714f63` |
| 最新合并 | PR #14：成员7导入准备规格 |
| 协作方式 | 使用既定协作分支或工作环境，不要求成员额外创建分支 |

成员4、5、7开始实现前必须拉取最新远端引用，在自己的既定协作环境中同步并记录上述基线或更新后的`origin/develop`。同步基线不代表允许整体合并旧功能分支；旧分支只能作为只读参考，复用内容必须人工核对并迁移。

## 2. 基线差异自检

`5ff87c36eaa44194bb44e7ccac2f59a28c416477`至本启动基线之间只有以下变化：

```text
docs/member_tasks/review_followup_20260727/07_excel_import_preparation_spec.md
```

该变化没有修改业务代码、测试、模型、迁移或`docs/integration_contracts/`中的冻结契约。原`develop@5ff87c3`已验证的147项测试及迁移结果可作为启动参考，但不能替代各候选SHA和最终发布候选的重新测试。

## 3. 稳定模块与正式入口

### 学生认证

| 项目 | 冻结内容 |
| --- | --- |
| 契约 | `docs/integration_contracts/student_session_contract.md` |
| 公共模块 | `apps/accounts/student_access.py` |
| 当前学生 | `get_current_student(request)` |
| 访问保护 | `student_required(view_func)` |
| 身份传递 | `request.current_student` |
| Session键 | `student_id`，值为严格正整数`Student.id` |
| 学生退出 | 只删除`student_id`，保留Django管理员认证 |

成员4只能消费上述正式接口，不得重新实现登录、退出、Session解析或目标学生选择。

### Excel解析

| 项目 | 冻结内容 |
| --- | --- |
| 契约 | `docs/integration_contracts/excel_parser_contract.md` |
| 正式入口 | `apps.imports.parser.parse_workbook(file_path: Path) -> ParseResult` |
| 副作用 | 纯解析，数据库零写入 |

成员7只能消费`ParseResult`，不得复制解析或统计逻辑。

### 管理员权限

| 项目 | 当前状态 |
| --- | --- |
| 契约 | `docs/integration_contracts/admin_permission_contract.md` |
| 规范状态 | 已冻结 |
| 代码状态 | 待成员5实现 |
| 角色 | `viewer_admin`、`data_admin` |

已确认认证隔离规则：

1. 管理员退出只清除Django管理员认证并保留`student_id`。
2. 学生退出只删除`student_id`并保留Django管理员认证。
3. 管理员权限只读取Django认证和`AdminUser.role`，不得读取`student_id`。

## 4. 模块启动状态

| 模块 | 状态 | 启动结论 |
| --- | --- | --- |
| student auth | STABLE | 成员3维护，成员4直接消费 |
| excel parser | STABLE | 成员6维护，成员7直接消费 |
| student profile | NEED_UPDATE | 从当前基线干净重建只读页面，不复用旧模型或迁移 |
| admin permission/query | NEED_UPDATE | 实现已冻结权限规范并人工迁移可用查询逻辑 |
| excel import | BLOCKED | 等待导入与回滚契约冻结 |
| audit | NOT_STARTED | 成员5提供统一服务，成员7消费 |

## 5. 启动规则

1. 不要求成员额外创建分支。
2. 每项实现必须记录所同步的`origin/develop`完整SHA。
3. 不得整体合并旧学生个人页或管理员查询分支。
4. 不得复制学生认证、管理员权限或Excel解析逻辑。
5. 契约冻结的是跨模块可观察行为，不冻结实现代码文件。
6. 每个PR只修改任务卡允许范围，并以最终SHA重新完成规定测试与持续集成检查。

## 6. 第一阶段结论

Sprint 2启动基线唯一且可追溯；成员可以继续使用既定协作分支或工作环境，但必须同步并记录最新`develop`。学生认证和Excel解析可直接消费；管理员权限待实现；学生个人页、管理员查询和Excel导入不得以占位URL可访问作为功能完成证据。

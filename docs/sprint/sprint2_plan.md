# Sprint 2 开发计划

## 1. 基线与审计范围

| 项目 | 内容 |
| --- | --- |
| 计划基线 | `develop@068c27fb7e41ec6f77299ebf3bbac68162714f63` |
| 阶段 | Sprint 1结束，Sprint 2规划 |
| 已合并稳定模块 | 学生认证、Excel纯解析 |
| 本轮原则 | 不沿用旧任务状态；成员在既定协作分支或工作环境中同步本基线或更新后的`develop`，不要求额外创建分支 |
| 审计资料 | `docs/spec.md`、`docs/integration_contracts/`、`docs/member_tasks/`、`docs/reviews/`、当前代码与远端分支 |

仓库当前没有`docs/code_review/`目录。现有Review证据分散在`docs/reviews/`、`docs/member_tasks/repair/`和`docs/member_tasks/review_followup_20260727/`，Sprint 2由成员1统一整理索引，但不迁移或改写历史结论。

## 2. Project Health Audit

### 2.1 Module Status

| 模块 | 负责人 | 状态 | 说明 |
| --- | --- | --- | --- |
| student auth | 成员3 | STABLE | 已合入；`student_id`、`get_current_student()`、`student_required()`、POST退出已冻结并有安全测试 |
| excel parser | 成员6 | STABLE | 已合入；唯一入口`parse_workbook(Path) -> ParseResult`已冻结，纯解析且数据库零写入 |
| admin query | 成员5 | NEED_UPDATE | 远端分支落后`develop`31个提交；与学生认证在accounts路由/视图冲突；正式管理员登录和权限尚未进入develop |
| student profile | 成员4 | NEED_UPDATE | develop仍为公开占位页；旧分支含重复模型、三份越界迁移和临时修复，禁止直接合并 |
| excel import | 成员7 | BLOCKED | 只有占位页面；导入契约已冻结，仍依赖管理员权限实现；回滚代码依赖变更记录模型与迁移评审 |
| audit | 成员5提供、成员7消费 | NOT_STARTED | 只有`OperationLog`模型；`record_operation_log()`服务及业务事件尚未进入develop |

### 2.2 Interface Status

| Contract | 状态 | 消费者 |
| --- | --- | --- |
| student auth | STABLE；规范文件为`student_session_contract.md` | 成员4学生个人页、其他学生只读页面 |
| excel parser | STABLE；`excel_parser_contract.md` | 成员7上传、预览和确认导入 |
| admin permission | FROZEN_SPEC / NEED_IMPLEMENTATION；契约已存在但develop无`permissions.py`实现 | 成员5查询、成员7导入与回滚 |
| student profile | FROZEN；`student_profile_contract.md` | 学生页面模板、学生流程集成测试 |
| admin query | FROZEN；`admin_query_contract.md` | 管理员模板、成员2集成测试 |
| excel import | FROZEN；`excel_import_contract.md` | 上传、预览、确认、历史、审计 |
| import rollback | FROZEN_SPEC / NEED_MODEL_IMPLEMENTATION；`import_rollback_contract.md` | 回滚服务、审计、成员2集成测试 |

`student_auth_contract`不得再创建同义文件；其唯一规范载体继续使用`student_session_contract.md`。如确需更名，必须一次性更新代码注释、Module Notes和成员4测试，不允许双文件并存。

### 2.3 Technical Debt

| 优先级 | 技术债 | 影响 | Sprint 2处理 |
| --- | --- | --- | --- |
| P0 | 学生个人页、管理员查询页、导入页目前均可匿名访问占位URL | 权限闭环不存在，状态码不能代表业务可用 | 成员4/5/7分别在后端入口接入冻结权限 |
| P0 | 管理员权限契约已有但实现未合入 | Excel导入无法安全开发，viewer/data_admin无实际差异 | 成员5先交付唯一权限工具和管理员认证 |
| P0 | 学生个人页旧分支重复创建`ApplicationRecord`、`IdeologicalReport`并修改`Student.branch` | 破坏冻结模型并产生双数据源 | 废弃旧净差异，从最新develop干净重建页面 |
| P0 | 回滚规则已冻结，但`ImportChangeRecord`模型与迁移尚未评审实现 | 当前仍无法生成可验证的恢复证据 | 成员7先提交变更记录模型、迁移和同事务测试设计评审 |
| P1 | 管理员查询旧分支落后且与认证模块冲突 | 直接合并会覆盖稳定学生认证 | 人工迁移业务差异，不整体合并旧分支 |
| P1 | README和首页仍声明学生认证、Excel解析未实现 | 交接信息与develop不一致 | 成员1在Sprint 2集成后更新状态文档 |
| P1 | 现有全量测试验证模块较多，但没有develop上的学生完整页面、管理员查询、上传预览端到端闭环 | 模块通过不等于业务闭环通过 | 成员2建立跨模块集成测试门禁 |
| P2 | Review文档目录与命名不统一，旧任务汇总状态过期 | 新成员可能读取错误任务或契约 | 新增Sprint 2唯一任务目录和Review索引 |
| P2 | 旧远端分支长期保留且作者信息部分仍为“你的名字” | 可追溯性和误合并风险 | 不从旧分支继续开发；成员提交前校验Git身份 |
| P3 | 部分占位模板和首页导航在权限实现前展示所有入口 | 用户体验不完整，但后端安全优先 | 后端门禁完成后再调整导航可见性 |

## 3. Current Integration Test

原业务代码审计环境为`develop@5ff87c3`，全量147项测试通过，迁移成功。Sprint 2启动基线已前移至`develop@068c27fb7e41ec6f77299ebf3bbac68162714f63`；新增提交仅更新成员7导入准备规格，未修改业务代码、测试、模型、迁移或冻结契约，因此继承该业务测试基线，发布候选仍须重新执行全量测试。

### 3.1 学生流程

| 步骤 | 结果 | 结论 |
| --- | --- | --- |
| 姓名+学号登录 | POST返回302并写入严格整数`student_id` | 已支持 |
| 登录后进入`/students/me/` | 返回200 | 仅URL可达 |
| Session身份 | 等于数据库`Student.id` | 正确 |
| 个人数据展示 | 页面不包含当前学生姓名，仍显示“占位” | 未支持 |
| 未登录访问个人页 | 返回200 | 权限未接入，P0缺口 |

结论：认证接口稳定，但学生查询闭环尚未完成。

### 3.2 管理员流程

| 步骤 | 结果 | 结论 |
| --- | --- | --- |
| 管理员登录GET | 200占位页 | 仅入口存在 |
| 管理员登录POST | 405 | 未实现 |
| 匿名访问学生列表 | 200占位页 | 权限未实现 |
| viewer_admin列表/详情 | 200占位页 | 无真实查询 |
| viewer_admin访问上传 | 200占位页 | 应为403，当前不符合契约 |
| data_admin访问上传 | 200占位页 | 仅占位，无业务 |

结论：admin permission只有文档契约，没有可消费实现；管理员流程整体不可验收。

### 3.3 Excel流程

| 步骤 | 状态 | 说明 |
| --- | --- | --- |
| 保存上传文件 | NOT_STARTED | GET占位，POST返回405 |
| 解析 | STABLE | `parse_workbook(Path)`可用 |
| 预览 | NOT_STARTED | 仅占位模板，无ParseResult消费 |
| 确认导入 | NOT_STARTED | 无服务、事务和幂等实现 |
| 日志 | NOT_STARTED | 只有模型和权限契约中的事件名称 |
| 回滚 | BLOCKED | 规则已冻结；`ImportChangeRecord`模型、迁移和同事务证据尚未评审实现 |

## 4. Sprint目标

建立稳定查询闭环，并完成可审查的Excel导入闭环：

1. 学生登录后只能查看Session对应的本人材料。
2. viewer_admin和data_admin均可按冻结条件查询学生，只有data_admin可进入导入业务。
3. Excel上传、解析、预览、确认导入、历史、审计和最近一次成功批次回滚形成单一服务链。
4. 所有新跨模块接口先冻结、后编码，最终在同一`develop`候选SHA完成端到端测试。

回滚业务规则已冻结；若`ImportChangeRecord`模型、迁移和同事务记录方案在Sprint中点前未通过评审，Sprint 2的承诺范围降级为“上传→解析→预览→确认导入→审计”，回滚代码保持BLOCKED，不得以不可验证的临时实现代替。

## 5. 下一轮开发顺序

### Gate 0：契约冻结与基线同步

1. 成员1创建Sprint 2契约草案和Review门禁。
2. 成员5、4、7分别确认消费者/提供方字段。
3. 所有人在既定协作分支或工作环境中同步并记录最新`develop`基线；不要求额外创建分支，仍禁止直接合并旧PR净差异。

### Gate 1：管理员权限与两条查询链并行

1. 成员5先交付管理员登录、唯一权限工具和审计服务最小实现。
2. 成员4基于稳定学生认证并行重建学生个人页。
3. 成员2为权限矩阵和学生身份建立集成门禁。

### Gate 2：管理员查询与学生个人页合入

1. 先合并成员5权限基础和管理员查询。
2. 合并成员4学生个人页。
3. 在最新develop上执行学生、viewer_admin、data_admin三身份回归。

### Gate 3：Excel上传与预览

1. 成员7只调用`parse_workbook()`，接入`data_admin_required`。
2. 保存文件、校验类型/大小/哈希，生成预览批次。
3. 显示Sheet、有效行、错误和警告；预览阶段业务表零写入。

### Gate 4：确认导入、审计与回滚

1. 按已冻结契约实现确认导入事务、幂等和字段映射。
2. 实现确认导入及OperationLog。
3. 只有`ImportChangeRecord`模型、迁移和同事务证据通过评审后，才实现最近一次成功批次回滚。

### Gate 5：Release Candidate

成员2组织全量迁移、双平台CI、污染检查和端到端验收；成员1给出最终PASS/NEED_FIX。

## 6. 为什么这样安排

1. Excel导入的权限入口依赖成员5；若先写导入，成员7必然复制角色字符串或临时放开权限。
2. 学生个人页只依赖已稳定的student auth，可与管理员权限并行，缩短关键路径。
3. 管理员查询和学生个人页都读取同一冻结模型，应在写入型导入前稳定，便于验证导入后的结果。
4. 上传/预览是纯读取与展示，风险低于正式写库，适合作为导入模块第一检查点。
5. 确认导入和回滚会改变核心数据，必须放在权限、解析、展示和契约均稳定之后。

## 7. 最大风险

最大风险是“在没有实现并验证变更记录模型时直接提供回滚”。导入事务与回滚语义已经冻结，但当前`ImportBatch`只有统计和状态，没有完整的导入前数据或逐字段变更记录。若成员7绕过模型评审直接实现回滚，可能无法区分本批新增、更新和后续人工/批次变化，造成数据丢失。

控制措施：

- 按`import_rollback_contract.md`提交`ImportChangeRecord`模型、迁移和同事务证据，评审通过后解锁回滚实现。
- 确认导入必须验证文件哈希、批次状态和幂等键。
- 回滚只能针对当前最新成功且未回滚批次，并在单个数据库事务内完成。
- 模型与迁移评审未通过时，回滚验收项不得标记完成。

## 8. 需要冻结的新接口

| 接口/契约 | 提供方 | 消费方 | 必须冻结内容 |
| --- | --- | --- | --- |
| `student_profile_contract.md` | 成员4 | 模板、集成测试 | FROZEN：身份来源、上下文字段、排序、空数据、展示来源、只读边界 |
| `admin_query_contract.md` | 成员5 | 管理员模板、集成测试 | FROZEN：登录、POST退出、认证隔离、筛选、分页、详情、404/403语义 |
| `excel_import_contract.md` | 成员7 | 页面、服务、测试 | FROZEN：上传限制、批次状态、ParseResult映射、预览零写入、确认事务、幂等、审计 |
| `import_rollback_contract.md` | 成员1/7 | 回滚服务、审计、测试 | FROZEN_SPEC / NEED_MODEL_IMPLEMENTATION：变更记录模型、可回滚判定、恢复范围、冲突、事务语义 |

现有`admin_permission_contract.md`不新建副本，但必须由成员5实现并由成员7消费。审计服务继续作为该契约的一部分；若事件字段需要扩展，应先更新该文件。

## 9. 成员任务与依赖

| 成员 | Sprint 2职责 | 主要依赖 | 交付 |
| --- | --- | --- | --- |
| 成员1 | 技术负责人、契约冻结、Review与合并门禁 | 全员确认 | 新契约、Review索引、集成顺序、最终结论 |
| 成员2 | CI、集成测试、Release Candidate验证 | 成员4/5/7候选SHA | 身份矩阵、业务闭环测试、双平台证据 |
| 成员3 | student auth维护与消费者支持 | 已稳定契约 | 不新增功能；联调测试与回归支持 |
| 成员4 | 学生个人页干净重建 | student auth | 本人材料只读页、契约、测试 |
| 成员5 | 管理员认证、权限、查询与审计服务 | admin permission契约 | 管理员闭环、唯一权限工具、查询测试 |
| 成员6 | parser消费者支持与契约回归 | excel parser稳定接口 | golden fixture、ParseResult映射测试、禁止改解析接口 |
| 成员7 | Excel上传、预览、确认、历史、日志、条件式回滚 | parser、admin permission、回滚决策 | Excel导入闭环及端到端测试 |

详细任务卡位于`docs/member_tasks/sprint2/`。

## 10. Release门禁

每个PR必须：

1. 从记录的最新develop SHA创建或正常合并最新develop。
2. 只修改任务卡允许文件。
3. 不复制冻结权限、认证或解析逻辑。
4. 执行`check`、`makemigrations --check`、`migrate`、相关测试和全量测试。
5. 最终SHA通过Repository policy、Ubuntu和Windows Django tests。
6. 提供接口变更、数据迁移、测试结果和未完成事项说明。

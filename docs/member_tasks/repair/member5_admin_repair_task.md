# Task Card

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 成员 | 成员5 |
| 模块 | 管理员认证、查询、权限与审计基础 |
| 关联PR | `feature/admin-query`，Review SHA `74a8f50` |
| 优先级 | P1 |
| 预计工作量 | 1个工作日 |
| 提供契约 | `docs/integration_contracts/admin_permission_contract.md` |
| 调用方 | 成员7导入模块 |

## 2. Original Problem

### ADMIN-01：展示失效思想汇报

- 文件位置：`apps/students/views.py:91-96`、`templates/students/admin_student_detail.html:55-61`
- 当前行为：使用 `student.ideological_reports.all()`。
- 实际风险：回滚或失效记录仍展示为当前有效材料。

### ADMIN-02：管理员退出可能清除学生身份

- 文件位置：`apps/accounts/views.py:32-46`
- 当前行为：调用 Django `auth_logout()`，会刷新整个Session。
- 实际风险：同一浏览器中的 `student_id` 可能一并丢失，与两类登录互不替代的集成方向存在冲突。

### ADMIN-03：统计来源显示错误

- 文件位置：`templates/students/admin_student_detail.html:37-50`
- 当前行为：存在汇总记录时固定显示“思想汇报汇总表”。
- 实际风险：无法区分Excel原始填报值和系统计算值。

### ADMIN-04：越界修改导入模块

- 文件位置：`apps/imports/views.py`、`apps/imports/urls.py`
- 当前行为：成员5直接实现并挂载导入占位View权限。
- 实际风险：扩大成员5范围，与成员7导入实现产生冲突。

### ADMIN-05：权限规则重复实现

- 文件位置：`apps/accounts/permissions.py`、`decorators.py`、`mixins.py`、`apps/students/views.py`
- 当前行为：相同角色判断存在多套实现，查询View未复用公共权限工具。
- 实际风险：角色规则修改时出现安全不一致。

### ADMIN-06：审计IP可由客户端伪造

- 文件位置：`apps/audit/services.py:36-40`
- 当前行为：无条件信任 `X-Forwarded-For`。
- 实际风险：当前没有可信代理配置时审计来源IP不可依赖。

### ADMIN-07：Module Notes重复

- 文件位置：`docs/04_module_notes/admin_query.md`、`docs/module_notes/admin_query.md`
- 当前行为：同一模块存在两份内容和日期不同的文档。
- 实际风险：成员7无法判断哪份接口说明有效。

## 3. Why It Is Wrong

- Spec：原始填报总数和系统计算数必须分开；权限必须后端验证。
- PRD/成员任务：成员5提供权限工具，不实现导入流程。
- Interface Contract：成员7应消费唯一权限接口，不能依赖多套字符串判断。
- Engineering Rule：核心规则集中定义，不重复枚举和权限逻辑；审计信息必须可追溯。

系统层面会导致失效数据展示、权限实现漂移和成员7联调冲突。

## 4. Repair Scope

允许修改：

```text
apps/accounts/views.py
apps/accounts/urls.py
apps/accounts/permissions.py
apps/accounts/mixins.py（仅薄封装需要时）
apps/students/views.py
apps/students/urls.py
apps/audit/services.py
templates/base.html
templates/accounts/admin_login.html
templates/students/admin_student_list.html
templates/students/admin_student_detail.html
tests/test_admin_query.py
tests/test_admin_permissions.py
docs/04_module_notes/admin_query.md
docs/integration_contracts/admin_permission_contract.md（仅最终接口确认）
```

## 5. Forbidden Modification Scope

禁止：

- 修改 `apps/imports/views.py`、`urls.py`或导入模板；
- 实现Excel解析、上传、预览、确认导入或回滚；
- 修改学生认证接口或 `student_id`；
- 修改模型字段和迁移；
- 新增管理员角色；
- 只依赖模板隐藏按钮实现权限；
- 无负责人确认就自行设计管理员退出后的学生Session新规则；
- 修改 `docs/spec.md`。

## 6. Implementation Guidance

1. 将角色判断集中在 `apps/accounts/permissions.py`。
2. 查询列表和详情复用 `viewer_or_data_admin_required` 或等价薄Mixin。
3. 删除 `decorators.py` 中重复的管理员权限实现；Mixin不得复制另一套角色集合。
4. 详情查询显式提供 `is_active=True`、`order_by("sequence_number")` 的明细。
5. 统计展示遵守 Spec：原始值非空时使用原始值；为空时使用计算值并说明来源；0是有效原始值。
6. 从本PR移除对 `apps/imports` 的改动，由成员7消费 `data_admin_required`。
7. 当前无可信代理配置时记录 `REMOTE_ADDR`。
8. 只保留 `docs/04_module_notes/admin_query.md`。
9. 管理员退出的学生Session共存行为先在PR描述中报告，由负责人确认；不得修改成员3模块绕过。

## 7. Interface Contract Update

更新文件：

```text
docs/integration_contracts/admin_permission_contract.md
```

接口：

```text
admin_required
admin_role_required
viewer_or_data_admin_required
data_admin_required
record_operation_log
```

输入：管理员认证请求、允许角色及审计操作描述。

输出：放行、登录重定向、403或 `OperationLog`。

异常：权限不足抛 `PermissionDenied`；日志数据库失败不得静默吞掉。

提供方：成员5。调用方：成员5查询页、成员7导入模块。

## 8. Required Tests

测试文件：

```text
tests/test_admin_query.py
tests/test_admin_permissions.py
```

必须新增或修正：

1. 有效和失效思想汇报同时存在时只展示有效记录。
2. 明细按真实 `sequence_number` 排序。
3. 原始总数为正数、0和None时来源正确。
4. 未登录、viewer、data_admin和未知角色权限矩阵。
5. 直接请求后端端点，不能只检查导航按钮。
6. 公共权限接口被查询View实际复用。
7. 审计登录、退出和查看详情。
8. 客户端伪造转发头时不覆盖未配置信任代理的远端IP。
9. 本PR不再依赖成员5创建的导入View。
10. 管理员退出的当前Session行为形成显式测试并等待负责人确认最终预期。

## 9. Acceptance Criteria

Given：学生同时存在有效和失效思想汇报。
When：管理员访问详情。
Then：只按序号显示有效记录。

Given：原始总数为空、计算数为4。
When：管理员访问详情。
Then：展示计算值4，并明确系统计算来源。

Given：`viewer_admin`直接请求导入入口。
When：不经过导航页面访问后端。
Then：公共权限工具拒绝请求，且不执行导入逻辑。

Given：成员7需要保护导入View。
When：导入 `data_admin_required`。
Then：只需使用一个稳定路径，不复制角色判断。

## 10. PR提交要求

提交前必须：

- 同步最新 `develop` 和成员3最终接口，人工解决 `accounts`、`students` 冲突；
- 四项Django命令通过；
- 删除本PR对 `apps/imports` 的越界实现；
- 只保留一份 Module Notes；
- Interface Contract记录最终导入路径；
- README无需修改时说明原因；
- PR描述列出权限矩阵、统计来源规则和管理员退出待确认项；
- 最终SHA通过仓库策略及Windows/Ubuntu CI。

## Integration Risk

权限接口直接影响成员7，`accounts`与成员3、`students`与成员4存在冲突。统计规则同时影响学生个人页。完成后通知成员3、成员4、成员7和负责人。

## PR界面的comment

```text
Request changes：请按 ADMIN-01～ADMIN-07 修复。必须过滤 is_active=True 明细、正确显示总篇数来源、集中权限实现，并移除对 imports View/URL 的越界修改。请冻结 permissions.py 与 audit/services.py 的调用契约；管理员退出是否保留学生Session请在PR中报告并等待负责人确认，不要修改成员3接口自行决定。
```

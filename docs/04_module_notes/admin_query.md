# 管理员查询模块

负责人：成员5

Branch: feature/admin-query

完成时间: 2026-08-04（修复轮次）

---

# 1. 模块目标

为学院管理员提供学生党务材料查询后台，包括：
- 管理员登录/退出
- 两种角色权限控制（viewer_admin / data_admin）
- 学生列表多条件筛选与分页
- 学生详情展示（含统计汇总）
- 查询操作审计日志
- 为成员7提供可复用的权限工具

---

# 2. 业务流程

用户：管理员访问登录页 → 输入用户名密码

↓

系统：验证凭证 → 创建 Session → 写入登录审计日志

↓

页面：跳转学生列表页 → 可筛选/翻页/查看详情

↓

用户：点击退出

↓

系统：POST 退出 → 清除 Session → 写入退出审计日志 → 跳转首页

---

# 3. 数据模型

涉及：

- `AdminUser` (accounts) — 管理员用户，含 role 字段（viewer_admin / data_admin）
- `Student` (students) — 学生信息
- `PartyBranch` (students) — 党支部
- `IdeologicalReportSummary` (materials) — 思想汇报汇总（Excel填报总篇数、系统计算日期数）
- `IdeologicalReport` (materials) — 思想汇报明细
- `ApplicationRecord` (materials) — 申请入党记录
- `OperationLog` (audit) — 操作审计日志

---

# 4. 核心文件

|文件|作用|
|-|-|
|`apps/accounts/views.py`|AdminLoginView（登录+日志）、admin_logout_view（POST退出+日志）|
|`apps/accounts/urls.py`|登录/退出路由|
|`apps/accounts/permissions.py`|统一权限接口：`check_admin_role()`、`ViewerOrDataAdminRequiredMixin`、`DataAdminRequiredMixin`、`admin_role_required`、`data_admin_required`、`viewer_or_data_admin_required`|
|`apps/accounts/decorators.py`|兼容重导出 `data_admin_required`（实现转至 permissions.py）|
|`apps/accounts/mixins.py`|兼容重导出 `DataAdminRequiredMixin`（实现转至 permissions.py）|
|`apps/students/views.py`|AdminStudentListView（列表+5类筛选+ViewerOrDataAdminRequiredMixin）、AdminStudentDetailView（详情+is_active过滤+统计来源+审计日志）|
|`apps/students/urls.py`|学生列表/详情路由|
|`apps/audit/services.py`|record_operation_log() 审计日志辅助函数；get_client_ip() 可信代理检查|
|`templates/base.html`|导航栏（含POST退出表单）|
|`templates/accounts/admin_login.html`|登录页模板|
|`templates/students/admin_student_list.html`|学生列表页（8列+5筛选+分页）|
|`templates/students/admin_student_detail.html`|学生详情页（含统计来源、有效明细）|
|`tests/test_admin_query.py`|59个自动化测试|

---

# 5. AI Coding记录

**第一轮（2026-07-29）：**

主要Prompt：
- 按spec实现管理员登录/退出/权限/列表/详情/审计
- 修复review反馈的7个缺陷
- 退出改用POST表单
- 非法筛选返回200、显示错误且结果为空，避免查询范围扩大
- 列表补全8个字段+状态筛选
- 详情补全计算日期数和导入批次
- 编写14类测试场景

AI生成：
- AdminLoginView、admin_logout_view
- permissions.py 四个权限工具
- AdminStudentListView（筛选校验+状态筛选）
- AdminStudentDetailView（含审计日志写入）
- record_operation_log 审计服务
- 完整的列表和详情模板
- 34个测试用例

**修复轮次（2026-08-04）：**

主要Prompt：
- 详情只显示 is_active=True 且按 sequence_number 排序的思想汇报明细
- 原始总数非 None 时展示原始值和 Excel 来源；为 None 时展示计算值和系统计算来源；0 不回退
- 将权限判断集中到 apps/accounts/permissions.py（Mixin + check_admin_role）
- 查询 View 复用 ViewerOrDataAdminRequiredMixin
- 移除本 PR 对 apps/imports/views.py 和 urls.py 的修改
- 审计 IP：无 TRUSTED_PROXIES 时使用 REMOTE_ADDR
- 只保留 docs/04_module_notes/admin_query.md
- 补齐 is_active 过滤、统计来源、统一权限和审计 IP 测试

人工修改：
- 按项目模板格式调整 Module Notes
- 确认 spec 中每个字段都在模板中正确展示

---

# 6. 遇到问题

问题：Review 发现退出链接用 GET 导致 405
原因：Django 4.1+ 的 LogoutView 默认仅接受 POST
解决：改为 POST 表单 + CSRF token，另写 admin_logout_view 处理退出+日志

问题：非法 branch 参数导致 500
原因：branch_id 直接传入 filter()，非数字时数据库报错
解决：校验支部、阶段和状态；非法值返回空结果并显示错误，不回退全量数据

问题：列表缺少4个字段、详情缺少统计信息
原因：初版只实现了基本展示
解决：按 spec 补全所有字段

问题：详情展示已回滚/失效思想汇报
原因：student.ideological_reports.all() 不过滤 is_active
解决：使用 Prefetch 过滤 is_active=True 并按 sequence_number 排序

问题：统计来源固定显示"汇总表"
原因：没有区分 Excel 原始填报值和系统计算值
解决：reported_total_count is not None（含0）→ Excel原始填报值；为 None → 系统计算

问题：权限在 permissions.py/decorators.py/mixins.py/View 中四套重复
原因：逐步添加权限时未收口
解决：统一到 permissions.py（check_admin_role + 两个 Mixin），decorators/mixins 改为兼容重导出

问题：审计 IP 无条件信任 X-Forwarded-For
原因：get_client_ip 未检查可信代理配置
解决：检查 settings.TRUSTED_PROXIES，无配置时使用 REMOTE_ADDR

问题：PR 中包含 imports 模块权限修改，超出职责范围
原因：初版在 imports/views.py 和 urls.py 中挂载了 DataAdminRequiredMixin
解决：回退到 TemplateView 直接渲染，由成员7负责权限

---

# 7. 测试

测试文件：`tests/test_admin_query.py`（54 tests）

**登录/退出（7项）：**
- 管理员登录成功跳转列表
- 登录成功写审计日志
- 密码错误显示错误提示
- 登录失败不写审计日志
- POST 退出清除 Session
- POST 退出写审计日志
- GET 退出返回 405

**权限矩阵（7项）：**
- viewer 可访问列表和详情
- viewer 可访问导入页（PR已回退导入改动，成员7负责）
- data_admin 可访问列表、详情和导入页
- 未登录不能访问列表和详情

**统一权限接口（5项）：**
- check_admin_role 判断正确（viewer/viewer_or_data/匿名）
- ViewerOrDataAdminRequiredMixin 对 viewer/data_admin/匿名 均生效

**筛选（7项）：**
- 姓名/学号模糊、支部/阶段/状态精确、组合筛选
- 非法 branch/stage/status 不产生 500

**列表与分页（2项）：**
- 列表展示 8 个字段 + 详情入口
- 分页保留筛选参数

**详情与统计来源（7项）：**
- 原始值非 None 时展示 Excel填报总篇数和来源
- 原始值存在时不展示系统计算值
- 原始值为 None 时展示系统计算日期数和来源
- reported_total_count=0 展示 0 篇且来源 Excel（不回退）

**is_active 过滤（3项）：**
- 有效记录按 sequence_number 排序
- is_active=False 的记录不展示
- 明细区域标注"有效记录"

**审计日志与 IP（5项）：**
- 查看详情写入 OperationLog
- 登录日志记录 IP
- 无 TRUSTED_PROXIES 时使用 REMOTE_ADDR
- 仅当 REMOTE_ADDR 命中 TRUSTED_PROXIES（支持IP/CIDR）时信任 X-Forwarded-For
- 无头时回退 REMOTE_ADDR

**边界（3项）：**
- 无材料学生不报错
- 不存在学生返回 404
- 空数据提示

测试运行命令：
```powershell
python manage.py test tests.test_admin_query -v 2
```

结果：54 tests passed.

---

# 8. 权限矩阵

权限统一入口：`apps/accounts/permissions.py`

| 角色 | 学生列表 | 学生详情 | Excel导入页 |
| --- | --- | --- | --- |
| `viewer_admin` | ✅ 允许 | ✅ 允许 | — 成员7负责 |
| `data_admin` | ✅ 允许 | ✅ 允许 | — 成员7负责 |
| 未登录 | ❌ 跳转登录页 | ❌ 跳转登录页 | — 成员7负责 |

权限在后端通过 `ViewerOrDataAdminRequiredMixin` / `DataAdminRequiredMixin` 校验。

**成员7复用接口：**
- `check_admin_role(user, *roles)` — 运行时角色判断
- `DataAdminRequiredMixin` (permissions.py) — 类视图仅数据管理员
- `ViewerOrDataAdminRequiredMixin` (permissions.py) — 类视图查询/数据管理员
- `data_admin_required` / `viewer_or_data_admin_required` — 函数视图装饰器
- `admin_role_required(*roles)` — 通用角色装饰器

**禁止在导入模块或其他模块复制角色判断逻辑。**

---

# 9. 审计日志写入点

| 操作 | action | target_type | 触发位置 | IP来源 |
| --- | --- | --- | --- | --- |
| 管理员登录 | `admin_login` | admin | AdminLoginView.form_valid() | REMOTE_ADDR（无可信代理时） |
| 管理员退出 | `admin_logout` | admin | admin_logout_view() | REMOTE_ADDR（无可信代理时） |
| 查看学生详情 | `view_student_detail` | student | AdminStudentDetailView.get() | REMOTE_ADDR（无可信代理时） |

IP 提取逻辑：`get_client_ip()` 仅在 `settings.TRUSTED_PROXIES` 配置时才信任 `X-Forwarded-For`；
当前无配置时直接使用 `REMOTE_ADDR`，防止客户端 IP 伪造。

---

# 10. 我的理解

这个模块本质解决：**为管理员提供带权限控制的党务材料查询后台**。

核心设计原则：
1. 权限后端强制校验，不能仅靠前端隐藏
2. 权限判断统一到 `apps/accounts/permissions.py`，禁止在多处复制
3. 筛选参数安全校验，非法值返回200、错误提示和空结果
4. 退出必须 POST，防止 CSRF 攻击
5. 敏感操作写审计日志，可追溯
6. 审计 IP 默认使用 REMOTE_ADDR，仅在配置可信代理时信任 X-Forwarded-For
7. 详情只展示 is_active=True 的有效明细，按 sequence_number 排序
8. 详情同时展示原始值、计算值、当前值及来源；reported_total_count=0 不回退
9. 权限工具独立封装，供成员7复用；禁止在导入模块复制角色判断

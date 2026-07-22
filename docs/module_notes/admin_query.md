
---
# Module Notes：管理员查询模块

负责人：成员5

Branch: `feature/admin-query`

完成时间: 2026-07-21

---

# 1. 模块目标

解决管理员登录后台、查询全部学生、按条件筛选、查看学生党务材料详情的问题。

两类管理员角色：

- **viewer_admin（查询管理员）**：可登录后台、查看学生列表和详情，**不可**访问 Excel 导入功能
- **data_admin（数据管理员）**：全部权限，包括 Excel 导入

---

# 2. 业务流程

```
管理员登录页
    │
    ├─ 错误 → 提示"用户名或密码错误"
    │
    └─ 成功 → 学生管理列表页
                │
                ├─ 筛选：姓名/学号/支部/阶段
                ├─ 分页：每页 50 条
                │
                └─ 点击学生 → 学生详情页
                                ├─ 基本信息（姓名/学号/支部/阶段/职务/状态）
                                └─ 党务材料（申请入党时间/思想汇报总篇数/明细列表）
```

权限流程：

```
请求 /imports/*
    │
    ├─ 未登录 → 302 跳转登录页
    ├─ viewer_admin → 403 禁止访问
    └─ data_admin → 放行
```

---

# 3. 数据模型

| 模型 | 关联方式 | 关键字段 |
|---|---|---|
| `AdminUser` | — | username, role (viewer_admin / data_admin) |
| `Student` | select_related('branch') | name, student_number, development_stage |
| `PartyBranch` | Student FK | name, code |
| `ApplicationRecord` | Student OneToOne | applied_at |
| `IdeologicalReportSummary` | Student OneToOne | reported_total_count, calculated_date_count |
| `IdeologicalReport` | Student FK | sequence_number, submitted_at |

列表页使用 `select_related('branch')` 避免 N+1 查询。

---

# 4. 核心文件

| 文件 | 作用 |
|---|---|
| `apps/accounts/views.py` | `AdminLoginView` — 管理员登录入口 |
| `apps/accounts/decorators.py` | `data_admin_required` — 函数视图权限装饰器 |
| `apps/accounts/mixins.py` | `DataAdminRequiredMixin` — 类视图权限 Mixin |
| `apps/students/views.py` | `AdminStudentListView` + `AdminStudentDetailView` |
| `apps/students/urls.py` | 学生管理路由 |
| `apps/imports/views.py` | 导入页视图，挂载权限 Mixin |
| `apps/imports/urls.py` | 导入路由 |
| `templates/accounts/admin_login.html` | 管理员登录页 |
| `templates/students/admin_student_list.html` | 学生列表页（表格+筛选+分页） |
| `templates/students/admin_student_detail.html` | 学生详情页 |
| `templates/base.html` | 导航栏按角色显示/隐藏入口 |
| `config/settings.py` | `LOGIN_REDIRECT_URL` 指向学生管理 |

---

# 5. AI Coding 记录

**主要 Prompt：**

- "实现管理员登录入口，使用 AdminUser 模型 + Django auth，不与 /admin/ 混淆"
- "实现管理员权限检查，基于 AdminRole viewer_admin / data_admin，后端强制拦截"
- "实现学生列表查询，展示姓名/学号/支部/阶段，考虑1500条性能"

**AI 生成：**

- `AdminLoginView`（封装 Django LoginView）
- `data_admin_required` 装饰器 + `DataAdminRequiredMixin`
- `AdminStudentListView`（select_related + 分页 + 多条件筛选）
- `AdminStudentDetailView`（预取关联数据）
- 全部模板页面（Bootstrap 5 表格/筛选栏/分页）

**人工修改：**

- 模板关联名修正（applicationrecord_set → application_record / report_summary / ideological_reports）
- Mixin 匿名用户处理（先检查 is_authenticated 再检查 role）
- `LOGIN_REDIRECT_URL` 配置

---

# 6. 遇到问题

| 问题 | 原因 | 解决 |
|---|---|---|
| 登录成功后跳转到 /accounts/profile/ | Django 默认 LOGIN_REDIRECT_URL 未配置 | settings.py 添加 `LOGIN_REDIRECT_URL = "students:admin_student_list"` |
| 未登录访问导入页报 AttributeError | Mixin 中直接访问 `request.user.role`，AnonymousUser 无此属性 | 先判断 `is_authenticated`，再检查 role |
| 详情页 AttributeError | 模板中关联名写错（applicationrecord_set 等） | 修正为 materials 模型中定义的 related_name |
| 筛选分页链接丢失参数 | 分页链接未拼装筛选条件 | 模板中用 `{% for k,v in filters.items %}` 保留参数 |

---

# 7. 测试

**正常情况：**

- viewer_admin 登录 → 学生列表 → 查看详情 ✅
- data_admin 登录 → 学生列表 → 查看详情 → Excel 上传 ✅
- 筛选：姓名模糊搜索 → 返回匹配结果 ✅
- 分页正常显示 ✅

**异常情况：**

- viewer_admin 访问 /imports/upload/ → 403 ✅
- 未登录访问 /imports/upload/ → 302 跳转登录页 ✅
- 登录失败 → 页面提示"用户名或密码错误" ✅
- 无数据时表格显示"暂无学生数据" ✅

**边界情况：**

- `select_related('branch')` 已验证 SQL JOIN 生效
- 分页 50/页，1500 条约 30 页
- 筛选参数保留在 URL 中，翻页不丢失

---

# 8. 我的理解

这个模块本质解决的是：

> **管理员通过统一的业务后台查询学生党务材料，并根据角色隔离敏感操作权限。**

不是简单的 CRUD，核心设计点在于：

1. **独立于 Django Admin**：业务登录不走 `/admin/`，使用自己的 `AdminLoginView`
2. **角色隔离在后端**：`DataAdminRequiredMixin` 在 dispatch 层拦截，前端隐藏导航只是辅助
3. **性能意识**：`select_related` 减少查询次数，分页控制内存占用
4. **筛选可组合**：姓名/学号/支部/阶段任意组合，参数透传保持可用性

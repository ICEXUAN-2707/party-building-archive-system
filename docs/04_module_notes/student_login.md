# 学生登录与权限模块说明（任务 3）

本模块提供独立的"姓名 + 学号"学生登录能力，不依赖 Django 自带的 Auth/Admin 用户体系。

## 一、模块组件清单

| 模块文件 | 职责 |
|---|---|
| `apps/accounts/forms.py` | `StudentLoginForm`：姓名/学号字段 + 首尾空格 trim |
| `apps/accounts/decorators.py` | `@student_login_required`、`@admin_url_forbid_student` 两个可复用装饰器 |
| `apps/accounts/views.py` | `student_login`、`student_logout` 视图；内置 5 次/5 分钟限流 |
| `apps/accounts/urls.py` | `student-login/`、`student-logout/` 路由 |
| `apps/students/views.py` | `student_profile`（登录保护）、`admin_student_list/detail`（学生访问 403） |
| `templates/accounts/student_login.html` | 登录页，统一展示 non_field_errors |
| `config/settings.py` | `SESSION_COOKIE_AGE = 1800`（30 分钟无操作失效） |

---

## 二、学生登录流程

```
POST /accounts/student-login/
        │
        ▼
   （前置检查）Session 中 _student_login_locked_until > now？
        │ yes ──► 直接返回「登录失败次数过多，请 5 分钟后再试」（不查 Student 表）
        │ no
        ▼
   StudentLoginForm 校验（必填、trim 空格）
        │ invalid ──► 失败计数+1，返回统一错误「姓名或学号不匹配」
        │ valid
        ▼
   Student.objects.filter(
       name=name, student_number=student_number, status=ACTIVE
   ).first()
        │ 空 ──► 失败计数+1；若≥5 则写 locked_until；返回统一错误
        │ 非空
        ▼
   _reset_login_throttle()  清除失败计数与 locked_until
   request.session["student_id"] = student.id
   302 重定向到 students:student_profile
```

### 错误处理规范

- **所有错误信息仅写在 `form.non_field_errors`**（`__all__` 级别），字段级错误被主动删除。
- **消息不暴露字段细节**：只出现"姓名或学号不匹配"，不出现"姓名错误"、"学号错误"等字样。
- **限流消息**：仅在达到 5 次失败后或锁定期内出现"登录失败次数过多，请 5 分钟后再试"。

---

## 三、Session 管理

### 1. 存储键

| Session Key | 类型 | 写入位置 | 清除时机 |
|---|---|---|---|
| `student_id`（= `SESSION_STUDENT_ID_KEY`） | `int` | 登录成功 | `student_logout` 视图；Session 过期 |
| `_student_login_failed_count` | `int` | 每次登录失败 | 登录成功；`locked_until` 过期自动清除 |
| `_student_login_locked_until` | `float`（Unix 时间戳） | 第 5 次失败时写入 = now + 300s | 登录成功；时间过期自动清除 |

### 2. 全局时效

- `SESSION_COOKIE_AGE = 1800`：学生登录后，30 分钟无任何请求操作则 Session 失效。
- 再次访问需要重新走姓名+学号校验。

### 3. 独立于管理员体系

- 学生 Session 键名 `student_id`，与 Django Auth 的 `_auth_user_id` / `_auth_user_backend` **无冲突**。
- 同一浏览器可以同时登录 Django Admin（管理员）和学生，互不干扰。

---

## 四、权限装饰器用法

从 `apps.accounts.decorators` 导入，可被角色四（学生个人信息、材料模块等）直接复用。

### 1. `@student_login_required`

**作用**：
- 从 `request.session["student_id"]` 读取身份；若不存在 → 302 跳转到 `accounts:student_login`。
- 若存在 → 通过 `setattr(request, 'student_id', <id>)` 附加到请求对象，View 直接读取 `request.student_id` 使用。
- **绝不从 `request.GET` 读取 student_id**，因此 URL 伪造 `?student_id=<他人id>` 完全无效。

**示例**：
```python
from django.shortcuts import render
from apps.accounts.decorators import student_login_required
from apps.students.models import Student

@student_login_required
def my_materials(request):
    student = Student.objects.get(pk=request.student_id)
    return render(request, "materials/my_materials.html", {"student": student})
```

### 2. `@admin_url_forbid_student`

**作用**：
- 用于"管理员专属页面"路由：检测到 Session 中存在 `student_id` 即代表学生身份 → 返回 403 Forbidden。
- 匿名用户、管理员身份直接放行。

**示例**：
```python
from django.shortcuts import render
from apps.accounts.decorators import admin_url_forbid_student

@admin_url_forbid_student
def admin_audit_list(request):
    return render(request, "audit/admin_list.html")
```

---

## 五、登录限流（5 次 / 5 分钟）

| 项目 | 说明 |
|---|---|
| 阈值 | `MAX_LOGIN_FAILURES = 5` |
| 锁定时长 | `LOCK_DURATION_SECONDS = 300`（5 分钟） |
| 存储位置 | 同一会话 Session（按浏览器 cookie 维度） |
| 锁定期间行为 | 直接返回限流错误消息，**不执行 `Student.objects.filter` 查询**，保护数据库 |
| 锁定解除 | ① 超过 5 分钟后下一次请求自动 reset；② 登录成功立刻 reset |

---

## 六、13 个验收测试场景索引

测试文件（任务 3-5 要求位置）：

- `tests/test_student_login.py`：覆盖场景 1~5 与 11~13
- `tests/test_student_permission.py`：覆盖场景 6~10

| 编号 | 场景 | 所在测试方法 |
|---|---|---|
| 1 | 正确姓名+学号登录成功，跳转+Session 存 student_id | `test_scenario_01_correct_credentials_login` |
| 2 | 姓名为空 → 表单校验不通过 | `test_scenario_02_empty_name` |
| 3 | 学号为空 → 表单校验不通过 | `test_scenario_03_empty_student_number` |
| 4 | 组合不匹配 → 统一错误，不暴露字段 | `test_scenario_04_mismatch_unified_error` |
| 5 | 登录成功访问个人信息页正常显示 | `test_scenario_05_profile_after_login` |
| 6 | 未登录访问个人页跳登录页 | `test_scenario_06_anonymous_profile_redirects` |
| 7 | 退出登录清除 Session student_id | `test_scenario_07_logout_clears_session` |
| 8 | 退出后访问个人页跳登录页 | `test_scenario_08_profile_after_logout_redirects` |
| 9 | URL 伪造 student_id 不生效 | `test_scenario_09_url_forged_student_id_ignored` |
| 10 | 学生访问管理员 URL 返回 403 | `test_scenario_10_student_blocked_on_admin_urls` |
| 11 | 连续 5 次失败触发限制 | `test_scenario_11_five_failures_trigger_lockout` |
| 12 | 限制期间不执行数据库查询 | `test_scenario_12_lockout_skips_database_query` |
| 13 | 登录成功后失败计数归零 | `test_scenario_13_success_resets_counter` |

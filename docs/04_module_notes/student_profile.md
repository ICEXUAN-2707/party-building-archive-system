# 学生个人档案模块 Module Notes
## 1. 模块简介
模块路径：`apps/students`
功能：仅展示当前登录学生本人党务材料，无数据写入、无管理员查询能力。
依赖模块：`apps/accounts` 学生认证接口。

## 2. 跨模块接口依赖（契约路径：docs/integration_contracts/student_session_contract.md）
导入路径：
```python
from apps.accounts.student_access import get_current_student, student_required
```
1. `@student_required`：视图装饰器，未登录 / 失效 Session 自动重定向登录页
2. `get_current_student(request)`：获取当前会话学生，自动清理无效 student_id

## 3. 路由信息
命名空间：`students`
路由：`path("me/", views.student_profile, name="student_profile")`
访问地址：`/students/me/`

## 4. 业务查询规则
仅读取 student=当前登录学生 的数据，禁止通过 URL/GET/POST 参数切换学生；
入党申请记录：`ApplicationRecord.objects.filter(student=student).first()`；
思想汇报：仅查询 is_active=True，按 sequence_number 升序；
总篇数展示规则：
存在 application.reported_total_count 且不为空：使用填报数值，标记来源 Excel；
无填报数值：使用汇报列表计数，标记系统自动统计。

## 5. 登出规范
页面登出仅使用 POST 表单，路由 `accounts:student_logout`，携带 CSRF 令牌；
仅清除 session["student_id"]，不调用 session.flush()，不影响管理员登录状态。

## 6. 模板文件
`templates/students/student_profile.html`
包含身份信息、入党申请、思想汇报明细、POST 登出按钮，具备空状态提示。

## 7. 测试覆盖文件
`tests/test_student_profile.py`：单元测试，覆盖匿名访问、失效 Session、越权拦截、总数展示规则；
`tests/test_student_flow_integration.py`：端到端流程，登录→个人页→POST 退出完整链路。

## 8. 禁止范围
不实现学生登录、登出逻辑；
不提供管理员列表 / 详情接口；
不接收请求参数中的 student_id；
不修改、写入 Student/ApplicationRecord/IdeologicalReport 数据；
不使用 session.flush()。
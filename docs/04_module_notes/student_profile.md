# 学生个人档案展示模块

负责人：成员4

Branch: `feature/student-profile`

完成时间: Sprint 1 返工

---

# 1. 模块目标

学生登录后只读查看本人党务档案：基础信息、入党申请时间、思想汇报总篇数（含原始/计算值来源）、思想汇报明细及最近更新时间。不做任何写入，不接受请求参数中的目标学生ID。

---

# 2. 业务流程

用户：学生（已通过成员3的登录写入 `student_id`）

↓

系统：`/students/me/` 由 `student_required` 校验 Session，失败重定向 `accounts:student_login`

↓

数据库：按 `request.current_student` 只读查询 `ApplicationRecord`、`IdeologicalReportSummary`、`IdeologicalReport`

↓

结果: 渲染 `student_profile.html`，关联缺失展示"暂无数据"，不500

---

# 3. 数据模型

只读调用，不修改：

- `students.Student`（身份来源）
- `materials.ApplicationRecord`（OneToOne 反向 `application_record`）
- `materials.IdeologicalReportSummary`（OneToOne 反向 `report_summary`）
- `materials.IdeologicalReport`（ForeignKey 反向 `ideological_reports`）

---

# 4. 核心文件

| 文件 | 作用 |
| - | - |
| `apps/students/views.py` | `student_profile` 只读视图，`@student_required` 保护 |
| `apps/students/urls.py` | `me/` 路由 `student_profile`；保留 admin 占位路由 |
| `templates/students/student_profile.html` | 档案展示模板，含退出表单 |
| `tests/test_student_profile.py` | 单元测试，用例 1-10 |
| `tests/test_student_flow_integration.py` | 联调测试，用例 11-12 及完整流程 |

---

# 5. 接口消费（成员3契约）

唯一身份入口：

```python
from apps.accounts.student_access import student_required
```

`student_required` 验证 Session 后将学生固定为 `request.current_student`，视图直接读取该属性，不重复实现认证、不调用 `session.flush()`。退出入口为 `accounts:student_logout`（POST），由模板表单调用。

---

# 6. 关键规则

1. 明细限定 `student=当前学生`、`is_active=True`，按 `sequence_number` 升序，模板显示真实 `sequence_number`。
2. 总篇数：`reported_total_count is not None`（含0）展示原始值；为 `None` 展示 `calculated_date_count` 并标记"系统自动统计"；无汇总时回退有效明细数量。
3. 关联缺失（申请/汇总/明细为空）一律展示"暂无数据"，不抛500。
4. URL、GET、POST 中的目标学生ID一律忽略，身份只来自 Session。

---

# 7. 测试

正常情况：登录后展示本人姓名学号、申请日期、总篇数、明细序号排序。

异常情况：匿名访问重定向登录；失效/不存在主键 Session 清理并重定向，不500。

边界情况：总篇数 0/正数/None；仅显示有效明细；无汇总无明细页面正常；GET/POST/URL 不能切换学生；匿名不能经管理员路由读到学生数据；退出表单 POST 正确URL。

---

# 8. 我的理解

这个模块本质解决：在成员3冻结的身份接口之上，安全地把"本人"的党务材料只读展示给学生，越权防护完全由后端 Session 决定，模板和请求参数都不参与身份判定。
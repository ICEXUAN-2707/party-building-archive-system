# 学生个人页接口契约

## 1. 契约状态

| 项目 | 内容 |
| --- | --- |
| 状态 | FROZEN |
| 版本 | Sprint 2 / 1.0 |
| 冻结日期 | 2026-08-09 |
| 提供方 | 成员4，`students`模块 |
| 消费方 | 学生个人页模板、成员2集成测试 |
| 依据基线 | `develop@068c27fb7e41ec6f77299ebf3bbac68162714f63` |
| 依赖 | `student_session_contract.md`、`docs/spec.md` V1.2、当前`Student`与`materials`模型 |

本契约冻结页面可观察行为，不冻结视图内部查询、私有辅助函数或`select_related()`、`prefetch_related()`的具体写法。

## 2. 公共入口

```text
method: GET
path: /students/me/
url name: students:student_profile
```

该入口必须由`apps.accounts.student_access.student_required`保护。未登录或学生Session失效时，行为完全服从`student_session_contract.md`。

## 3. 身份与权限

1. 目标学生唯一来自`request.current_student`。
2. 视图不得直接重新解析`request.session["student_id"]`。
3. URL、GET、POST、Cookie中的自定义字段或隐藏表单不得指定目标学生ID。
4. Django管理员认证不能替代学生身份；仅有管理员认证而没有有效`student_id`时仍按未登录学生处理。
5. 页面只读，不提供编辑或写入入口。

## 4. 页面数据

页面必须提供并展示：

| 数据 | 模型来源 | 空数据行为 |
| --- | --- | --- |
| 姓名、学号、发展阶段、职务、状态 | `Student` | Student由认证保证存在 |
| 党支部名称、代码 | `Student.branch` | 现有模型为必填关系 |
| 申请入党时间 | `ApplicationRecord.applied_at` | 关联或日期不存在时显示“暂无” |
| Excel填报总篇数 | `IdeologicalReportSummary.reported_total_count` | 允许为空 |
| 系统计算日期数 | `IdeologicalReportSummary.calculated_date_count` | 无汇总时按0处理 |
| 页面展示总篇数及来源 | 本契约第5节 | 必须标注回退来源 |
| 思想汇报明细 | `IdeologicalReport` | 空列表显示明确空状态 |
| 最近更新时间 | 本契约第7节 | 至少包含学生更新时间 |

推荐模板上下文字段如下；字段名称属于本模块对模板和测试的正式接口：

```text
student
application_record
report_summary
active_reports
display_total_count
display_total_source
latest_updated_at
```

`application_record`和`report_summary`允许为`None`；`active_reports`必须是可迭代空集合而不是`None`。

## 5. 总篇数展示规则

该规则以`docs/spec.md` V1.2为准：

1. `reported_total_count is not None`时，`display_total_count`使用该值，包含值为0的情况；`display_total_source`为`reported`。
2. `reported_total_count is None`时，`display_total_count`使用`calculated_date_count`；`display_total_source`为`calculated`。
3. 使用计算值时，学生页必须显示“根据当前已记录提交时间统计”或等价提示。
4. 填报数和计算数不一致时，页面展示填报数，但思想汇报明细只展示真实存在的有效记录；不得补造明细或覆盖原始填报数。
5. 汇总关联不存在时，页面展示总篇数为0并标记为`calculated`。

旧任务资料中“填报值为空时显示未知”的描述被本节取代，不得作为实现或测试依据。

## 6. 思想汇报规则

1. 只读取`is_active=True`的记录。
2. 严格按`sequence_number`升序展示，不按日期重新编号。
3. 展示`sequence_number`、`submitted_at`和必要的来源说明。
4. 日期按`docs/spec.md`统一显示为“YYYY年M月D日”。
5. 不得因为页面访问创建汇总、申请或思想汇报记录。

## 7. 最近更新时间

`latest_updated_at`取下列实际存在时间的最大值：

```text
Student.updated_at
ApplicationRecord.updated_at
IdeologicalReportSummary.updated_at
有效IdeologicalReport.created_at
```

`IdeologicalReport`当前没有`updated_at`字段，不得在契约消费者中假定该字段存在。没有关联数据时使用`Student.updated_at`。

## 8. 数据访问与副作用

1. 页面请求不得创建、更新、停用或删除任何业务记录。
2. 应避免模板触发N+1查询，但查询优化方式不是冻结接口。
3. OneToOne关联不存在时必须正常返回页面，不能产生500。
4. 数据库或系统异常不得伪装为空数据静默吞掉。

## 9. 契约测试

1. 未登录访问重定向学生登录。
2. 有效Session只显示当前学生。
3. URL、GET或POST伪造学生ID不能越权。
4. 仅管理员认证不能访问学生个人页。
5. 申请、汇总或明细关联为空时正常展示。
6. `reported_total_count=None`时回退计算数并标记来源。
7. `reported_total_count=0`时显示0且来源为填报值。
8. 填报数与计算数不一致时不补造思想汇报。
9. 只显示有效明细并按次数升序。
10. 最近更新时间按本契约计算。
11. 页面请求前后业务表逐项不变。
12. 学生登录、个人页、POST退出和再次访问拒绝形成完整链路。

## 10. 禁止行为

- 不复制学生认证工具。
- 不修改模型或迁移来实现展示。
- 不接受目标学生ID。
- 不在页面请求中修复或回填业务数据。
- 不实现管理员列表或详情。

## 11. 变更规则

路由、上下文字段、展示来源、排序、空数据或最近更新时间规则变化时，必须同步更新本契约、成员4 Module Notes和成员2集成测试，并由成员4、成员2和成员1共同确认。

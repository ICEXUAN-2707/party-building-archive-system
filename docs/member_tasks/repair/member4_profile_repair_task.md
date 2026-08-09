# Task Card

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 成员 | 成员4 |
| 模块 | `students` 学生个人信息展示 |
| 关联PR | `feature/student-profile`，Review SHA `9004484` |
| 优先级 | P0 |
| 预计工作量 | 1～1.5个工作日 |
| 前置依赖 | 成员3最终接口SHA与 `student_session_contract.md` |

## 2. Original Problem

### PROFILE-01：匿名管理员详情泄露学生数据

- 文件位置：`apps/students/views.py:32-39`、`apps/students/urls.py:8-9`
- 当前行为：新增管理员列表和详情函数，没有管理员认证或角色检查。
- 实际风险：匿名用户可枚举主键读取学生信息，属于学生数据越权访问。

### PROFILE-02：个人页存在确定性反向解析错误

- 文件位置：`templates/students/profile.html:56`
- 当前行为：引用不存在的 `accounts:logout`。
- 实际风险：登录学生渲染页面时产生 `NoReverseMatch` 和500。

### PROFILE-03：核心材料没有传给模板

- 文件位置：`apps/students/views.py:24-29`、`templates/students/profile.html:27-47`
- 当前行为：View只传 `student`，模板读取不存在的 `application`、`report_count`、`report_list`。
- 实际风险：申请日期、总篇数和明细无法正确展示。

### PROFILE-04：失效Session返回500

- 文件位置：`apps/students/views.py:28`
- 当前行为：直接 `Student.objects.get()`，不处理不存在记录。
- 实际风险：过期Session触发服务器错误。

### PROFILE-05：复制成员3认证逻辑

- 文件位置：`apps/students/views.py:6-21`
- 当前行为：成员4重新实现登录和 `session.flush()` 退出。
- 实际风险：两套认证接口漂移，退出还会清空管理员状态。

### PROFILE-06：总篇数和明细规则错误

- 文件位置：`templates/students/profile.html:38-44`
- 当前行为：没有实现原始值/计算值选择规则，使用 `forloop.counter` 代替 `sequence_number`。
- 实际风险：页面展示错误党务材料信息。

### PROFILE-07：没有模块测试和Module Notes

- 文件位置：整个PR。
- 当前行为：没有新增个人页测试和交付文档。
- 实际风险：现有基线测试无法发现真实页面500和越权问题。

## 3. Why It Is Wrong

- Spec：学生只能查看Session对应的本人数据；总篇数为 `None` 时展示 `calculated_date_count`；明细按序号解释。
- PRD/成员任务：成员4只负责只读展示，不负责登录、退出或管理员查询。
- Interface Contract：必须调用成员3提供的身份接口，不得复制认证。
- Engineering Rule：权限由后端执行，测试必须调用真实生产代码。

当前实现同时造成匿名数据泄露、页面500和核心功能缺失，因此必须阻止合并。

## 4. Repair Scope

允许修改：

```text
apps/students/views.py
apps/students/urls.py
templates/students/student_profile.html
tests/test_student_profile.py
tests/test_student_flow_integration.py
docs/04_module_notes/student_profile.md
```

只读调用：

```text
apps/accounts 学生身份接口
apps/students/models.py
apps/materials/models.py
```

## 5. Forbidden Modification Scope

禁止：

- 实现或修改学生登录、退出、Session写入；
- 实现管理员列表、管理员详情或管理员权限；
- 修改 `apps/accounts/`；
- 接受URL、GET或POST中的目标学生ID；
- 写入 Student、ApplicationRecord、汇总或明细；
- 修改模型字段和迁移；
- 修改 `docs/spec.md`；
- 使用 `session.flush()`。

## 6. Implementation Guidance

1. 删除本分支新增的学生登录、退出和管理员视图。
2. 恢复冻结模板路径 `templates/students/student_profile.html`。
3. `/students/me/` 使用成员3的 `student_required` 和 `get_current_student()`。
4. 查询当前学生的申请记录和汇总；缺失关联使用安全的空状态。
5. 查询思想汇报时限定 `student=当前学生`、`is_active=True`，并按 `sequence_number` 升序。
6. `reported_total_count is not None` 时展示原始值；为 `None` 时展示 `calculated_date_count` 并标记系统计算来源；值为0时必须展示0。
7. 模板显示真实 `sequence_number`，不得使用循环序号重新编号。
8. 退出入口调用成员3的 `accounts:student_logout` POST接口。

## 7. Interface Contract Update

消费文件：

```text
docs/integration_contracts/student_session_contract.md
```

接口名称：`get_current_student(request)`、`student_required`。

输入：带Session的 `HttpRequest`。

输出：经验证的当前 Student 或登录重定向。

异常：无效Session由提供方清理；材料关联为空由个人页显示空状态。

调用方：成员4。提供方：成员3。

成员4只在 Module Notes 记录实际导入路径，不改变契约行为。

## 8. Required Tests

测试文件：

```text
tests/test_student_profile.py
tests/test_student_flow_integration.py
```

必须覆盖：

1. 匿名访问个人页被重定向。
2. 登录学生只看到本人姓名和学号。
3. GET、POST和URL无法切换学生。
4. 申请记录存在和缺失。
5. `reported_total_count`为正数、0和None。
6. None时展示计算值和正确来源说明。
7. 只显示 `is_active=True` 的明细。
8. 明细按真实 `sequence_number` 排序和标号。
9. 无汇总、无明细时页面正常。
10. 无效Session不返回500。
11. 页面退出表单使用正确URL和POST。
12. 匿名用户不能通过本PR的任何管理员路由读取学生数据。

## 9. Acceptance Criteria

Given：学生A已登录，数据库同时存在学生B。
When：访问 `/students/me/` 并提交包含B主键的请求参数。
Then：页面只返回A的信息。

Given：Excel填报总数为空、系统计算数为5。
When：访问个人页。
Then：展示5并说明来源为系统计算，不修改原始字段。

Given：存在有效和失效思想汇报。
When：查看个人页。
Then：只按 `sequence_number` 显示有效记录。

Given：未登录访问管理员学生详情。
When：请求任意学生主键。
Then：本PR不提供该越界实现，数据不会被匿名返回。

## 10. PR提交要求

提交前必须：

- 等待并记录成员3最终接口SHA；
- 同步最新 `develop`，解决与成员3/5的 `students` 文件冲突；
- 四项Django命令全部通过；
- 新增真实个人页和完整流程测试；
- 更新 Module Notes 和接口消费路径；
- README无需修改时在PR描述说明原因；
- PR描述明确列出已删除的越界登录和管理员代码；
- 最终SHA通过仓库策略及Windows/Ubuntu CI。

## Integration Risk

直接依赖成员3认证接口，并与成员5共同修改 `apps/students/views.py` 和 `urls.py`。修复完成后必须通知成员3、成员5和负责人，并在集成分支验证学生/管理员路由均未丢失。

## PR界面的comment

```text
Block：当前分支存在匿名管理员详情数据泄露、个人页NoReverseMatch、材料上下文缺失和重复认证实现。请删除所有登录/退出及管理员视图，只基于成员3冻结接口实现 /students/me/，恢复 student_profile.html，并补齐本人隔离、总篇数fallback、有效明细排序和空状态测试。完成前不得合并。
```

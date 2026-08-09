# 任务卡：成员4 第二轮迭代学生个人页

## 任务目标

从最新develop干净实现学生本人材料只读页，完成登录→本人页→退出闭环。

## 任务背景

旧分支包含重复模型、越界迁移和临时登录逻辑，不具备合并价值；认证接口现已稳定。

## 前置依赖

- `student_session_contract.md`
- 新增`student_profile_contract.md`
- 当前`develop`中的`Student`和`materials`模型结构；本任务不得修改模型或迁移

## 允许范围

- `apps/students/views.py`
- `apps/students/urls.py`中的学生本人路由
- `templates/students/student_profile.html`
- `tests/test_student_profile.py`
- `tests/test_student_flow_integration.py`
- `docs/04_module_notes/student_profile.md`

## 禁止范围

- 不实现或复制登录、退出和会话解析。
- 不修改任何模型或迁移。
- 不实现管理员列表/详情。
- 不接受URL、GET或POST目标学生ID。
- 不写任何业务数据。

## 接口契约

创建`student_profile_contract.md`，冻结：`request.current_student`身份、页面路由、模板上下文字段、总篇数展示口径和来源、思想汇报过滤与排序、最近更新时间口径、空数据及未登录行为。

冻结契约只约束调用方可观察的接口和行为，不冻结实现代码。`select_related()`、`prefetch_related()`及私有辅助函数属于实现与性能要求，可在不改变契约行为的前提下调整。

## 实施建议

使用`@student_required`；只从`request.current_student`出发查询`application_record`、`report_summary`、有效`ideological_reports`，避免N+1。不得直接重新解析`request.session["student_id"]`。

个人页至少展示姓名、学号、党支部、发展阶段、职务、状态、申请入党时间、Excel填报总篇数、系统计算日期数、统计来源、思想汇报明细和最近更新时间。`reported_total_count=None`显示“未知”，`reported_total_count=0`显示`0`，不得混淆二者。

## 必须测试

- 未登录重定向。
- 只能显示当前会话对应的学生。
- 伪造参数不能越权。
- 申请记录/汇总/明细完整展示。
- `reported_total_count=None`与`0`的展示语义正确。
- 最近更新时间来源符合契约。
- 无关联数据正常显示。
- 只显示`is_active=True`并按次数升序。
- 页面请求数据库零写入。
- 登录→本人页→POST退出→再次访问拒绝。

## 验收标准

- 页面展示身份和materials模型数据正确。
- `/students/me/`已从公开占位`TemplateView`替换为受`@student_required`保护的真实只读视图。
- 无重复认证或模型实现。
- 全量测试和双平台持续集成检查通过。

# 任务卡：成员5 第二轮迭代管理员权限与查询

## 任务目标

从最新develop干净重建管理员登录、权限、学生查询、详情和基础审计闭环。

## 任务背景

旧分支落后31个develop提交并与稳定学生认证冲突，禁止整体合并；`admin_permission_contract.md`已有规范但没有实现。

## 前置依赖

- `admin_permission_contract.md`
- 当前`develop`中的`AdminUser`、`AdminRole`、`OperationLog`、`Student`和`materials`模型结构；本任务不得修改模型或迁移
- 新增`admin_query_contract.md`

## 允许范围

- `apps/accounts/permissions.py`
- 管理员相关`apps/accounts/views.py`和`urls.py`
- `apps/audit/services.py`
- 管理员相关`apps/students/views.py`和`urls.py`
- 管理员模板
- `tests/test_admin_query.py`
- Module Notes与`admin_query_contract.md`

## 禁止范围

- 不修改学生认证接口。
- 不复制学生认证模式作为管理员认证；管理员继续使用Django Auth。
- 不实现Excel上传、解析、导入或回滚。
- 不修改冻结模型和迁移。
- 不整体合并旧`feature/admin-query`。

## 接口契约

实现既有`admin_permission_contract.md`中的唯一权限工具和`record_operation_log()`；新增`admin_query_contract.md`冻结管理员登录与POST退出路由、登录成功与失败行为、筛选、分页、详情、统计来源和响应语义。

冻结契约不等于冻结代码文件。成员5必须在允许范围内实现契约；内部查询、视图组织和私有辅助函数可调整，但不得改变公共导入路径、角色枚举、权限矩阵和已冻结响应行为。

管理员与学生认证采用对称隔离规则：

- 管理员退出只清除Django管理员认证，保留同一浏览器中的`student_id`。
- 学生退出只删除`student_id`，保留Django管理员认证。
- 管理员权限只读取Django认证和`AdminUser.role`，不得读取`student_id`。

## 实施建议

人工迁移可复用查询逻辑；先实现`apps/accounts/permissions.py`中的唯一权限工具，再实现业务管理员登录、POST退出和学生查询。管理员登录使用Django `authenticate()`与`login()`；退出只清除管理员认证。类视图Mixin只能是同一角色判断的薄封装。

成员5负责提供并测试`data_admin_required`等权限工具，不进入Excel导入业务；成员7负责将工具应用到真实上传、预览、确认和回滚入口，并完成真实导入URL的角色集成测试。

## 必须测试

- 管理员登录和POST退出。
- 管理员退出后Django管理员认证被清除且`student_id`保留。
- 学生退出后`student_id`被删除且Django管理员认证保留。
- viewer_admin/data_admin查询允许。
- 未登录重定向、未知角色403。
- viewer_admin导入入口403、data_admin允许。
- 姓名、学号、支部、阶段、状态及组合筛选。
- 非法筛选参数不500，分页保留参数。
- 详情404、有效思想汇报过滤、统计来源。
- 登录、退出、查看详情审计及可信IP规则。

## 验收标准

- `admin_permission_contract.md`有唯一实现且成员7可直接导入。
- `/accounts/admin-login/`、管理员学生列表和详情已从公开占位`TemplateView`替换为真实受保护视图。
- 不覆盖或回退学生认证实现。
- 查询列表、详情和权限矩阵在同一最终SHA通过。

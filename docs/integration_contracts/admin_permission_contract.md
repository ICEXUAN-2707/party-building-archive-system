# 管理员权限与审计接口契约

## 1. 契约状态

| 项目 | 内容 |
| --- | --- |
| 契约状态 | 冻结 |
| 实现状态 | 开发中，尚未合入 `develop@42abdf7` |
| 最后核验 | 2026-08-12 |
| 提供方 | 成员5，`accounts` 与 `audit` 模块 |
| 调用方 | 成员5查询页面、成员7导入模块 |
| 依据 | `docs/spec.md`、成员5任务Spec、PR Review Report |

## 2. 冻结角色

```text
viewer_admin
data_admin
```

不得新增同义角色或在调用模块中复制角色判断。

## 3. 权限矩阵

| 身份 | 学生列表/管理员详情 | 上传、预览、确认导入、回滚 |
| --- | --- | --- |
| 未登录 | 禁止，跳转管理员登录 | 禁止，跳转管理员登录 |
| `viewer_admin` | 允许 | 禁止，返回403 |
| `data_admin` | 允许 | 允许 |
| 非法或未知角色 | 禁止，返回403 | 禁止，返回403 |

权限必须在每个后端入口执行，模板隐藏按钮只能作为辅助。

## 4. 提供接口

最终实现文件固定为：

```text
apps/accounts/permissions.py
```

### 4.1 `admin_required(view_func)`

要求有效的 Django 管理员认证。未登录时跳转 `accounts:admin_login`。

### 4.2 `admin_role_required(*roles)`

输入：一个或多个 `AdminRole` 冻结值。

输出：视图装饰器。

行为：

- 未登录：跳转管理员登录。
- 已登录但角色不在允许集合：抛出 `PermissionDenied`，由 Django 返回403。
- 角色合法：调用原视图。

### 4.3 `viewer_or_data_admin_required(view_func)`

允许 `viewer_admin` 和 `data_admin` 访问查询页面。

### 4.4 `data_admin_required(view_func)`

只允许 `data_admin` 访问导入相关页面和修改操作。

类视图如需 Mixin，可以基于上述相同判断提供薄封装；不得维护第二套角色规则。

## 5. 审计接口

文件：

```text
apps/audit/services.py
```

接口：

```python
record_operation_log(
    request,
    action: str,
    target_type: str = "",
    target_id: str = "",
    description: str = "",
) -> OperationLog | None
```

输入：当前请求及操作描述。

输出：认证管理员对应的 `OperationLog`；未认证请求返回 `None`。

异常：数据库写入失败不得静默吞掉。

IP规则：当前未配置可信反向代理时使用 `REMOTE_ADDR`。只有部署配置明确可信代理后，才可采用经过验证的转发头。

## 6. 操作归属

成员5记录：

```text
admin_login
admin_logout
view_student_detail
```

成员7调用同一服务记录：

```text
upload_excel
confirm_import
rollback_import
```

成员5不得进入导入流程代替成员7写日志，成员7不得复制审计服务。

## 7. Session 交叉约束

管理员登录与学生登录互不替代。管理员权限只读取 Django 管理员认证，不读取 `student_id`；学生权限只读取 `student_id`，不把管理员认证当作学生身份。

冻结的对称隔离规则：

1. 学生退出只删除`student_id`，不得清除Django管理员认证。
2. 管理员退出同时清除Django管理员认证和同一Session中的`student_id`。
3. 管理员登录不得覆盖或删除`student_id`。
4. 成员5不得通过修改学生认证接口实现管理员退出。

## 8. 调用方约束

成员7必须导入本契约中的权限工具，不得在 `imports` 模块中使用字符串比较重新实现角色判断。成员5只提供权限工具，不修改成员7的上传、预览、确认或回滚业务视图。

## 9. 契约测试

1. 未登录请求被重定向到管理员登录。
2. `viewer_admin` 可以查询学生。
3. `viewer_admin` 直接请求导入入口返回403。
4. `data_admin` 可以访问导入入口。
5. 未知角色不能访问查询或导入入口。
6. 模板中是否显示按钮不影响后端结果。
7. 登录、退出和查看详情生成正确审计记录。
8. 审计日志不会信任未经配置的客户端转发头。
9. 管理员退出后Django管理员认证和`student_id`均被清除；学生退出后Django管理员认证保持不变。

## 10. 变更规则

接口名称、导入路径、角色响应方式或审计字段发生变化时，必须同步更新本契约、成员5/7 Module Notes 和权限集成测试。

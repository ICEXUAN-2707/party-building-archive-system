# 管理员登录与学生查询接口契约

## 1. 契约状态

| 项目 | 内容 |
| --- | --- |
| 状态 | FROZEN |
| 实现状态 | 已实现，PR #3合入 `develop@d2868b4` |
| 版本 | Sprint 2 / 1.0 |
| 冻结日期 | 2026-08-09 |
| 提供方 | 成员5，`accounts`、`students`与`audit`模块 |
| 消费方 | 管理员模板、成员7权限消费者、成员2集成测试 |
| 依据基线 | `develop@068c27fb7e41ec6f77299ebf3bbac68162714f63` |
| 依赖 | `admin_permission_contract.md`、`student_session_contract.md`、`docs/spec.md` V1.2 |

本契约冻结登录、退出、查询和响应语义，不冻结函数视图、类视图、查询表达式或私有辅助函数的实现形式。

## 2. 管理员登录

```text
methods: GET, POST
path: /accounts/admin-login/
url name: accounts:admin_login
fields: username, password
```

规则：

1. 使用Django`authenticate()`和`login()`以及项目的`AdminUser`。
2. 只允许`is_active=True`且认证成功的管理员登录。
3. 登录成功跳转`students:admin_student_list`并记录`admin_login`。
4. 登录失败返回同一页面和统一错误提示，不泄露用户名、密码、停用状态或具体失败原因。
5. 登录失败不写业务`OperationLog`；安全失败事件不属于本契约。
6. 管理员登录不得覆盖或删除`student_id`。
7. 已登录且角色合法的管理员访问登录页时重定向学生列表。

## 3. 管理员退出

```text
method: POST
path: /accounts/admin-logout/
url name: accounts:admin_logout
success redirect: accounts:admin_login
```

规则：

1. 退出必须使用带CSRF保护的POST。
2. 同时清除Django管理员认证和`request.session["student_id"]`。
3. GET不得执行退出；Django可返回405。
4. 对已认证管理员记录`admin_logout`。
5. 学生退出的对称行为继续由`student_session_contract.md`控制，不得在成员5代码中重写。

## 4. 权限

查询页面必须消费`apps.accounts.permissions.viewer_or_data_admin_required`或同一冻结判断的薄Mixin：

| 身份 | 列表与详情 |
| --- | --- |
| 未登录 | 重定向`accounts:admin_login` |
| `viewer_admin` | 允许 |
| `data_admin` | 允许 |
| 已认证但角色未知 | 403 |
| `is_active=False` | 不视为有效管理员 |

模板隐藏链接不能替代后端权限检查。

## 5. 学生列表

```text
method: GET
path: /students/admin/students/
url name: students:admin_student_list
page size: 20（固定，不开放page_size）
```

冻结查询参数：

| 参数 | 匹配方式 | 合法值 |
| --- | --- | --- |
| `name` | 去除首尾空白后包含匹配 | 任意非空字符串 |
| `student_number` | 去除首尾空白后包含匹配 | 任意非空字符串 |
| `branch` | 精确匹配`PartyBranch.id` | 现存支部正整数主键 |
| `development_stage` | 精确匹配 | `ACTIVIST`、`PROBATIONARY`、`FULL_MEMBER` |
| `status` | 精确匹配 | `active`、`inactive` |
| `page` | 分页 | 正整数页码 |

规则：

1. 多个有效条件使用AND组合。
2. 空字符串等同未提供该条件。
3. 非法`branch`、阶段或状态返回200并展示筛选错误，不得500或静默改成其他条件。
4. 非法筛选请求不得返回未筛选的全量结果；结果集合应为空。
5. 非法或越界页码使用Django`Paginator.get_page()`语义：非法值回到第一页，超过末页回到最后一页。
6. 翻页链接保留所有有效筛选条件，并使用安全URL编码。
7. 默认排序采用`Student`模型排序，即按`student_number`升序。

列表至少展示姓名、学号、支部、发展阶段、职务、状态、更新时间和详情入口。

推荐模板上下文字段：

```text
page_obj
students
filter_values
filter_errors
branches
development_stage_choices
status_choices
```

## 6. 学生详情

```text
method: GET
path: /students/admin/students/<int:pk>/
url name: students:admin_student_detail
```

规则：

1. 学生不存在返回404，不记录`view_student_detail`。
2. 成功查看后记录`view_student_detail`，目标类型为`student`，目标ID为学生主键字符串。
3. 展示学生基本信息、申请记录、思想汇报汇总、有效思想汇报、来源批次和更新时间。
4. 有效思想汇报按`sequence_number`升序。
5. 关联为空时正常展示，不返回500。
6. 管理员详情必须同时展示`reported_total_count`、`calculated_date_count`和当前页面采用的统计来源。
7. 页面展示总篇数遵循`docs/spec.md`：填报值非空时使用填报值，否则使用计算值并明确标注来源。

## 7. 审计

统一调用`apps.audit.services.record_operation_log()`：

```text
admin_login
admin_logout
view_student_detail
```

1. 未认证请求不创建业务操作日志。
2. 登录失败、查询列表、筛选失败和详情404不创建上述成功事件。
3. 未配置可信代理时IP只使用`REMOTE_ADDR`。
4. 审计写入失败不得静默吞掉。

## 8. 副作用

列表与详情只读，除成功详情审计外不得写入`Student`或材料业务表。管理员退出按已确认决策同时清除管理员认证和`student_id`；学生退出仍只清除学生身份。

## 9. 契约测试

1. 登录成功、失败和停用管理员场景。
2. 已登录合法管理员访问登录页重定向列表。
3. POST退出同时清除管理员认证和`student_id`。
4. 学生退出删除`student_id`并保留管理员认证。
5. GET退出不执行退出。
6. 匿名列表和详情重定向登录。
7. `viewer_admin`、`data_admin`均可查询，未知角色返回403。
8. 五类筛选和组合筛选正确。
9. 非法支部、阶段或状态返回200、显示错误且不泄露全量结果。
10. 分页固定20条并保留筛选参数。
11. 详情404、空关联、有效明细过滤和统计来源正确。
12. 成功登录、退出、查看详情生成正确审计。
13. 查询请求不修改学生或材料数据。

## 10. 禁止行为

- 不使用学生Session进行管理员认证。
- 不修改学生认证接口实现管理员退出。
- 不复制角色字符串判断。
- 不整体合并旧`feature/admin-query`。
- 不修改冻结模型或迁移。
- 不进入Excel上传、预览、确认或回滚业务。

## 11. 变更规则

路由、筛选参数、分页、角色响应、Session隔离、详情字段或审计事件变化时，必须同步更新本契约、`admin_permission_contract.md`、成员5/7 Module Notes及成员2集成测试，并由成员5、受影响消费者和成员1共同确认。

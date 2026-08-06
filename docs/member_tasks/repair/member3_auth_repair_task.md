# Task Card

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 成员 | 成员3 |
| 模块 | `accounts` 学生认证 |
| 关联PR | `feature/student-login-permission-new`，Review SHA `07121ed` |
| 优先级 | P1 |
| 预计工作量 | 0.5～1个工作日 |
| 前置契约 | `docs/integration_contracts/student_session_contract.md` |
| 调用方 | 成员4学生个人页 |

## 2. Original Problem

### AUTH-01：擅自限制学生状态

- 文件位置：`apps/accounts/views.py:59-67`
- 当前行为：姓名和学号匹配之外，还要求 `status=StudentStatus.ACTIVE`。
- 实际风险：已有学生可能因未批准的状态规则无法登录，改变冻结认证口径。

### AUTH-02：学生退出允许GET

- 文件位置：`apps/accounts/urls.py:10`、`apps/accounts/views.py:94-97`
- 当前行为：退出视图未限制HTTP方法。
- 实际风险：可被跨站链接触发登出，不符合正式POST退出接口。

### AUTH-03：访问保护接口不完整

- 文件位置：`apps/accounts/decorators.py:10-17`、`apps/students/views.py:8-15`
- 当前行为：装饰器只复制未经验证的主键；无效学生由成员3在个人页中处理，并直接渲染登录模板返回200。
- 实际风险：成员4无法复用稳定接口，失效Session行为不一致。

### AUTH-04：错误提示偏离冻结文案

- 文件位置：`apps/accounts/views.py:15`
- 当前行为：提示“姓名或学号不匹配”。
- 实际风险：界面和验收契约漂移。

### AUTH-05：越界实现登录限流

- 文件位置：`apps/accounts/views.py:18-48`及相关测试。
- 当前行为：在基础认证PR中实现基于Session的五次失败锁定。
- 实际风险：扩大成员范围，且清除Cookie即可绕过，产生虚假安全保证。

## 3. Why It Is Wrong

- Spec：学生身份只能使用冻结的 `student_id` Session；退出不能影响管理员认证。
- PRD/成员任务：当前不限制学生状态；限流必须另建子任务。
- Interface Contract：缺少 `get_current_student()`，失效Session没有统一处理。
- Engineering Rule：成员3不负责个人档案展示，不应在 `students` View 中继续承载认证逻辑。

系统层面会导致学生无法按冻结凭证登录、访问保护被不同页面重复实现，并阻塞成员4联调。

## 4. Repair Scope

允许修改：

```text
apps/accounts/forms.py
apps/accounts/views.py
apps/accounts/urls.py
apps/accounts/decorators.py 或 apps/accounts/student_access.py（二选一）
templates/accounts/student_login.html
templates/base.html（仅学生POST退出入口）
tests/test_student_auth.py
tests/test_student_session.py
docs/04_module_notes/student_auth.md
docs/integration_contracts/student_session_contract.md（仅最终导入路径确认）
```

允许修改的函数：学生登录、学生退出、`get_current_student`、`student_required`。

## 5. Forbidden Modification Scope

禁止：

- 修改 `Student`、材料或导入模型及迁移；
- 实现学生个人资料查询；
- 实现管理员登录或管理员权限；
- 修改管理员退出行为；
- 根据 `Student.status` 增加登录限制；
- 保留或重新实现登录失败次数限制；
- 从请求参数读取目标学生ID；
- 修改 `docs/spec.md`。

## 6. Implementation Guidance

1. 登录只按清理后的姓名和学号联合查询。
2. 成功时写入 `request.session["student_id"]`，跳转 URL name `students:student_profile`。
3. 失败统一使用“姓名或学号不正确”。
4. 在一个公共模块内实现 `get_current_student(request)` 和 `student_required`。
5. 无效Session值应被清理并重定向，不能返回500或由成员4重复处理。
6. 学生退出添加 `require_POST`，只执行 `session.pop("student_id", None)`。
7. 删除限流常量、Session键、分支和专属测试。

不要直接生成个人页逻辑；成员4只消费验证后的 Student。

## 7. Interface Contract Update

更新文件：

```text
docs/integration_contracts/student_session_contract.md
```

接口：

```text
get_current_student(request) -> Student | None
student_required(view_func) -> wrapped view
POST accounts:student_logout
```

输入：`HttpRequest`及其 `student_id` Session。

输出：验证后的 Student、重定向响应或退出重定向。

异常：无效Session不得500；数据库系统异常不得静默吞掉。

提供方：成员3。调用方：成员4。

如果最终公共模块不是 `student_access.py`，只允许更新契约中的导入路径，不得改变行为。

## 8. Required Tests

测试文件：

```text
tests/test_student_auth.py
tests/test_student_session.py
```

必须覆盖：

1. 正确姓名学号登录。
2. 任一凭证错误统一失败。
3. 空输入失败且不写Session。
4. `inactive` 学生仍按当前冻结规则通过正确凭证登录。
5. 未登录访问受保护页重定向。
6. 不存在、非整数和失效Session被清理。
7. GET退出返回405。
8. POST退出只删除 `student_id`。
9. 学生退出不影响已存在的管理员认证。
10. GET/POST中的学生ID不能覆盖Session。

验收目标：测试调用真实生产视图和权限工具，不得在测试中复制认证逻辑。

## 9. Acceptance Criteria

Given：数据库存在任意状态的学生。
When：提交正确姓名和学号。
Then：Session写入该学生主键并进入本人页面。

Given：Session引用不存在的学生。
When：访问受保护页面。
Then：Session被清理并重定向登录页，不返回500。

Given：同一浏览器已登录管理员和学生。
When：学生通过POST退出。
Then：只删除学生身份，管理员认证仍有效。

Given：请求携带另一个学生ID。
When：访问受保护页面。
Then：请求参数被忽略，只采用Session身份。

## 10. PR提交要求

提交前必须：

- 同步最新 `develop` 并人工解决与成员5的 `accounts` 冲突；
- 四项Django命令全部通过；
- Module Notes记录最终接口导入路径；
- Interface Contract与实现一致；
- README无需修改时在PR描述说明“本修复不改变安装和启动步骤”；
- PR描述列出移除的越界限流和新增测试；
- 最终SHA重新通过仓库策略及Windows/Ubuntu CI。

## Integration Risk

影响成员4个人页和学生端完整流程；`accounts/views.py`、`urls.py`、权限文件与成员5分支存在文本冲突。接口确认后必须通知成员4、成员5和负责人。

## PR界面的comment

```text
Request changes：请按 AUTH-01～AUTH-05 修复。重点是移除未批准的状态限制和Session限流，提供统一 get_current_student/student_required 接口，并将学生退出限定为POST且只删除 student_id。请同步更新 student_session_contract、Module Notes和真实生产测试；完成前不要与成员4个人页自行拼接认证逻辑。
```

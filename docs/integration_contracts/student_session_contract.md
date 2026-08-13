# 学生 Session 与访问保护接口契约

## 1. 契约状态

| 项目 | 内容 |
| --- | --- |
| 契约状态 | 冻结 |
| 实现状态 | 已合入 `develop` |
| 实现基线 | `develop@42abdf7` |
| 最后核验 | 2026-08-12 |
| 提供方 | 成员3，`accounts` 模块 |
| 调用方 | 成员4，`students` 学生个人页 |
| 依据 | `docs/spec.md`、成员3/4任务Spec、PR Review Report |

本契约只定义学生身份识别和访问保护，不定义学生档案展示、管理员认证或登录失败限流。

## 2. Session 契约

```text
key: student_id
value: Student 数据库主键（严格正整数类型）
```

规则：

1. 登录成功后先调用 `request.session.cycle_key()`，再写入 `request.session["student_id"] = student.id`；轮换不得清除管理员认证或其他Session数据。
2. 当前学生只能由该 Session 值确定。
3. URL、GET、POST 和隐藏表单字段不得指定或覆盖目标学生 ID。
4. Session 值必须满足 `type(value) is int and value > 0`；数字字符串、布尔值、浮点数、零、负数或不存在的主键必须删除并要求重新登录。
5. 学生退出只删除 `student_id`，不得调用会清空管理员认证状态的 Session `flush()` 或 Django `logout()`。
6. 当前冻结规则不依据 `Student.status` 拒绝登录。

## 3. 提供接口

唯一公共模块固定为：

```text
apps/accounts/student_access.py
```

不得保留第二套学生访问保护装饰器或兼容接口。

### 3.1 `get_current_student(request)`

输入：

```text
django.http.HttpRequest
```

输出：

```text
有效 Session：Student 实例
缺少或失效 Session：None
```

副作用：

- Session 引用不存在的学生时删除 `request.session["student_id"]`。
- 不写入 Student 或任何材料模型。

异常：

- 无效、非严格正整数或不存在的 Session 值不得导致 500。
- 数据库或系统级异常不得静默吞掉。

调用方：成员4学生个人页及其他只读学生端页面。

### 3.2 `student_required(view_func)`

输入：Django 函数视图。

输出：包装后的函数视图。

行为：

1. 调用 `get_current_student(request)`。
2. 当前学生不存在时，重定向至 `accounts:student_login`。
3. 当前学生存在时，将已验证的 Student 提供给被保护视图；具体采用 `request.current_student` 或再次调用 `get_current_student()`，由成员3在 Module Notes 中固定一种方式。
4. 不接受请求参数中的学生 ID。

### 3.3 学生退出入口

```text
method: POST
url name: accounts:student_logout
path: /accounts/student-logout/
```

成功行为：只删除 `student_id`，然后重定向 `accounts:student_login`。

## 4. 登录行为

```text
输入：name + student_number
成功：写入 student_id，跳转 students:student_profile
失败：统一提示“姓名或学号不正确”，不写入 student_id
```

登录失败次数限制不属于本轮修复范围。

## 5. 调用示例

```python
@student_required
def student_profile(request):
    student = get_current_student(request)
    ...
```

示例只说明调用关系，不构成完整实现。

## 6. 契约测试

1. 正确姓名和学号写入 `Student.id`。
2. 错误凭证不写 Session。
3. 未登录访问受保护页面会重定向。
4. 失效、字符串、布尔值、浮点数、非正整数和不存在的 Session 值会被清理且不返回 500。
5. 请求参数不能覆盖 Session 身份。
6. POST 学生退出只删除 `student_id`。
7. 学生退出后管理员认证状态保持不变。
8. 登录轮换Session key，同时保留管理员认证状态。
9. 数据库系统异常不得被当成无效Session静默吞掉。

## 7. 变更规则

Session 键、退出方式、保护工具行为或最终导入路径发生变化时，必须同时更新：

```text
本契约
成员3 Module Notes
成员4 Module Notes
成员3/4联调测试
```

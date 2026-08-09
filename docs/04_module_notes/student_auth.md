# 学生认证模块

负责人：成员3

提供方：`accounts`

调用方：成员4学生个人页及其他只读学生端页面

## 1. 模块边界

本模块只负责姓名与学号登录、学生 Session、访问保护和学生退出。

本模块不负责学生档案展示、管理员认证或权限、管理员查询、登录失败限流、Excel导入及回滚。

## 2. 唯一公共接口

最终导入路径：

```python
from apps.accounts.student_access import get_current_student, student_required
```

`apps.accounts.student_access` 是唯一学生身份识别入口，不存在第二套装饰器或兼容接口。

### `get_current_student(request)`

- 只读取 `request.session["student_id"]`。
- Session 值必须是严格正整数类型的 `Student.id`；布尔值、字符串、浮点数、零和负数均无效。
- 有效值返回已验证的 `Student`。
- 缺少或失效值返回 `None`；失效值同时从 Session 删除。
- 不读取 URL、GET、POST 或隐藏字段中的学生ID。
- 不写 Student 或材料数据；数据库系统异常不静默吞掉。

### `student_required(view_func)`

- 调用 `get_current_student(request)`。
- 无有效学生时重定向 `accounts:student_login`。
- 验证通过时将 Student 固定为 `request.current_student` 后调用原视图。

调用示例：

```python
from apps.accounts.student_access import student_required

@student_required
def student_profile(request):
    student = request.current_student
    ...
```

## 3. Session 契约

```text
key: student_id
value: Student.id（严格正整数）
```

登录成功时轮换 Session key 以防止会话固定，然后写入学生主键。轮换保留同一 Session 中的 Django 管理员认证及其他数据。

学生退出、Session 类型无效或主键不存在时删除 `student_id`。学生退出不得调用 `flush()` 或 Django `logout()`。

## 4. 登录规则

```text
输入：name + student_number
成功：写入 student_id，重定向 students:student_profile
失败：统一提示“姓名或学号不正确”，不写入 student_id
```

- 姓名和学号去除首尾空格后联合查询。
- 不依据 `Student.status` 拒绝登录。
- 不实现登录失败次数限制。
- 不输出真实凭证到日志。

## 5. 退出规则

```text
method: POST
path: /accounts/student-logout/
url name: accounts:student_logout
success redirect: accounts:student_login
```

GET返回405；POST受Django CSRF中间件保护，只删除 `student_id`。

## 6. 测试范围

- 正确、错误、空白及带首尾空格的凭证。
- inactive学生按冻结规则正常登录。
- Session key轮换且管理员认证保留。
- 有效、缺少、失效及类型非法的Session。
- GET/POST参数不能覆盖Session身份。
- 数据库系统异常向上抛出。
- GET退出405、POST退出幂等、CSRF保护及管理员认证保留。

完整测试直接调用生产视图和公共访问保护接口，不复制认证逻辑。

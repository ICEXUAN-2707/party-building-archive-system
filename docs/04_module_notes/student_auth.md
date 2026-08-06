学生认证模块说明（成员3）
1. 模块概述
学生认证模块负责学生登录、退出和访问保护，不涉及管理员认证、学生档案展示或登录失败限流。

本说明替代旧文档 student_login.md，后者中的限流、状态限制等内容已在本轮修复中移除。

2. 模块组件清单
模块文件	职责
apps/accounts/forms.py	StudentLoginForm：姓名/学号字段 + 首尾空格 trim
apps/accounts/views.py	student_login、student_logout 视图
apps/accounts/urls.py	student-login/、student-logout/ 路由
apps/accounts/student_access.py	get_current_student、student_required 统一访问保护接口
apps/accounts/decorators.py	仅保留 SESSION_STUDENT_ID_KEY 常量，供 context_processors.py 使用
templates/accounts/student_login.html	登录页，统一展示 non_field_errors
templates/base.html	学生 POST 退出入口（带 CSRF）
config/settings.py	SESSION_COOKIE_AGE = 1800（30 分钟无操作失效）
3. 最终导入路径
所有学生身份识别和访问保护均通过 apps.accounts.student_access 模块提供。

导入方式：


Plain Text

from apps.accounts.student_access import get_current_student, student_required
旧的 apps/accounts/decorators.py 不再提供认证装饰器，仅保留 SESSION_STUDENT_ID_KEY 常量供 context_processors.py 引用。

4. 核心接口
4.1 get_current_student(request)
项目	说明
输入	django.http.HttpRequest
输出（有效 Session）	Student 实例（已 select_related("branch")）
输出（缺失/失效 Session）	None
副作用	Session 引用不存在的学生时自动删除 request.session["student_id"]
异常处理	无效、非整数、不存在的 Session 值不会导致 500；数据库系统级异常不静默吞掉
4.2 student_required(view_func)
项目	说明
输入	Django 函数视图
输出	包装后的函数视图
未登录/无效 Session	302 重定向至 accounts:student_login
验证通过	将 Student 实例挂载到 request.current_student，被保护视图直接读取
Student 传递方式（固定）：采用 request.current_student，被保护视图无需再次调用 get_current_student()。

调用方（成员4等）只需：


Plain Text

from apps.accounts.student_access import student_required

@student_required
def student_profile(request):
    student = request.current_student
    ...
4.3 学生退出
项目	说明
方法	POST（GET 返回 405）
URL name	accounts:student_logout
Path	/accounts/student-logout/
行为	只执行 request.session.pop("student_id", None)
重定向	accounts:student_login
管理员影响	无，不调用 flush() 或 Django logout()
5. Session 契约
Session Key	类型	写入时机	清理时机
student_id	int（Student 主键）	登录成功	学生退出、无效 Session 被检测到时
SESSION_COOKIE_AGE = 1800：30 分钟无操作 Session 失效。
student_id 与 Django Auth 的 _auth_user_id 无冲突，同一浏览器可同时登录管理员和学生。
6. 登录规则
项目	说明
输入	name + student_number
查询条件	只按姓名和学号联合查询，不限制 Student.status
成功	写入 student_id，302 跳转 students:student_profile
失败	统一提示「姓名或学号不正确」，不写入 student_id
限流	无（本轮修复已移除越界实现的登录失败限流）
登录流程
POST /accounts/student-login/
StudentLoginForm 校验（必填、trim 空格）
校验失败：删除字段级错误，添加统一错误「姓名或学号不正确」
校验通过：Student.objects.filter(name=name, student_number=student_number).first()
查询为空：添加统一错误「姓名或学号不正确」
查询非空：request.session["student_id"] = student.id，302 重定向到 students:student_profile
7. 管理员页面保护
apps/students/urls.py 中的 _admin_guard 装饰器使用 get_current_student(request) 检测学生身份：

检测到学生 Session -> 返回 403 Forbidden
匿名用户、管理员身份 -> 放行
8. 本轮修复变更记录
变更项	说明
移除 Student.status 限制	登录不再要求 status=ACTIVE，所有状态学生均可凭正确姓名+学号登录
移除登录失败限流	删除 5 次/5 分钟锁定逻辑及相关 Session 键
统一访问保护接口	新建 student_access.py，提供 get_current_student 和 student_required
学生退出改为 POST	添加 @require_POST，防止 CSRF 登出
错误提示统一	从「姓名或学号不匹配」改为「姓名或学号不正确」
Student 传递方式	固定为 request.current_student
9. 测试清单
测试文件：

tests/test_student_auth.py：覆盖登录、退出、访问保护
tests/test_student_session.py：覆盖 Session 管理
编号	场景	所在测试方法
1	正确姓名+学号登录成功	test_correct_credentials_login
2	姓名错误统一失败	test_wrong_name_unified_error
3	学号错误统一失败	test_wrong_number_unified_error
4	空输入失败且不写 Session	test_empty_input_no_session
5	inactive 学生仍可登录	test_inactive_student_can_login
6	GET 退出返回 405	test_get_logout_returns_405
7	POST 退出只删除 student_id	test_post_logout_deletes_student_id
8	学生退出不影响管理员认证	test_logout_does_not_affect_admin_auth
9	未登录访问受保护页重定向	test_anonymous_redirected_to_login
10	不存在 Session 被清理	test_invalid_session_cleaned_and_redirected
11	非整数 Session 被清理	test_non_integer_session_cleaned
12	GET 参数不能覆盖 Session	test_query_param_cannot_override_session
13	POST 参数不能覆盖 Session	test_post_param_cannot_override_session
14	Session 时效为 1800 秒	test_session_cookie_age_is_thirty_minutes
15	登录写入 student_id	test_login_writes_student_id
16	登录后可访问个人页	test_profile_accessible_after_login
17	退出后不可访问个人页	test_profile_inaccessible_after_logout
18	失效 Session 访问时被清理	test_expired_session_cleaned_on_access
19	退出重定向到登录页	test_student_logout_redirects_to_login
20	未登录退出仍重定向	test_logout_when_not_logged_in_still_redirects
21	GET 请求展示登录表单	test_get_request_shows_form
所有测试调用真实生产视图和权限工具，不在测试中复制认证逻辑。
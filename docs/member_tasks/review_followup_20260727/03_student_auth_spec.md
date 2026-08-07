# 成员3后续任务Spec：学生认证与Session契约

## 1. 任务摘要

| 项目 | 内容 |
| --- | --- |
| Task ID | `S1-M301`、`S1-M302` |
| 负责人 | 成员3 |
| Sprint | Sprint 1 |
| 优先级 | P0 |
| 当前状态 | `Request Changes`；PR #6必须打回重做 |
| 原PR | `#6 feature/student-login-permission -> main`，冲突状态`dirty` |
| Branch | 从最新`develop`新建干净返工分支，建议`fix/student-auth-review` |
| 前置依赖 | `S1-L01`接口契约 |
| 提供给成员4 | `student_id` Session、学生访问保护工具 |

## 2. 目标

实现：

```text
姓名+学号
→ 匹配已有Student
→ request.session["student_id"] = Student.id
→ 跳转 students:student_profile
```

## 3. PR #6返工与Git基线要求

PR #6从仓库初始提交分出，目标错误地指向`main`，并重复携带项目骨架；不得直接解决冲突后合并。

成员3必须：

1. 将PR #6关闭或转为Draft并标明按本任务卡返工。
2. 获取最新远端`develop`并记录返工基线SHA。
3. 从该SHA创建干净分支，不得从PR #6、`main`或旧功能分支创建。
4. 只迁移学生认证任务范围内、经过人工复核的表单、视图、路由、模板和测试。
5. 不迁移重复骨架、旧配置、其他成员页面实现或完整登录失败次数限制。
6. 新PR目标必须为`develop`，并记录基线SHA、最终测试SHA和CI链接。

## 4. 负责范围

### S1-M301：实现认证流程

1. 学生登录表单。
2. 姓名和学号联合校验。
3. 成功写入Session。
4. 失败统一提示，不泄露具体匹配情况。
5. 学生退出并删除 `student_id`。
6. 学生访问保护装饰器或Mixin。
7. Session中学生ID失效时清理Session并返回登录页。

### S1-M302：测试与Module Notes

记录成员4如何复用访问保护工具，以及登录、退出、失效Session的行为。

## 5. 明确禁止范围

1. 不新增学生账号模型。
2. 不使用Django管理员登录替代学生登录。
3. 不展示学生完整档案。
4. 不允许前端传入目标学生ID。
5. 不实现登录失败次数限制，除非另建任务。
6. 不修改Student冻结字段。
7. 不直接向`main`提交或合并。
8. 不整体合并PR #6旧分支。
9. 不使用强推、历史重写或删除迁移解决返工。

## 6. 预计修改文件

```text
apps/accounts/forms.py
apps/accounts/views.py
apps/accounts/urls.py
apps/accounts/decorators.py 或 student_access.py
templates/accounts/student_login.html
tests/test_student_auth.py
docs/04_module_notes/student_auth.md
```

## 7. 开发步骤

1. 关闭或转Draft处理PR #6，并从最新`develop`创建干净返工分支。
2. 逐文件人工复核旧实现，只迁移本任务允许范围。
3. 定义表单字段和空值校验。
4. 使用ORM联合查询姓名和学号。
5. 写入冻结Session键。
6. 实现退出。
7. 实现访问保护和失效ID处理。
8. 补齐测试。
9. 向成员4提供最小调用示例。

## 8. 测试要求

1. 正确姓名+学号登录成功。
2. 姓名正确、学号错误失败。
3. 学号正确、姓名错误失败。
4. 空输入失败。
5. 登录成功后Session值等于Student主键。
6. 登录失败不写Session。
7. 退出删除Session。
8. 未登录访问个人页被拒绝。
9. Session引用不存在学生时安全退出。
10. 不允许请求参数覆盖Session身份。

## 9. 验收标准

1. 成员4可直接复用保护工具。
2. 登录成功跳转使用URL name，不硬编码路径。
3. 不记录真实姓名学号到日志。
4. 所有测试和Django检查通过。
5. 新分支可验证为从记录的最新`develop`基线创建。
6. 新PR目标为`develop`且不包含重复项目骨架。

## 10. CI合并门禁

1. 分支必须从最新`develop`创建，PR目标必须为`develop`。
2. 登录、Session、权限和失败路径测试必须提交到仓库，由完整测试套件执行。
3. 最终待合并SHA必须同时通过`Repository policy`、`Django tests (ubuntu-latest)`、`Django tests (windows-latest)`。
4. PR新增提交或同步`develop`后必须等待新SHA重新通过，禁止复用旧运行结果。
5. 任一检查未成功时不得请求合并；本地测试不能替代CI。

## 11. 完成证据

```text
PR #6关闭或转Draft记录
返工基线SHA
新的返工PR
测试输出
Session断言
Module Notes
与成员4的接口确认
最终测试SHA
三项CI检查成功链接
```

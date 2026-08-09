# 任务卡：成员3 第二轮迭代认证维护与联调支持

## 任务目标

维护已冻结的学生认证接口，并帮助成员4完成真实消费者联调，不新增认证功能。

## 任务背景

学生认证已稳定；第二轮迭代的风险来自消费者绕过`request.current_student`或重新实现登录。

## 前置依赖

- `student_session_contract.md`
- 成员4的`student_profile_contract.md`

## 允许范围

- `apps/accounts/student_access.py`仅限缺陷修复
- `tests/test_student_auth.py`
- `tests/test_student_session.py`
- 成员3/4联调测试和Module Notes校准

## 禁止范围

- 不增加状态限制或登录限流。
- 不实现学生个人页。
- 不修改Student模型、管理员认证或Excel模块。
- 不创建第二套装饰器。

## 接口契约

保持`student_id`、`get_current_student()`、`student_required()`和POST退出不变；若消费者发现缺口，先提交契约变更申请。

## 实施建议

主要工作是审查成员4的调用方式并补充回归场景，不主动重构稳定代码。

## 必须测试

- 会话身份不能被URL、GET或POST参数覆盖。
- 无效会话清理。
- 学生退出不影响管理员认证。
- 学生个人页使用`request.current_student`。

## 验收标准

- 成员4无需复制认证逻辑。
- 认证原有安全测试全部通过。
- 本任务无不必要生产代码变更。

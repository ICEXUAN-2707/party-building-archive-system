# 成员4后续任务Spec：学生个人页与学生端联调

## 1. 任务摘要

| 项目 | 内容 |
| --- | --- |
| Task ID | `S1-M401`、`S1-M402` |
| 负责人 | 成员4 |
| Sprint | Sprint 1 |
| 优先级 | P0 |
| 当前状态 | 阻塞；等待成员3交付合格的学生认证接口 |
| Branch | `feature/student-profile` |
| 前置依赖 | `S1-M301` |
| 联调对象 | 成员3 |

## 2. 目标

学生登录后只能查看本人：

- 姓名、学号、支部、发展阶段；
- 申请入党时间；
- 思想汇报总篇数；
- 思想汇报明细；
- 最近更新时间。

成员4不得基于PR #6的旧分支开始联调；应等待成员3的新返工PR明确保护工具导入路径和Session行为。

## 3. 负责范围

### S1-M401：实现个人页

1. 将占位View替换为真实只读View。
2. 使用成员3访问保护工具。
3. 从 `request.session["student_id"]` 获取Student。
4. 关联读取申请记录、汇总和明细。
5. 明细按 `sequence_number` 升序。
6. 处理空申请、空汇总、空明细。
7. 不显示其他学生数据。

### S1-M402：学生端联调

验证登录、跳转、本人展示、退出和重新访问的完整请求链。

## 4. 明确禁止范围

1. 不重新实现登录。
2. 不接受URL、GET或POST中的目标学生ID。
3. 不写入Student或材料模型。
4. 不实现管理员查询。
5. 不修改冻结模型和迁移。

## 5. 预计修改文件

```text
apps/students/views.py
apps/students/urls.py
templates/students/student_profile.html
tests/test_student_profile.py
tests/test_student_flow_integration.py
docs/04_module_notes/student_profile.md
```

## 6. 开发步骤

1. 确认成员3保护工具导入路径。
2. 建立只读关联查询。
3. 定义模板上下文。
4. 实现正常和空状态。
5. 补越权与失效Session测试。
6. 与成员3执行真实Session联调。

## 7. 测试要求

1. 当前学生信息展示正确。
2. 有申请记录时显示日期。
3. 缺少申请记录不报错。
4. `reported_total_count=None`显示未知，而不是0。
5. `reported_total_count=0`显示0。
6. 明细为空显示空状态。
7. 明细按序号而非日期排序。
8. Session失效时不返回500。
9. 不能通过请求参数查看其他学生。
10. 退出后不能继续访问。

## 8. 验收标准

```text
登录
→ student_id写入
→ 跳转个人页
→ 只展示本人
→ 退出
→ 再访问被拒绝
```

完整通过，且没有业务数据写入。

## 9. CI合并门禁

1. 分支必须从最新`develop`创建，PR目标必须为`develop`。
2. 本人数据、越权、空关联和完整Session流程测试必须进入完整测试套件。
3. 最终待合并SHA必须同时通过`Repository policy`、`Django tests (ubuntu-latest)`、`Django tests (windows-latest)`。
4. 与成员3联调产生新提交后，必须以新SHA重新完成三项检查。
5. 任一检查未成功时不得请求合并；页面截图和本地测试不能替代CI。

## 10. 完成证据

```text
PR
页面截图
单元测试
联调测试
Module Notes
最终测试SHA
三项CI检查成功链接
```

# 成员5后续任务Spec：管理员查询修复与验收

## 1. 任务摘要

| 项目 | 内容 |
| --- | --- |
| Task ID | `S1-M501`、`S1-M502` |
| 负责人 | 成员5 |
| Sprint | Sprint 1 |
| 优先级 | P0/P1 |
| 当前状态 | PR #3开放，`Request Changes`；落后最新`develop` 8个提交 |
| Branch | 继续使用 `feature/admin-query` |
| PR | `#3 feature/admin-query -> develop` |
| Review结论 | `Request Changes` |
| 合并前置 | P0和关键Major全部修复 |

## 2. 必须修复的问题

| 问题ID | 级别 | 内容 |
| --- | --- | --- |
| AQ-B001 | Blocker | 页面退出链接GET返回405 |
| AQ-M001 | Major | 没有管理员功能自动化测试 |
| AQ-M002 | Major | 列表字段和状态筛选不完整 |
| AQ-M003 | Major | 详情缺少计算数、来源、批次、更新时间 |
| AQ-M004 | Major | 查询审计日志未实现 |
| AQ-M005 | Major | 非法branch筛选触发500 |
| AQ-M006 | Major | Module Notes路径和测试描述不准确 |

## 3. 负责范围

### S1-M501：修复合并阻塞

1. 将退出入口改为带CSRF的POST表单。
2. 验证退出后认证Session被清除。
3. 校验branch和stage筛选值。
4. 非法筛选不得产生500。
5. 分页参数使用安全URL编码。

### S1-M502：补齐交付

1. 列表增加职务、状态、更新时间和详情入口。
2. 增加状态筛选。
3. 详情增加计算日期数、统计来源、批次和更新时间。
4. 新增审计服务。
5. 登录、退出、查看详情写入对应日志。
6. 新增 `tests/test_admin_query.py`。
7. 修正Module Notes路径、分支名和真实测试证据。

## 4. 明确禁止范围

1. 不实现Excel解析、正式导入或回滚。
2. 不修改导入模型状态机。
3. 不修改冻结模型字段。
4. 不用隐藏按钮代替后端权限。
5. 不把测试结果写成未经自动化验证的人工结论。

## 5. 预计修改文件

```text
apps/accounts/views.py
apps/accounts/urls.py
apps/accounts/decorators.py
apps/accounts/mixins.py
apps/students/views.py
apps/audit/services.py
templates/base.html
templates/students/admin_student_list.html
templates/students/admin_student_detail.html
tests/test_admin_query.py
docs/04_module_notes/admin_query.md
```

## 6. 开发步骤

1. 先同步最新`develop`，确认并人工解决`config/settings.py`等重叠改动。
2. 为已发现缺陷写失败测试。
3. 修复POST退出。
4. 增加筛选输入校验。
5. 补列表和详情字段。
6. 实现统一审计服务。
7. 为权限、筛选、404、空数据和日志补测试。
8. 更新Module Notes。
9. 将修复推送到PR #3，并以最终SHA重新完成三项CI检查。

## 7. 测试要求

至少覆盖：

1. 登录成功和失败。
2. 退出使用POST并清除Session。
3. GET退出不作为正式入口。
4. 未登录不能访问列表和详情。
5. viewer可查询但不能进入导入页。
6. data_admin可查询并可进入导入页。
7. 五类筛选均有效。
8. 非法branch/stage不返回500。
9. 翻页保留筛选条件。
10. 列表展示冻结字段。
11. 详情展示汇总原始值和计算值。
12. 关联材料缺失不报错。
13. 学生不存在返回404。
14. 查看详情写入OperationLog。

## 8. 验收标准

1. AQ-B001和AQ-M005复测通过。
2. 成员5原任务Spec完成定义全部满足。
3. `python manage.py test`包含新增管理员测试。
4. Module Notes中的每项测试可在仓库中定位。
5. 重新Review结论至少达到 `Approve after fixes`。

## 9. CI合并门禁

1. 修复分支必须先同步最新`develop`，PR目标必须为`develop`。
2. 管理员认证、角色权限、筛选、审计日志和退出测试必须进入完整测试套件。
3. 最终待合并SHA必须同时通过`Repository policy`、`Django tests (ubuntu-latest)`、`Django tests (windows-latest)`。
4. 解决`config/settings.py`冲突后必须以新的最终SHA重新运行全部检查。
5. 任一检查未成功时不得合并；原PR或旧SHA的成功结果不得复用。

## 10. 完成证据

```text
PR差异
新增测试清单
完整测试输出
权限矩阵
OperationLog断言
更新后的Module Notes
最终测试SHA
三项CI检查成功链接
```

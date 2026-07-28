# 成员1后续任务Spec：接口冻结与Sprint 1集成管理

## 1. 任务摘要

| 项目 | 内容 |
| --- | --- |
| Task ID | `S1-L01`、`S1-L02` |
| 负责人 | 成员1（项目负责人） |
| Sprint | Sprint 1 |
| 优先级 | P0 |
| 当前状态 | 进行中；CI门禁已可用，业务PR仍需返工或修复 |
| 建议分支 | `docs/sprint1-integration-contracts` |
| 问题来源 | Review材料缺失、接口基线不完整、成员分支依赖不清 |
| 主要目标 | 冻结跨模块接口，管理修复顺序，形成可审查的Sprint 1集成候选 |

## 2. 当前问题

1. `docs/member_tasks/README.md`和任务汇总表待本轮建立。
2. 缺少 `docs/member_tasks/00_integration_contracts.md`。
3. 成员3已有PR #6，但目标分支、开发基线和改动范围均不合格；成员4、7仍无远端功能分支。
4. 成员5的PR #3仍为Request Changes，且功能分支落后最新`develop`。
5. 成员6的PR #4仍错误指向`main`，必须基于最新`develop`返工。
6. CI已通过PR #7合入`develop@3a0e41b`，但分支保护是否启用仍需负责人确认。
7. 当前不能直接形成新的Sprint 1业务集成基线。

## 3. 负责范围

### S1-L01：冻结跨模块接口

统一记录：

| 接口 | 提供方 | 消费方 | 冻结内容 |
| --- | --- | --- | --- |
| 学生Session | 成员3 | 成员4 | `student_id = Student.id` |
| 学生个人页 | 成员4 | 成员3 | `students:student_profile` |
| 管理员角色 | 成员5 | 成员7 | `viewer_admin/data_admin` |
| 导入权限 | 成员5 | 成员7 | `data_admin_required`或最终等价接口 |
| Excel解析 | 成员6 | 成员7 | `parse_workbook(Path) -> ParseResult` |
| 导入批次状态 | 成员7 | 管理员页面 | `previewed/success/failed/rolled_back` |

### S1-L02：组织Sprint 1集成门禁

1. 收集成员3、4、5的PR和测试证据。
2. 确认成员5的P0问题已经修复。
3. 按依赖顺序组织临时集成测试。
4. 未通过门禁时不得要求强行合并。
5. 输出Sprint 1是否形成Demo的结论。
6. 要求PR #4和PR #6关闭或转Draft后按任务卡返工。
7. 要求PR #3同步最新`develop`并完成Request Changes。

## 4. 明确禁止范围

1. 不代替成员修改业务代码。
2. 不修改 `docs/spec.md` 冻结规则。
3. 不直接在 `develop` 开发。
4. 不执行强推、历史重写或绕过Review。
5. 不因进度压力跳过权限和Session测试。

## 5. 预计修改文件

```text
docs/member_tasks/README.md
docs/member_tasks/00_integration_contracts.md
docs/reviews/（仅在负责人明确要求落盘时）
```

## 6. 开发步骤

1. 从实际代码和成员Spec提取接口名称、类型和空值规则。
2. 标注接口提供方、消费方和可用时间。
3. 对文档与代码不一致处发起负责人决策。
4. 建立合并门禁清单。
5. 在成员PR修复完成后组织临时集成。
6. 记录测试SHA，避免旧报告套用新提交。

## 7. 验收标准

1. 所有跨模块接口只有一个正式名称。
2. 每个接口都有输入、输出、错误行为和负责人。
3. 成员3、4、5能根据文档完成联调。
4. 成员6、7不再重复实现Excel解析入口。
5. Sprint 1集成结论绑定明确提交SHA。

## 8. CI集成门禁

CI已在PR #7、测试SHA `30941da6`、运行 `30328443814` 上完成首次跨平台验证。

成员1负责执行以下合并门禁：

1. 所有成员功能分支必须从最新`develop`创建，PR目标必须为`develop`。
2. 最终待合并SHA必须同时通过`Repository policy`、`Django tests (ubuntu-latest)`、`Django tests (windows-latest)`。
3. PR新增提交或同步`develop`后，旧SHA的成功结果不得作为合并证据。
4. 任一检查失败、取消、跳过或仍在运行时不得合并。
5. 本地测试和截图不能替代GitHub Actions结果。
6. 集成结论必须记录PR、最终SHA和对应CI运行链接。

## 9. 完成证据

```text
接口契约文档
成员确认记录
PR清单
集成测试输出
最终测试SHA
三项CI检查成功链接
Sprint 1门禁结论
```

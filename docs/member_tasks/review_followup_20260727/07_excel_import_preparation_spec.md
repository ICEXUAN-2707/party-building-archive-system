# 成员7后续任务Spec：导入模块契约准备

## 1. 任务摘要

| 项目 | 内容 |
| --- | --- |
| Task ID | `S1-M701` |
| 负责人 | 成员7 |
| Sprint | Sprint 1联调准备；正式实现属于Sprint 2 |
| 优先级 | P1 |
| 当前状态 | 阻塞；等待成员5权限接口和成员6解析接口稳定 |
| 建议分支 | 暂不要求业务分支；契约确认后使用 `feature/excel-import` |
| 前置依赖 | `S1-L01`；正式开发依赖`S1-M502`、`S2-M601`、`S2-M602` |
| 主要目标 | 明确成员7如何消费权限和解析结果，避免重复实现 |

## 2. 当前问题

1. `data_admin`权限接口尚需成员5完成修复和测试。
2. 成员6尚未交付`parse_workbook(Path) -> ParseResult`。
3. ParseResult错误码和Sheet统计仍在调整。
4. 当前不具备正式导入、预览或回滚的稳定前提。
5. PR #4尚未按`develop`基线返工，当前不得消费其旧分支实现。

## 3. 负责范围

### S1-M701：契约审查和测试设计

1. 审查成员5权限接口调用方式。
2. 审查成员6 ParseResult字段。
3. 建立ParseResult到ImportBatch统计字段映射表。
4. 定义错误行、警告行、失败Sheet的消费行为。
5. 设计预览不写正式数据的测试。
6. 设计确认导入事务测试。
7. 设计最近一次成功导入回滚测试。

## 4. 必须明确的映射

| ParseResult | ImportBatch/预览 |
| --- | --- |
| `total_sheets` | `total_sheets` |
| `success_sheets` | `success_sheets` |
| `failed_sheets` | `failed_sheets` |
| `total_rows` | `total_rows` |
| `success_rows` | `success_rows` |
| `skipped_rows` | `skipped_rows` |
| `warning_rows` | `warning_rows` |
| `errors` | `ImportErrorRecord` |
| `warnings` | `ImportWarningRecord` |

## 5. 明确禁止范围

1. 当前不复制测试中的Excel驱动代码。
2. 不另写表头、日期、次数或支部解析。
3. 不在成员6主接口稳定前实现正式预览。
4. 不绕过成员5的后端权限工具。
5. 不修改冻结模型和迁移。
6. 不使用真实学生Excel。

## 6. 预计产出

```text
导入消费接口检查清单
ParseResult字段映射表
预览测试计划
导入事务测试计划
回滚测试计划
待成员5/6确认问题列表
```

## 7. 开发步骤

1. 阅读最终接口契约。
2. 使用虚构ParseResult样例验证字段是否足够。
3. 标记无法从ParseResult获得的预览数据。
4. 与成员5确认权限调用点。
5. 与成员6确认错误码和空值。
6. 在依赖稳定后再拆分Sprint 2正式任务。

## 8. 验收标准

1. 不存在成员7需要自行解析Excel的字段缺口。
2. 每个ParseResult字段都有明确消费位置。
3. 错误行不会进入正式业务写入计划。
4. 警告行行为明确且可测试。
5. 预览阶段零正式学生数据写入。
6. 正式开发任务具备可执行依赖顺序。

## 9. CI合并门禁

1. 正式开发分支必须从最新`develop`创建，PR目标必须为`develop`。
2. 后续预览零写入、事务、跳过错误行、权限和回滚测试必须进入完整测试套件。
3. 最终待合并SHA必须同时通过`Repository policy`、`Django tests (ubuntu-latest)`、`Django tests (windows-latest)`。
4. 成员5或成员6接口更新导致新提交后，必须以新SHA重新完成三项检查。
5. 任一检查未成功时不得请求合并；依赖分支的成功结果不能替代本分支CI。

## 10. 完成证据

```text
接口检查清单
字段映射表
成员5确认记录
成员6确认记录
测试场景列表
最终测试SHA
三项CI检查成功链接
```

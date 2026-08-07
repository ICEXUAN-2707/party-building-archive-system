# 成员6后续任务Spec：Excel解析主接口与契约修复

## 1. 任务摘要

| 项目 | 内容 |
| --- | --- |
| Task ID | `S2-M601`、`S2-M602` |
| 负责人 | 成员6 |
| Sprint | Sprint 2提前准备 |
| 优先级 | P0/P1 |
| 当前状态 | PR #4开放且错误指向`main`；必须打回重做 |
| Branch | 从最新 `develop` 新建干净返工分支，禁止继续沿用错误基线 |
| Review结论 | `Request Changes` |
| 提供给成员7 | `parse_workbook(Path) -> ParseResult` |

## 2. 必须修复的问题

| 问题ID | 级别 | 内容 |
| --- | --- | --- |
| EP-B000 | Blocker | PR #4 目标分支错误地指向 `main`，且功能分支不是从最新 `develop` 创建 |
| EP-B001 | Blocker | 生产主接口不存在 |
| EP-B002 | Blocker | 端到端测试调用测试内部驱动 |
| EP-M001 | Major | 表头备用正则接受第100次 |
| EP-M002 | Major | 中文次数错误码不一致 |
| EP-M003 | Major | 越界列被静默忽略 |
| EP-M004 | Major | 缺少冻结错误码 |
| EP-M005 | Major | 工作表警告被重复为每行警告 |
| EP-M006 | Major | 未搜索前两行表头 |
| EP-M007 | Major | 非法总篇数等输入静默降级 |
| EP-M008 | Major | Module Notes接口和路径错误 |

## 3. PR #4返工与Git基线要求

当前PR：

```text
PR #4
feature/excel-parser -> main
```

不符合 `docs/02_git_workflow.md`，不得直接合并，也不得由项目负责人代为修复。

成员6必须：

1. 将PR #4关闭或转为Draft，并明确标记需要按本清单返工。
2. 获取最新远端 `develop`，记录作为返工基线的提交SHA。
3. 从该SHA新建干净返工分支，不得从旧 `feature/excel-parser` 或 `main` 创建。
4. 只迁移Excel解析任务范围内、经过人工复核的实现；不得整体合并旧分支。
5. 不得带入旧项目骨架、其他成员业务代码或任务范围外配置。
6. 完成所有Blocker、Major和测试要求后重新提交PR。
7. 新PR目标分支必须为 `develop`。
8. 新PR说明必须记录基线SHA、测试SHA、执行命令和测试结果。
9. 在CI修复并可用后，新PR必须以该测试SHA通过全部必需检查。

当前CI已在`develop@3a0e41b`可用，新返工PR必须执行三项正式检查，不再接受“CI尚未建立”作为缺少证据的理由。

建议分支名由项目负责人审批，例如：

```text
fix/excel-parser-review
```

## 4. 负责范围

### S2-M601：实现生产主接口

```python
def parse_workbook(file_path: Path) -> ParseResult:
    ...
```

必须完成：

1. 验证输入路径。
2. 使用openpyxl打开工作簿。
3. 遍历全部工作表。
4. 识别九个冻结党支部。
5. 在前两行查找正式表头。
6. 失败Sheet不进入有效行。
7. 聚合SheetResult和ParseResult统计。
8. 始终关闭工作簿。

### S2-M602：统一边界和错误

1. 中文次数暂支持第一至第二十。
2. `sequence_number`暂支持1–99。
3. 第100次不得通过任何备用路径。
4. 中文第二十一次必须产生统一错误码。
5. 未知Sheet、表头失败和日期顺序异常使用统一登记码。
6. 缺少总篇数列只产生工作表级警告。
7. 非法总篇数值不得静默变成None。
8. 更新Module Notes，删除绝对路径和不存在的模块引用。

## 5. 明确禁止范围

1. 不写数据库。
2. 不创建ImportBatch。
3. 不实现上传、预览模板、确认导入或回滚。
4. 不要求成员7复制解析聚合代码。
5. 不修改 `docs/spec.md`。
6. 不扩大已暂定的中文和序号范围。
7. 不提交真实Excel。
8. 不直接向 `main` 提交或合并。
9. 不通过整体合并旧分支的方式迁移代码。
10. 不使用强推、历史重写或删除现有迁移文件处理返工。

## 6. 预计修改文件

```text
apps/imports/parser.py
apps/imports/error_codes.py
apps/imports/report_column_utils.py
apps/imports/datatypes.py（仅契约确需时）
tests/test_excel_parser.py
tests/test_imports_parser_header.py
docs/04_module_notes/excel_parser.md
```

## 7. 开发步骤

1. 先完成EP-B000：关闭或转为Draft处理旧PR，基于最新`develop`建立干净返工分支。
2. 逐提交、逐文件人工复核旧实现，只迁移任务范围内代码。
3. 为EP-B001、EP-M001和EP-M002写失败测试。
4. 集中定义九支部映射和错误码。
5. 实现`parse_workbook`。
6. 将测试内部驱动迁移为生产调用。
7. 统一Sheet级和行级统计。
8. 补文件损坏、未知Sheet和表头失败测试。
9. 更新Module Notes和成员7调用示例。
10. 修正后续Git作者身份。
11. 在CI可用后，以最终测试SHA重新提交到`develop`并保存检查链接。

## 8. 测试要求

1. 九个支部全部识别。
2. 多Sheet成功聚合。
3. 一个Sheet失败不阻止其他Sheet预览。
4. 未知Sheet不产生有效学生行。
5. 前两行任一合法表头可被识别。
6. 普通学生行不被当成表头。
7. 第99次合法，第100次错误。
8. 第二十合法，第二十一次错误。
9. 错误码与中央定义完全一致。
10. 缺总篇数列只产生一次Sheet警告。
11. 文件不存在、损坏和非xlsx产生明确系统异常。
12. 所有端到端测试直接调用`parse_workbook`。
13. 解析前后数据库记录数不变。
14. 新PR与记录的最新`develop`基线关系可验证。
15. 新PR的全部CI检查在同一测试SHA上通过。

## 9. 验收标准

1. 成员7只调用一个生产入口。
2. ParseResult所有统计字段含义明确。
3. 不存在测试辅助函数代替业务入口。
4. 临时次数边界在所有路径一致。
5. 测试和文档不包含开发者绝对路径。
6. 新分支确实从记录的最新`develop`提交创建。
7. 新PR目标分支为`develop`，不存在对`main`的直接合并请求。
8. 新PR不包含项目骨架或其他成员任务范围内的额外改动。

## 10. CI合并门禁

1. 返工分支必须从记录的最新`develop`基线SHA创建，新PR目标必须为`develop`。
2. 解析器边界、错误码、多Sheet和数据库零写入测试必须进入完整测试套件。
3. 最终待合并SHA必须同时通过`Repository policy`、`Django tests (ubuntu-latest)`、`Django tests (windows-latest)`。
4. 迁移旧实现、同步`develop`或修复Review意见后，必须以新SHA重新完成三项检查。
5. PR #4、旧分支或旧SHA上的结果均不得作为返工PR的CI证据。
6. 任一检查未成功时不得请求合并。

## 11. 完成证据

```text
PR #4关闭或转为Draft的记录
返工分支基线SHA
新的 feature/fix -> develop PR
最终测试SHA
CI成功运行链接
真实生产入口测试
九支部测试
边界测试
数据库无写入断言
Module Notes
成员7接口确认
```

# 成员2后续任务Spec：配置基线与CI基础

## 1. 任务摘要

| 项目 | 内容 |
| --- | --- |
| Task ID | `S1-A01`、`S1-A02` |
| 负责人 | 成员2（技术架构负责人） |
| Sprint | Sprint 1 |
| 优先级 | P1；已成为合并门禁 |
| 当前状态 | S1-A01、S1-A02已完成；进入CI维护期 |
| 已合入基线 | `develop@3a0e41b`，PR #5、PR #7 |
| 后续建议分支 | CI变更使用独立`fix/ci-*`或`chore/ci-*`分支 |
| 问题来源 | Review基线风险、测试仅依赖人工执行 |
| 主要目标 | 修复环境变量读取，建立最小可用CI |

## 2. 当前问题

以下原Review问题已经完成修复：

```text
操作系统环境变量优先于.env
GitHub Actions工作流可正常解析
Repository policy自动运行
Ubuntu与Windows双平台Django测试自动运行
SQLite使用runner临时目录
```

当前工作转为维护固定检查名称、诊断CI失败和向成员1提供分支保护建议。

## 3. 负责范围

### S1-A01：修复环境变量读取（已完成）

建议优先级：

```text
操作系统环境变量
→ .env
→ 代码默认值
```

必须保持：

- Python 3.12；
- Django 5.x；
- SQLite；
- 不引入额外配置框架，除非负责人另行批准。

### S1-A02：建立最小CI（已完成，持续维护）

CI只负责自动验证，不自动部署、不自动合并。

首版步骤：

1. 检出代码。
2. 安装Python 3.12。
3. 缓存pip依赖（可选）。
4. 安装 `requirements.txt`。
5. 设置测试用临时环境变量。
6. 执行Django四项检查。

## 4. 明确禁止范围

1. 不引入Docker生产部署。
2. 不引入Redis、Celery或新数据库。
3. 不在CI中使用真实密钥、真实Excel或真实学生数据。
4. 不自动向 `main/develop` 推送。
5. 不替代成员模块测试。

## 5. 预计修改文件

```text
config/settings.py
tests/test_settings.py
.github/workflows/ci.yml
README.md（仅补充CI状态或命令说明）
```

## 6. 开发步骤

1. 为现有配置读取补回归测试。
2. 实现OS环境变量优先级。
3. 验证 `.env` 仍可用于Windows本地开发。
4. 已建立GitHub Actions最小工作流。
5. 已在PR #7、测试SHA `30941da6`、运行`30328443814`验证三项检查成功。
6. 将CI设为PR必查项的建议提交负责人审批。
7. 后续CI修改必须使用独立PR，不与业务功能混合。

## 7. 测试要求

1. 环境变量覆盖默认值。
2. `.env`在无OS变量时生效。
3. 空列表配置不产生空字符串项。
4. CI能发现未生成迁移。
5. CI能发现失败测试。
6. CI日志不得输出Secret值。

## 8. 验收标准

1. 本地四项检查仍通过。
2. GitHub PR自动运行CI。
3. CI使用Python 3.12和冻结依赖。
4. 不依赖开发者绝对路径。
5. CI失败时能定位到具体命令。

## 9. CI维护与验收要求

CI已在PR #7、测试SHA `30941da6`、运行 `30328443814` 上完成首次验证，当前正式检查名称为：

```text
Repository policy
Django tests (ubuntu-latest)
Django tests (windows-latest)
```

成员2后续负责：

1. 保持Python 3.12、Ubuntu和Windows双平台矩阵。
2. 保持SQLite位于runner临时目录，不得写入仓库工作区。
3. 保持`check`、迁移检查、空库迁移、完整测试和post-test守卫。
4. CI配置变更必须走独立PR并以同一最终SHA完成三项检查。
5. 工作流解析失败视为CI整体不可用，不得解释为测试失败或测试通过。
6. 未经负责人审批不得加入自动部署、自动合并或真实Secret。
7. 向成员1提供分支保护所需的固定检查名称，不擅自修改job名称。

## 10. 完成证据

```text
配置测试
CI成功运行链接
最终测试SHA
Ubuntu与Windows成功结果
故意失败验证截图或运行记录
Module Notes
```

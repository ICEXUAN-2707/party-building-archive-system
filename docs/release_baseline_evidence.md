# 发布基线证据索引

## 1. 当前判定

| 项目 | 内容 |
| --- | --- |
| 核验日期 | 2026-08-31 |
| 起始代码SHA | `d14003df839217ead49a5c45cf699713a527dd32` |
| 当前候选状态 | Conditional No-Go |
| 原因 | `ci_guard`修复及基线文档尚未形成新的提交SHA |
| 正式候选报告 | 待新SHA形成后重跑 |

本索引不提交Excel、SQLite、媒体文件、备份或密钥。验收产物只保存在Git忽略的授权目录，
仓库仅记录报告摘要、SHA-256和门禁结论。

## 2. 候选内容

当前收敛内容只包括：

```text
docs/current_project_status.md
docs/sprint/release_baseline_convergence_plan.md
docs/release_baseline_evidence.md
scripts/ci_guard.py
tests/test_ci_guard.py
```

`ci_guard`修复用于解决冻结验收流程中的规则冲突：

- `artifacts/acceptance/`是`.gitignore`和验收指南指定的脱敏证据目录；
- 修复前`ci_guard --post-test`会把该目录内的验收Excel判定为测试污染；
- 修复后只豁免精确前缀`artifacts/acceptance/`；
- 仓库根目录、`media/imports/`和其他`artifacts/`子目录仍保持原拦截规则；
- 新增测试同时验证授权目录通过和相邻非授权目录继续被拦截。

## 3. 本地回归证据

### 3.1 基础检查

| 检查 | 结果 |
| --- | --- |
| Python | 3.12.10 |
| Django | 5.2.4 |
| `manage.py check` | 通过 |
| `makemigrations --check --dry-run` | 通过，无模型变更 |
| 空库`migrate --noinput` | 通过 |
| `git diff --check` | 通过 |

### 3.2 全量测试

修复前基线运行：

```text
代码SHA：d14003df839217ead49a5c45cf699713a527dd32
测试数：382
结果：通过
耗时：441.789秒
```

`ci_guard`修复后运行：

```text
代码基线：d14003d加当前未提交收敛差异
测试数：384
结果：通过
耗时：497.505秒
污染检查：通过
```

修复后测试结果证明当前工作树通过，但未提交差异没有稳定Git SHA，因此不能代替正式候选CI。

## 4. 联合验收证据

### 4.1 前置成功报告

| 项目 | 内容 |
| --- | --- |
| 报告Git SHA | `d14003df839217ead49a5c45cf699713a527dd32` |
| 固定种子 | `20260822` |
| 学生数 | 1500 |
| 支部数 | 9 |
| 首批 | 1500行成功，创建1500名学生和4500条思想汇报 |
| 第二批 | 1500行成功，更新1500名学生和4500条思想汇报 |
| 回滚后 | 1500名学生、1500条申请、1500条汇总、4500条有效思想汇报 |
| 重启复查 | 通过 |
| 报告SHA-256 | `DC90575E3481F8CA9941FB3A8363C3B55E7FE14FD62F10D302EDD9BA3AA87B08` |

报告位于本地Git忽略目录：

```text
artifacts/acceptance/run-1500-d14003d-20260831/acceptance_report.json
```

该报告证明`d14003d`业务链路通过。由于随后修复了`ci_guard`，新候选SHA形成后必须使用相同
学生规模和固定种子重新运行，生成新的报告哈希。

## 5. 部署专项证据

| 检查 | 结果 |
| --- | --- |
| 生产设置与安全门禁 | 通过 |
| `manage.py check --deploy` | 通过 |
| Dockerfile契约 | 通过 |
| entrypoint契约 | 通过 |
| Compose契约 | 通过 |
| `docker compose config --quiet` | 通过 |
| 本地Bootstrap资源契约 | 通过 |
| 存活与就绪检查契约 | 通过 |
| 备份自动化契约 | 通过 |
| 部署专项测试 | 39项通过 |

真实镜像构建、容器启动、HTTPS浏览器访问、告警投递和COS异机恢复不属于上述静态/单元验证，
继续作为DEP-08至DEP-10门禁。

## 6. 远端与生产证据缺口

以下证据尚未取得：

1. 新候选SHA；
2. Repository policy、Ubuntu和Windows CI运行链接；
3. 新候选SHA对应的1500条验收报告；
4. Docker真实构建和容器健康冒烟；
5. RC Tag及不可变镜像摘要；
6. 云服务器、域名、TLS、安全组和责任人登记；
7. COS异机恢复和应用回退演练。

## 7. 下一门禁

1. 审查当前5个候选文件；
2. 在批准的发布准备分支形成单一候选提交；
3. 以新SHA重跑384项测试和1500条联合验收；
4. 推送并取得双平台CI证据；
5. 更新本索引后进行BASE-07发布评审。

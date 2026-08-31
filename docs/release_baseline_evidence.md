# 发布基线证据索引

## 1. 当前判定

| 项目 | 内容 |
| --- | --- |
| 核验日期 | 2026-08-31 |
| 发布候选代码SHA | `72653d96d0f8728736d1ae9baf3274897fed3f63` |
| 候选分支 | `release/baseline-convergence` |
| 当前候选状态 | Go |
| 原因 | 本地门禁、Repository policy、Ubuntu和Windows CI全部通过 |
| 正式候选报告 | 已生成并校验 |

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

候选SHA正式运行：

```text
代码SHA：72653d96d0f8728736d1ae9baf3274897fed3f63
测试数：384
结果：通过
耗时：405.486秒
污染检查：通过
```

候选在独立临时SQLite数据库完成空库迁移和全量回归，仓库工作树测试后无未授权产物。

## 4. 联合验收证据

### 4.1 正式候选报告

| 项目 | 内容 |
| --- | --- |
| 报告Git SHA | `72653d96d0f8728736d1ae9baf3274897fed3f63` |
| 固定种子 | `20260822` |
| 学生数 | 1500 |
| 支部数 | 9 |
| 首批 | 1500行成功，创建1500名学生和4500条思想汇报 |
| 第二批 | 1500行成功，更新1500名学生和4500条思想汇报 |
| 回滚后 | 1500名学生、1500条申请、1500条汇总、4500条有效思想汇报 |
| 重启复查 | 通过 |
| 总耗时 | 89.669秒 |
| 报告SHA-256 | `B9CA1DC24470B5C6C99D17227AF3A080047105E506E423C7D98366CFD91059D3` |

报告位于本地Git忽略目录：

```text
artifacts/acceptance/run-1500-72653d9-20260831/acceptance_report.json
```

该报告的`git_sha`与发布候选完全一致，使用固定学生规模和固定种子完成完整业务链路及
新进程重启复查。

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

基线远端证据：

- PR：`https://github.com/ICEXUAN-2707/party-building-archive-system/pull/34`；
- CI运行：`https://github.com/ICEXUAN-2707/party-building-archive-system/actions/runs/33357654268`；
- Repository policy：通过；
- Django tests（Ubuntu）：通过；
- Django tests（Windows）：通过。

以下生产证据尚未取得：

1. Docker真实构建和容器健康冒烟；
2. RC Tag及不可变镜像摘要；
3. 云服务器、域名、TLS、安全组和责任人登记；
4. COS异机恢复和应用回退演练。

## 7. 下一门禁

1. 审核并合并PR #34到`develop`；
2. 按`docs/sprint/deployment_release_engineering_plan.md`进入DEP-08；
3. DEP-08通过后依次执行DEP-09和DEP-10；
4. DEP-10通过前不创建正式Tag、不部署生产、不导入真实数据。

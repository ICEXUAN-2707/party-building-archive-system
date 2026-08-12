# Sprint 2 CI 数据库自动清理修复记录

## 修复日期

2026-08-11

## 修复目标

将 CI 数据库生命周期从依赖 GitHub 托管运行器回收，调整为工作流主动清理并验证。

## 实现内容

- 迁移前清理 `RUNNER_TEMP` 中可能遗留的 CI 数据库。
- 测试或迁移普通失败后，通过 `always()` 再次执行清理。
- 清理范围仅包含 `ci.sqlite3`、`test_ci.sqlite3` 及其 journal、WAL、SHM 文件。
- 清理脚本验证 `DJANGO_SQLITE_PATH` 必须严格位于 `RUNNER_TEMP`，且文件名为 `ci.sqlite3`。
- 污染守卫支持通过 `--temp-dir` 检查 CI 临时目录残留。
- 清理结束后，由独立步骤验证仓库目录和临时目录均无测试污染。

## 本地验证范围

- 固定 CI 数据库文件清理。
- SQLite journal、WAL、SHM 伴生文件清理。
- 无关数据库文件保留。
- 越界数据库路径拒绝。
- 非预期数据库文件名拒绝。
- CI 临时目录残留检测。

Ubuntu、Windows 远端结果需在候选提交触发 GitHub Actions 后补充，不能以本地结果替代。

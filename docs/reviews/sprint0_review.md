# Sprint 0 Review记录

## 1. 审查范围

本次 Review 覆盖 Sprint 0 项目骨架阶段交付物：

* Django 项目配置；
* 五个业务 App 骨架；
* 冻结核心模型和初始迁移；
* 九个党支部初始化命令；
* Django Admin 基础配置；
* 公共模板和占位页面；
* 虚构测试数据命令；
* README；
* 基础测试；
* Sprint 0 文档基线。

本次 Review 不包含学生正式登录、Excel 解析、正式导入、回滚、完整审计日志或正式 Docker 部署。

---

## 2. 当前分支

```text
feature/project-foundation
```

该分支为 Sprint 0 项目骨架正式开发分支。

---

## 3. 检查命令

本次实际执行了以下命令：

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test
```

---

## 4. 检查结果

```text
manage.py check:
System check identified no issues (0 silenced).

manage.py makemigrations --check:
No changes detected.

manage.py migrate:
No migrations to apply.

manage.py test:
Found 12 test(s).
Ran 12 tests in 0.401s.
OK.
```

结论：Sprint 0 当前代码可运行，迁移无遗漏，基础测试通过。

---

## 5. 本轮修复事项

本轮完成以下 Sprint 0 基线修正：

1. 新增 `docs/01_scope_freeze.md`，明确 Sprint 0 允许范围、禁止范围、冻结模型、冻结枚举、分支名称和变更审批规则。
2. 将 Git 协作规范统一到 `docs/02_git_workflow.md`。
3. 删除重复旧 Git 规范文件。
4. 将项目骨架正式开发分支统一为 `feature/project-foundation`。
5. 清除文档中的旧项目骨架分支名。
6. 在 `docs/spec.md` 中明确学号全局唯一、学号不是数据库主键、登录使用姓名和学号联合校验、同一学号不同姓名视为数据冲突。
7. 补充 README 中仓库地址占位符 `<YOUR_REPOSITORY_URL>` 及替换说明。
8. 在 `AGENTS.md` 中补充 Git 协作规范文档引用和 Sprint 0 正式开发分支。

---

## 6. 遗留风险

1. 当前未验证远程仓库权限，后续推送或创建 PR 可能受 GitHub 认证影响。
2. `develop` 分支需要项目负责人确认远程是否已建立并设置保护规则。
3. Sprint 1 开始前，应确认真实或脱敏 Excel 样例是否可用于后续解析测试。
4. 当前仍处于骨架阶段，学生登录、管理员查询、Excel 导入和回滚均未进入正式实现。

---

## 7. 是否允许合入develop

建议允许创建：

```text
feature/project-foundation -> develop
```

的 Pull Request。

合入前建议项目负责人再次确认：

* 当前分支只包含 Sprint 0 范围内改动；
* 未提交敏感数据；
* GitHub 远程权限可用；
* `develop` 分支作为团队集成分支已准备好。

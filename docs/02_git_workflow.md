# Git 工作流规范

本文为本项目唯一正式 Git 协作规范文件。

## 1. 分支模型

```text
main
develop
feature/xxx
```

分支含义：

| 分支 | 用途 |
| --- | --- |
| `main` | 正式稳定版本 |
| `develop` | 集成测试版本 |
| `feature/xxx` | 功能开发分支 |

Sprint 0 项目骨架正式开发分支固定为：

```text
feature/project-foundation
```

后续功能分支示例：

```text
feature/student-auth
feature/student-profile
feature/admin-query
feature/excel-parser
feature/excel-import
feature/docker
```

---

## 2. 禁止事项

禁止：

* 直接向 `main` 推送代码；
* 直接在 `develop` 上开发业务代码；
* 执行 `git push --force`；
* 将 `.env`、`db.sqlite3`、真实 Excel、真实学生数据、上传文件、虚拟环境目录、缓存文件提交到仓库；
* 未运行测试就发起合并。

---

## 3. 开发流程

从 `develop` 创建功能分支：

```bash
git checkout develop
git pull origin develop
git checkout -b feature/student-auth
```

开发完成后查看状态：

```bash
git status
```

按任务范围精确暂存文件：

```bash
git add path/to/file
```

提交：

```bash
git commit -m "feat(student-auth): 实现学生登录入口"
```

推送到远程功能分支：

```bash
git push origin feature/student-auth
```

在 GitHub 创建 PR：

```text
feature/student-auth -> develop
```

PR 必须经过 Review 和测试后才能合并。

---

## 4. Sprint 0 基线流程

Sprint 0 只允许在 `feature/project-foundation` 上完成项目骨架相关工作。

合入 `develop` 前必须满足：

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
python manage.py test
```

同时确认：

* 核心模型与 `docs/spec.md` 一致；
* 九个党支部初始化命令幂等；
* README 可指导新成员从零启动；
* 未提交敏感数据；
* 未提前实现后续业务功能。

---

## 5. Commit 格式

推荐格式：

```text
type(scope): message
```

常用类型：

| 类型 | 含义 |
| --- | --- |
| `feat` | 新增功能 |
| `fix` | 修复问题 |
| `docs` | 文档 |
| `test` | 测试 |
| `refactor` | 重构 |
| `chore` | 工程配置或杂项 |

示例：

```bash
git commit -m "docs: 补充Sprint0范围冻结说明"
git commit -m "feat(imports): 添加导入批次模型"
git commit -m "test(students): 覆盖党支部初始化幂等性"
```

---

## 6. Pull Request 检查项

PR 发起前，开发者必须确认：

* 只修改本任务范围内文件；
* 未引入冻结技术栈外的新依赖；
* 未修改 `docs/spec.md` 中冻结规则，除非该任务明确要求；
* 已运行相关测试；
* 已补充 Module Notes；
* AI 生成代码已经人工审查。

PR Review 关注：

* 是否符合 `docs/spec.md` 和 `AGENTS.md`；
* 是否存在权限绕过；
* 是否影响其他模块；
* 是否缺少测试；
* 是否存在敏感数据或真实学生数据。

---

## 7. 冲突处理

同步 `develop`：

```bash
git checkout develop
git pull origin develop
```

回到功能分支并合并：

```bash
git checkout feature/student-auth
git merge develop
```

解决冲突后：

```bash
git add path/to/resolved_file
git commit -m "fix: 解决develop合并冲突"
```

不得用 `git reset --hard` 或强推覆盖团队成员工作，除非项目负责人明确批准。

---

## 8. 常用命令速查

| 命令 | 作用 |
| --- | --- |
| `git status` | 查看工作区状态 |
| `git branch` | 查看本地分支 |
| `git branch -r` | 查看远程分支 |
| `git checkout -b feature/name` | 创建并切换功能分支 |
| `git add path/to/file` | 精确暂存文件 |
| `git commit -m "message"` | 提交暂存内容 |
| `git push origin feature/name` | 推送功能分支 |
| `git log --oneline -10` | 查看最近提交 |

---

## 9. Git 基本原理简述

Git 每次提交记录的是项目目录快照，而不是简单的代码差异。

分支本质上是指向某个提交的轻量指针。功能分支用于隔离开发工作，PR 用于把经过审查和测试的快照合入 `develop`。

# Sprint 0 范围冻结说明

## 1. 适用范围

本文用于冻结“学院学生材料信息查询系统”Sprint 0 项目骨架阶段的实现边界。

Sprint 0 的正式开发分支为：

```text
feature/project-foundation
```

本文只解释 `docs/spec.md` 和 `AGENTS.md` 已有规则，不新增业务规则。

---

## 2. Sprint 0 允许实现内容

Sprint 0 只允许完成项目骨架和协作基础，包括：

* Django 项目初始化；
* `accounts`、`students`、`materials`、`imports`、`audit` 五个 App 初始化；
* 冻结核心数据模型；
* 初始数据库迁移；
* 九个党支部幂等初始化命令；
* 管理员用户、角色和 Django Admin 基础配置；
* 公共模板和占位页面；
* 虚构测试数据命令；
* README 和基础开发文档；
* 环境变量配置示例；
* 基础测试。

---

## 3. Sprint 0 禁止提前实现内容

Sprint 0 不得完整实现后续业务功能，包括：

* 学生姓名学号正式登录；
* 登录失败次数限制；
* 学生个人信息完整展示；
* 管理员完整查询筛选；
* Excel 解析；
* Excel 正式导入；
* 导入预览业务；
* 最近一次成功导入回滚；
* 完整审计日志业务；
* 正式 Docker、Nginx 或生产部署。

如确需为后续功能保留入口，只允许使用占位页面、占位 URL 或 TODO。

---

## 4. 冻结模型

Sprint 0 必须保留以下业务模型命名：

```text
PartyBranch
Student
ApplicationRecord
IdeologicalReportSummary
IdeologicalReport
ImportBatch
ImportErrorRecord
ImportWarningRecord
OperationLog
```

管理员用户模型采用 `AdminUser`。

不得创建含义重复的模型，例如 `Branch`、`StudentProfile`、`ReportSubmission`、`ExcelBatch`、`ImportError`。

---

## 5. 冻结枚举

管理员角色：

```text
viewer_admin
data_admin
```

发展阶段：

```text
ACTIVIST
PROBATIONARY
FULL_MEMBER
```

导入批次状态：

```text
previewed
success
failed
rolled_back
```

学生状态：

```text
active
inactive
```

---

## 6. 学号唯一规则

Sprint 0 冻结以下学生身份规则：

* 学号在系统内全局唯一；
* 学号不作为数据库主键；
* 数据库仍使用自动生成的 `id`；
* 学生登录使用姓名和学号联合校验；
* 同一学号对应不同姓名视为数据冲突。

当前 `Student.student_number` 使用数据库唯一约束，符合该规则。

---

## 7. 变更审批规则

以下变更必须先更新 `docs/spec.md` 并由项目负责人确认：

* 修改冻结模型、字段或枚举；
* 修改学生身份唯一性规则；
* 修改权限边界；
* 修改 Excel 解析、导入或回滚规则；
* 引入新技术栈；
* 提前实现 Sprint 0 禁止范围内的正式业务功能。

如发现文档之间存在冲突，应停止相关实现，明确指出冲突位置，给出可选方案，并等待项目负责人决策。

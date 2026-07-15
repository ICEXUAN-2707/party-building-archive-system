# AGENTS.md

## 1. 项目简介

本项目为“学院学生材料信息查询系统”。

项目面向学院内部学生和管理员，核心功能包括：

* 学生使用姓名和学号登录；
* 学生查询本人党务材料信息；
* 管理员查询全部学生；
* 数据管理员上传并预览Excel；
* 跳过错误数据并导入有效记录；
* 保存原始Excel；
* 回滚最近一次成功导入。

项目完整业务规则见：

```text
docs/spec.md
```

在修改代码前，必须先阅读该文件。

Git协作规范见：

```text
docs/02_git_workflow.md
```

---

## 2. 当前开发阶段

当前处于：

```text
项目骨架阶段
```

本阶段目标是建立可运行、可测试、适合7人协作开发的Django项目基础。

本阶段不是完整产品开发阶段。

当前项目骨架正式开发分支为：

```text
feature/project-foundation
```

当前应完成：

* Django项目初始化；
* Django App初始化；
* 核心数据模型；
* 数据库迁移；
* 九个党支部初始化机制；
* 管理员角色基础；
* 公共模板；
* 占位页面；
* 测试数据机制；
* README；
* 基础测试；
* 环境变量配置。

当前不得完整实现：

* 学生姓名学号登录业务；
* 登录失败次数限制；
* 学生个人信息完整展示；
* 管理员完整查询筛选；
* Excel解析；
* Excel正式导入；
* 导入预览；
* 回滚业务；
* 完整审计日志；
* 复杂页面动画或视觉精修；
* 正式Docker部署。

这些功能只允许建立必要接口、占位页面或TODO。

---

## 3. 冻结技术栈

必须使用：

* Python 3.12
* Django 5.x稳定版本
* Django Template
* Bootstrap 5
* openpyxl
* SQLite
* Git与GitHub

正式部署方向为：

```text
Docker容器化 + 校园内网单机部署
```

当前骨架阶段只需为未来Docker部署保留良好结构，不要求完成正式生产部署。

禁止擅自引入：

* Flask
* FastAPI
* Spring Boot
* Vue
* React
* Redis
* Celery
* 微服务
* Kubernetes
* MongoDB
* 其他ORM
* 前后端分离架构

禁止擅自升级Python或Django主版本。

---

## 4. Django App划分

项目应包含以下App：

```text
accounts
students
materials
imports
audit
```

职责如下。

### accounts

* 学生登录接口基础；
* 管理员认证基础；
* Session基础；
* 管理员角色与权限基础。

### students

* 党支部；
* 学生主数据；
* 发展阶段；
* 学生列表和详情接口基础。

### materials

* 申请入党记录；
* 思想汇报汇总；
* 思想汇报明细。

### imports

* 导入批次；
* 导入错误；
* 导入警告；
* Excel上传和解析接口占位。

### audit

* 管理员操作日志。

不得在多个App中重复建立含义相同的模型。

---

## 5. 冻结模型命名

必须使用以下业务模型名称：

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

管理员用户优先采用Django自定义用户模型，并根据项目实现选择清晰名称。

禁止自行创建含义重复的模型，例如：

```text
Branch
StudentProfile
ReportSubmission
ExcelBatch
ImportError
```

`ImportErrorRecord`不得命名为`ImportError`，避免与Python内置异常混淆。

---

## 6. 核心模型字段

### PartyBranch

```text
id
name
code
is_active
created_at
updated_at
```

### Student

```text
id
name
student_number
branch
development_stage
position
status
source_import_batch
created_at
updated_at
```

### ApplicationRecord

```text
id
student
applied_at
source_import_batch
created_at
updated_at
```

### IdeologicalReportSummary

```text
id
student
reported_total_count
calculated_date_count
source_import_batch
created_at
updated_at
```

### IdeologicalReport

```text
id
student
sequence_number
submitted_at
source_column_name
import_batch
is_active
created_at
```

### ImportBatch

至少包含：

```text
id
batch_label
original_filename
stored_file
file_hash
imported_by
imported_at
status
total_sheets
success_sheets
failed_sheets
total_rows
success_rows
skipped_rows
warning_rows
created_students
updated_students
created_reports
updated_applications
count_mismatch_rows
unknown_branch_rows
invalid_stage_rows
column_shift_rows
rolled_back_at
rolled_back_by
```

### ImportErrorRecord

至少包含：

```text
id
import_batch
sheet_name
excel_row_number
student_name
student_number
field_name
error_code
error_message
created_at
```

### ImportWarningRecord

至少包含：

```text
id
import_batch
sheet_name
excel_row_number
student_name
student_number
warning_code
warning_message
source_value
parsed_value
created_at
```

### OperationLog

至少包含：

```text
id
operator
operator_role
action
target_type
target_id
description
ip_address
created_at
```

如发现模型之间存在循环依赖，应先说明问题和解决方案，不得直接删除冻结字段。

---

## 7. 冻结枚举

### 管理员角色

```text
viewer_admin
data_admin
```

不得创建同义角色。

### 发展阶段

```text
ACTIVIST
PROBATIONARY
FULL_MEMBER
```

对应：

```text
ACTIVIST       入党积极分子
PROBATIONARY   中共预备党员
FULL_MEMBER    正式党员
```

### 导入批次状态

```text
previewed
success
failed
rolled_back
```

### 学生状态

第一版至少支持：

```text
active
inactive
```

Excel中缺少某名学生时，不自动将其改为`inactive`。

---

## 8. 九个党支部

必须预置：

```text
MINGLI   明理党支部
DELI     德理党支部
WEILI    惟理党支部
QIULI    求理党支部
ZHILI    知理党支部
ZHAOLI   昭理党支部
XUELI    学理党支部
BOLI     博理党支部
YILI     艺理党支部
```

应提供幂等的初始化机制，例如：

```bash
python manage.py initialize_branches
```

重复执行不得创建重复数据。

---

## 9. Excel业务约束

Excel结构：

* 一个文件包含多个工作表；
* 每个正式工作表原则上对应一个党支部；
* 前两行为表头；
* 第一行为字段分组；
* 第二行为正式字段名；
* 第三行起为学生数据；
* 思想汇报列命名为“第X次思想汇报”；
* 标准日期格式为`YYYY/MM/DD`；
* 真实数据约1500条。

当前骨架阶段不得完整实现解析器，但模型和接口必须支持以上结构。

思想汇报列数量不得固定为20。

不得为每次思想汇报创建固定数据库字段，例如：

```text
report_1_date
report_2_date
report_3_date
```

---

## 10. 关键业务关系

模型关系应表达：

```text
PartyBranch 1 ── N Student

Student 1 ── 1 ApplicationRecord

Student 1 ── 1 IdeologicalReportSummary

Student 1 ── N IdeologicalReport
```

思想汇报总篇数和思想汇报明细必须分开保存。

### Excel填报总篇数

保存为：

```text
IdeologicalReportSummary.reported_total_count
```

允许为空。

### 系统计算日期数

保存为：

```text
IdeologicalReportSummary.calculated_date_count
```

### 每次提交时间

保存为多条：

```text
IdeologicalReport
```

并包含：

```text
sequence_number
submitted_at
```

不得使用系统计算值覆盖Excel原始填报值。

---

## 11. Session和权限接口

学生登录成功后的Session键冻结为：

```text
student_id
```

值为：

```text
Student数据库主键
```

学生个人页面必须从Session读取学生身份，不得允许前端自由传入目标学生ID。

权限必须由后端验证，不能只隐藏按钮或导航。

当前骨架阶段可以建立装饰器、Mixin或接口占位，但不要求完成全部业务。

---

## 12. 项目目录

推荐结构：

```text
project_root/
├── AGENTS.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── manage.py
├── config/
├── apps/
│   ├── accounts/
│   ├── students/
│   ├── materials/
│   ├── imports/
│   └── audit/
├── templates/
├── static/
├── media/
│   └── imports/
├── tests/
├── docs/
└── scripts/
```

如Django初始化方式导致目录略有差异，应保持业务模块和职责一致。

---

## 13. 环境和配置要求

所有敏感和环境相关配置必须通过环境变量管理。

项目必须提供：

```text
.env.example
```

不得提交：

```text
.env
db.sqlite3
真实Excel
真实学生数据
真实密码
虚拟环境目录
__pycache__
上传文件
数据库备份
```

`.gitignore`必须覆盖以上文件。

不得依赖开发者电脑上的绝对路径。

---

## 14. 页面要求

当前只建立基础页面或占位页面：

* 首页；
* 学生登录页；
* 管理员登录页；
* 学生个人信息占位页；
* 管理员学生列表占位页；
* 管理员学生详情占位页；
* Excel上传占位页；
* 导入预览占位页；
* 导入历史占位页；
* 403页面；
* 404页面；
* 500页面。

页面使用：

```text
Django Template + Bootstrap 5
```

设计方向：

* 简约；
* 清晰；
* 留白充分；
* 高校年轻感；
* 搜索与查询优先；
* 不引入复杂动画。

骨架阶段不进行视觉精修。

---

## 15. 测试要求

完成骨架后必须运行：

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
python manage.py test
```

至少建立测试验证：

1. Django配置检查通过；
2. 首页可以访问；
3. 核心模型可以创建；
4. 九个支部初始化成功；
5. 初始化命令重复执行不会产生重复数据；
6. 发展阶段枚举有效；
7. 管理员角色枚举有效；
8. 思想汇报汇总与明细关系有效；
9. 占位页面URL可以解析。

测试不得只断言`True`。

---

## 16. README要求

README至少说明Windows环境下：

1. 安装Python；
2. 克隆仓库；
3. 创建虚拟环境；
4. 激活虚拟环境；
5. 安装依赖；
6. 创建`.env`；
7. 执行迁移；
8. 初始化九个党支部；
9. 创建管理员；
10. 生成测试数据；
11. 启动项目；
12. 运行测试。

所有命令必须能够直接复制执行，或明确说明需要替换的参数。

---

## 17. 编码原则

* 优先清晰和可读性；
* 避免过度抽象；
* 避免一次生成过多无关功能；
* 核心业务规则集中定义；
* 使用Django ORM；
* 使用类型提示；
* 对关键业务逻辑添加简短中文注释；
* 不重复定义枚举；
* 不静默吞掉异常；
* 不在Model的`save()`中隐藏复杂导入逻辑；
* 文件解析、业务校验和数据库写入应分离。

---

## 18. 修改限制

未经明确指令不得：

* 修改`docs/spec.md`；
* 更换技术栈；
* 删除冻结模型；
* 重命名冻结模型或字段；
* 新增正式业务功能；
* 完整实现Excel导入；
* 完整实现回滚；
* 添加真实数据；
* 修改Git分支；
* 执行`git push --force`；
* 删除现有迁移文件；
* 重置整个仓库；
* 修改任务范围外的文件。

如发现Spec存在冲突：

1. 停止相关实现；
2. 明确指出冲突位置；
3. 给出可选方案；
4. 等待项目负责人决策；
5. 不自行选择并修改业务规则。

---

## 19. Codex工作方式

执行任务时必须：

1. 先阅读`docs/spec.md`和本文件；
2. 检查当前仓库结构；
3. 检查当前Git状态；
4. 输出实施计划；
5. 列出计划新增或修改的文件；
6. 小步实施；
7. 每个阶段运行检查；
8. 不修改任务范围外的文件；
9. 最后运行完整测试；
10. 汇总改动、测试结果和未完成事项。

发现已有代码时，应先理解和复用，不能无理由重新生成整个项目。

---

## 20. 完成定义

项目骨架只有在满足以下条件后才算完成：

* 新成员可以按照README从零启动项目；
* 项目不依赖个人电脑绝对路径；
* 数据迁移成功；
* 九个支部可以初始化；
* 占位页面可以访问；
* 核心模型可创建；
* Django Admin可查看核心模型；
* 基础测试全部通过；
* 项目没有提交敏感数据；
* 未提前完整实现后续成员负责的业务功能。

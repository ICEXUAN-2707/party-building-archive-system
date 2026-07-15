# 学院学生材料信息查询系统

本项目用于学院内部学生党务材料信息查询。当前处于项目骨架阶段，只提供 Django 项目结构、核心模型、初始化命令、占位页面和基础测试，不包含正式 Excel 导入或完整查询业务。

## 技术栈

- Python 3.12
- Django 5.x
- Django Template
- Bootstrap 5
- openpyxl
- SQLite

## 目录结构

```text
config/                 Django 项目配置
apps/accounts/          管理员用户、角色和登录入口占位
apps/students/          党支部、学生主数据、初始化命令
apps/materials/         申请入党记录、思想汇报汇总与明细
apps/imports/           导入批次、错误、警告和导入页面占位
apps/audit/             操作日志
templates/              公共模板和占位页面
static/                 静态文件
media/imports/          原始 Excel 保存目录
tests/                  基础测试
docs/                   需求规格
scripts/                后续脚本目录
```

## Windows 启动步骤

1. 安装 Python 3.12，并确认命令可用：

```powershell
python --version
```

2. 克隆仓库：

```powershell
git clone <仓库地址>
cd party-building-archive-system
```

3. 创建虚拟环境：

```powershell
python -m venv .venv
```

4. 激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

5. 安装依赖：

```powershell
python -m pip install -r requirements.txt
```

6. 创建 `.env`：

```powershell
Copy-Item .env.example .env
```

然后按需修改 `.env` 中的 `DJANGO_SECRET_KEY`、`DJANGO_DEBUG`、`DJANGO_ALLOWED_HOSTS`。

7. 执行迁移：

```powershell
python manage.py migrate
```

8. 初始化九个党支部：

```powershell
python manage.py initialize_branches
```

9. 创建超级管理员：

```powershell
python manage.py createsuperuser
```

10. 生成虚构测试数据：

```powershell
python manage.py seed_demo_data
```

11. 启动项目：

```powershell
python manage.py runserver
```

12. 访问地址：

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/admin/
```

13. 运行测试：

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

## 管理命令

```powershell
python manage.py initialize_branches
python manage.py seed_demo_data
```

`initialize_branches` 可重复执行，不会创建重复支部。`seed_demo_data` 只生成虚构姓名和虚构学号，可重复执行。

## 当前已实现

- Django 5 项目骨架
- 五个业务 App
- 自定义管理员用户 `AdminUser`
- 冻结核心模型与枚举
- Django Admin 基础配置
- 九个党支部幂等初始化
- 虚构测试数据命令
- Bootstrap 公共模板和占位页面
- 环境变量配置示例
- 基础测试

## 当前未实现

- 学生姓名学号正式登录
- 登录失败次数限制
- 学生个人信息完整展示
- 管理员完整查询筛选
- Excel 解析、预览、正式导入
- 错误数据跳过导入
- 最近一次成功导入回滚
- 完整审计日志业务
- 正式 Docker、Nginx 和生产部署

## 常见问题

如果 PowerShell 禁止激活虚拟环境，可临时允许当前会话执行脚本：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

如果提示 Django 不存在，请确认已激活虚拟环境并执行：

```powershell
python -m pip install -r requirements.txt
```

## Git 协作提醒

- 不提交 `.env`、`db.sqlite3`、真实 Excel、真实学生数据、上传文件、虚拟环境目录。
- 当前分支用于项目骨架开发。
- 提交前运行 `python manage.py test`。

## 未来 Docker 方向

正式部署方向为 Docker 容器化加校园内网单机部署。当前阶段只保留目录、环境变量和媒体文件位置，暂不提供生产 Dockerfile、Nginx 或备份恢复脚本。

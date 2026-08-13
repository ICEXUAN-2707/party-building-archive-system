# “智赋党建，数启新程”学院学生材料信息查询系统

本项目是基于 Django 5 的学院内部学生党务材料查询与 Excel 数据管理系统。当前已完成工程基础、学生认证、学生个人档案和 Excel 纯解析器；管理员查询、Excel 上传预览、正式导入与最近批次回滚正在开发。

当前进度、稳定接口、开发中模块和风险以 [当前项目状态](docs/current_project_status.md) 为唯一入口。冻结业务规则见 [Spec](docs/spec.md)，协作规则见 [Git 工作流](docs/02_git_workflow.md)。

## 当前能力

- Django 5.2.4 单体应用与五个业务 App；
- 冻结核心模型、迁移、九支部幂等初始化；
- 姓名与学号联合登录、严格 `student_id` Session 契约；
- 学生本人党务档案只读展示；
- `parse_workbook(Path) -> ParseResult` 多工作表 Excel 纯解析；
- Windows/Ubuntu CI、迁移检查和数据库污染防护；
- 当前 `develop@42abdf7` 本地全量测试 171 项通过。

## 开发中

- 管理员认证、权限、筛选、详情和审计；
- Excel 上传、服务端预览快照、导入历史和受控下载；
- 正式事务导入；
- 服务端 JSON 业务快照、最近成功批次回滚和 SQLite 备份。

## 尚未进入本阶段

- Docker、Nginx 和正式校园内网部署；
- 任意历史批次或部分学生回滚；
- 全量业务版本化和数据库快照模型；
- 多 Web 实例及高并发架构。

## 技术栈

- Python 3.12
- Django 5.2.4
- Django Template + Bootstrap 5
- openpyxl 3.1.5
- SQLite

## Windows 启动

```powershell
git clone https://github.com/ICEXUAN-2707/party-building-archive-system.git
cd party-building-archive-system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py initialize_branches
python manage.py createsuperuser
python manage.py seed_demo_data
python manage.py runserver
```

访问：

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/admin/
```

## 验证

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
git diff --check
```

## 数据安全

不得提交 `.env`、`db.sqlite3`、真实 Excel、真实学生数据、上传文件、备份文件或虚拟环境。正式导入与回滚的现行方案见 [第一版收敛作业方案](docs/sprint/mvp_convergence_governance_plan.md)。

## Docker 方向

正式部署方向仍为 Docker 容器化加校园内网单机部署；当前阶段先完成查询与 Excel 数据闭环，尚未提供生产 Dockerfile、Nginx 或正式部署手册。

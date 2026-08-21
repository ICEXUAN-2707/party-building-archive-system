# “智赋党建，数启新程”学院学生材料信息查询系统

本项目是基于 Django 5 的学院内部学生党务材料查询与 Excel 数据管理系统。当前已完成学生和管理员查询、Excel上传预览、正式事务导入、最近成功批次回滚及受控SQLite灾难恢复。

当前进度、稳定接口、开发中模块和风险以 [当前项目状态](docs/current_project_status.md) 为唯一入口。冻结业务规则见 [Spec](docs/spec.md)，协作规则见 [Git 工作流](docs/02_git_workflow.md)。

## 当前能力

- Django 5.2.4 单体应用与五个业务 App；
- 冻结核心模型、迁移、九支部幂等初始化；
- 姓名与学号联合登录、严格 `student_id` Session 契约；
- 学生本人党务档案只读展示；
- `parse_workbook(Path) -> ParseResult` 多工作表 Excel 纯解析；
- 管理员认证、统一权限、学生筛选分页、详情和操作审计；
- Windows/Ubuntu CI、迁移检查和数据库污染防护；
- 服务端Excel证据链、事务导入、HTTP 409幂等并发保护和最近批次回滚；
- SQLite导入前一致性备份及停机灾难恢复命令；
- 确定性约1500条合成Excel联合验收工具。

## 上线收尾中

- 约1500条同SHA合成数据联合验收；
- Docker、生产WSGI、持久化目录和干净环境部署演练。

## 非目标

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

不得提交 `.env`、`db.sqlite3`、真实 Excel、真实学生数据、上传文件、备份文件或虚拟环境。正式导入与回滚的现行方案见 [第一版收敛作业方案](docs/sprint/mvp_convergence_governance_plan.md)，合成验收见 [Excel联合验收指南](docs/excel_acceptance_guide.md)，备份恢复见 [SQLite备份与灾难恢复指南](docs/backup_restore_guide.md)。

## Docker 方向

正式部署方向仍为 Docker 容器化加校园内网单机部署；Excel闭环完成联合验收后，进入生产Dockerfile、持久化目录和部署手册开发。

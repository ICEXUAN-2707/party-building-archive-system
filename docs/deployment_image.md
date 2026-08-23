# DEP-03 生产Web镜像合同

## 1. 范围

本阶段只交付Django生产Web镜像，不包含Compose、Nginx、证书、健康检查、迁移自动化或备份调度。

## 2. 镜像基线

- 基础镜像：`python:3.12.14-slim-bookworm`；
- WSGI服务：Gunicorn 25.0.0；
- 容器用户：`app`，UID/GID均为`10001`；
- 工作目录：`/app`；
- 应用端口：`8000`，只能由后续Compose内部网络访问；
- 数据目录：`/data/database`、`/data/media`、`/data/static`、`/data/backups`。

镜像不包含`.env`、数据库、Excel、媒体、备份、测试、开发文档、虚拟环境或Git历史。

## 3. 启动合同

入口脚本首先执行：

```text
python manage.py collectstatic --noinput
```

生产配置不完整时，Django配置门禁会在静态收集阶段阻止启动。静态收集成功后，入口进程被替换为Gunicorn。

Gunicorn冻结为单worker，避免部署人员通过环境变量开启多进程并扩大SQLite写入竞争。允许调整：

| 变量 | 默认值 | 范围 |
| --- | ---: | ---: |
| `GUNICORN_THREADS` | 2 | 1—8 |
| `GUNICORN_TIMEOUT` | 60秒 | 30—300秒 |
| `GUNICORN_GRACEFUL_TIMEOUT` | 30秒 | 10—120秒 |

访问日志暂不由Gunicorn输出，避免默认请求行记录查询参数。公网访问日志由DEP-04的Nginx按脱敏格式统一配置。

## 4. 构建与静态检查

具备Docker的Linux环境执行：

```text
docker build --pull --tag party-archive-web:dep03 .
```

构建后必须检查：

1. 容器用户不是root；
2. 镜像中不存在`.env`、SQLite、Excel和媒体文件；
3. 生产变量缺失时容器拒绝启动；
4. 完整生产变量下`collectstatic`成功；
5. Gunicorn只启动一个worker；
6. 容器退出时Gunicorn可以接收并处理终止信号。

当前开发机没有Docker CLI，因此本阶段只能完成合同测试和代码审查，不能把本地镜像构建标记为通过。
真实构建验证必须在具备Docker的CI或云服务器脱敏环境完成后，才允许合并或继续DEP-04。

## 5. 明确不执行的启动操作

入口脚本不会自动执行：

- 数据库迁移；
- 九支部初始化；
- 管理员创建；
- 测试数据导入；
- 数据库恢复；
- 备份删除或轮换。

这些操作必须通过后续部署流程显式执行并保留结果。

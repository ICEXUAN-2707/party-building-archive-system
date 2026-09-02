# 生产部署指南（DEP-09）

本指南面向 Ubuntu 24.04 LTS、x86_64、单机 Docker Compose 部署。云服务器尚未审批时，只执行本地或受限环境验证，不导入真实数据、不开放公网。本指南中的 `<...>` 必须替换，真实密钥、IP、联系人和证书不得提交仓库。

## 1. 上线前门禁

- 固定经审批的 Git Tag、提交 SHA、Web 镜像摘要和 Nginx 镜像版本，禁止部署 `develop`、浮动分支或仅用 `latest`。
- 推荐最低 2 vCPU、4 GiB 内存、30 GiB 可用磁盘；生产采购基线以资产登记为准。
- 只允许安全组和宿主机防火墙开放 80/443；SSH 仅允许登记来源；不得开放 8000。
- 准备受信任 TLS 证书、生产域名、DNS、COS 和五类责任人。未准备好时只能脱敏演练。
- 在变更单中记录旧版本、新版本、窗口、操作人、审核人、备份标识和回退点。

在目标主机的固定候选代码目录运行只读预检：

```bash
bash scripts/validate_production_host.sh
```

预检失败项必须处理；警告项必须登记解释。脚本不会安装软件或修改主机。

## 2. 初始化目录与配置

```bash
sudo bash scripts/initialize_production_host.sh
sudo install -d -m 0750 /srv/party-archive/app
```

将固定候选代码放入 `/srv/party-archive/app`，核对：

```bash
cd /srv/party-archive/app
git status --short
git rev-parse HEAD
git tag --points-at HEAD
```

创建非敏感 Compose 参数和生产配置：

```bash
cp deploy/compose.env.example deploy/compose.env
sudo cp .env.production.example /srv/party-archive/secrets/.env.production
sudo chmod 600 /srv/party-archive/secrets/.env.production
sudoedit /srv/party-archive/secrets/.env.production
```

`WEB_IMAGE`必须是已审核的不可变标签或摘要；替换生产密钥、域名、CSRF 来源及持久化路径。证书文件必须为：

```text
/srv/party-archive/secrets/tls/fullchain.pem
/srv/party-archive/secrets/tls/privkey.pem
```

## 3. 首次启动

```bash
docker compose --env-file deploy/compose.env -f compose.production.yml config --quiet
docker compose --env-file deploy/compose.env -f compose.production.yml up -d
docker compose --env-file deploy/compose.env -f compose.production.yml ps
```

入口脚本负责迁移和静态资源；首次部署还须初始化九个支部并人工创建首个管理员：

```bash
docker compose --env-file deploy/compose.env -f compose.production.yml exec web python manage.py initialize_branches
docker compose --env-file deploy/compose.env -f compose.production.yml exec web python manage.py createsuperuser
```

## 4. 验收

```bash
curl -I http://<正式域名>/
curl --fail https://<正式域名>/nginx-health
curl --fail https://<正式域名>/health/live/
curl --fail https://<正式域名>/health/ready/
docker compose --env-file deploy/compose.env -f compose.production.yml logs --tail 200 web nginx
```

确认 HTTP 跳转 HTTPS、证书受信任、两个容器 healthy、8000 未映射、Bootstrap 静态文件可访问、九个支部存在。只使用合成数据验证登录、查询、导入预览和回滚。

## 5. 停止与交接

正常停止使用：

```bash
docker compose --env-file deploy/compose.env -f compose.production.yml down
```

禁止使用 `docker compose down --volumes`，禁止删除 `/srv/party-archive/data`。交接时记录候选 SHA、镜像摘要、配置键名清单、证书到期日、最近备份、健康状态及未决缺陷，任何记录不得包含秘密值或真实学生资料。

# 生产部署指南（DEP-09）

本指南适用于 Ubuntu 24.04 LTS、x86_64、单机 Docker Compose，以及固定公网 IPv4 + HTTP 的第一版部署。拿到正式服务器前只能在 WorkBuddy 或其他受控环境使用合成数据演练，不得导入真实数据。

## 1. 上线前门禁

- 固定经过审核的 Git SHA、RC Tag、Web 镜像摘要和 Nginx 镜像版本；禁止部署 `develop`、浮动分支或仅使用 `latest`。
- 建议至少 2 vCPU、4 GiB 内存、20 GiB 可用磁盘。
- SSH 只允许登记来源；80 端口只允许校园网、VPN或明确可信来源；不得开放 443、8000和数据库端口。
- 登记固定公网 IPv4、安全组、COS 和项目/运维/数据/安全责任人。
- HTTP 会明文传输会话和业务数据；若无法限制来源，必须暂停上线并升级为 HTTPS 方案。

在目标主机运行只读预检：

```bash
bash scripts/validate_production_host.sh
```

## 2. 初始化与配置

```bash
sudo bash scripts/initialize_production_host.sh
sudo install -d -m 0750 /srv/party-archive/app
cd /srv/party-archive/app
git status --short
git rev-parse HEAD
git tag --points-at HEAD
cp deploy/compose.env.example deploy/compose.env
sudo cp .env.production.example /srv/party-archive/secrets/.env.production
sudo chmod 600 /srv/party-archive/secrets/.env.production
sudoedit /srv/party-archive/secrets/.env.production
```

`WEB_IMAGE`必须使用审核后的不可变标签或摘要。将 `<FIXED_PUBLIC_IPV4>` 替换为服务器固定公网 IPv4，并配置相同 Host 对应的 `http://<FIXED_PUBLIC_IPV4>` CSRF 来源。不得提交环境文件或秘密值。

## 3. 首次启动

```bash
docker compose --env-file deploy/compose.env -f compose.production.yml config --quiet
docker compose --env-file deploy/compose.env -f compose.production.yml up -d
docker compose --env-file deploy/compose.env -f compose.production.yml ps
docker compose --env-file deploy/compose.env -f compose.production.yml exec web python manage.py initialize_branches
docker compose --env-file deploy/compose.env -f compose.production.yml exec web python manage.py createsuperuser
```

## 4. 验收

```bash
curl --fail http://<FIXED_PUBLIC_IPV4>/nginx-health
curl --fail http://<FIXED_PUBLIC_IPV4>/health/live/
curl --fail http://<FIXED_PUBLIC_IPV4>/health/ready/
docker compose --env-file deploy/compose.env -f compose.production.yml logs --tail 200 web nginx
```

确认 Web 与 Nginx 均为 healthy、只有 Nginx 的 80 端口对允许来源开放、8000 未映射、Bootstrap 静态文件可访问、九个支部存在。只用合成数据验证登录、查询、导入、回滚和审计。

## 5. 停止与交接

```bash
docker compose --env-file deploy/compose.env -f compose.production.yml down
```

禁止使用 `docker compose down --volumes`，禁止删除 `/srv/party-archive/data`。交接时记录候选 SHA、镜像摘要、配置键名清单、固定公网 IPv4、访问来源限制、最近备份、健康状态和未决缺陷；记录中不得包含秘密值或真实学生资料。

# DEP-IP-03 生产 Compose、Nginx 与持久化合同

## 1. 范围

本阶段交付阿里云单机 Compose 编排、固定公网 IPv4 的 HTTP 入口和宿主机数据持久化。目标主机为
Ubuntu Server 24.04 LTS、x86_64、最低 2 vCPU/4 GiB，建议 80 GiB SSD。

```text
授权来源 -> 阿里云安全组:80 -> Nginx:80 -> Compose内部网络 -> Django/Gunicorn:8000
```

`8000` 只由 Compose 内部网络暴露，宿主机和阿里云安全组不得开放该端口。Nginx 不直接提供
`/media/`，原始 Excel 和业务文件继续由 Django 权限控制下载。

## 2. 服务器目录

```bash
sudo bash scripts/initialize_production_host.sh
```

业务数据位于 `/srv/party-archive/data/{database,media,static,backups}`。Web 容器使用 UID/GID
`10001`，这些目录必须允许该用户读写。初始化脚本不再创建 TLS 目录，Compose 也不挂载 TLS 文件。

## 3. 配置

```bash
cp deploy/compose.env.example deploy/compose.env
sudo cp .env.production.example /srv/party-archive/secrets/.env.production
sudo chmod 600 /srv/party-archive/secrets/.env.production
```

将示例中的 `203.0.113.10` 替换为服务器实际固定公网 IPv4；该示例地址仅用于文档，不能直接
启动生产环境。两个文件中的 IP 必须一致：

```env
NGINX_SERVER_NAME=<固定公网IPv4>
DJANGO_ALLOWED_HOSTS=<固定公网IPv4>
DJANGO_CSRF_TRUSTED_ORIGINS=http://<固定公网IPv4>
```

同时替换生产密钥和固定镜像标签。真实 IP、密钥和 `.env.production` 不提交 Git。

## 4. 校验与启动

```bash
docker compose --env-file deploy/compose.env -f compose.production.yml config --quiet
docker compose --env-file deploy/compose.env -f compose.production.yml up -d
docker compose --env-file deploy/compose.env -f compose.production.yml ps
docker compose --env-file deploy/compose.env -f compose.production.yml logs --tail 200 web nginx
curl --fail -H "Host: <固定公网IPv4>" http://127.0.0.1/health/ready/
```

外部授权客户端通过 `http://<固定公网IPv4>/` 访问。禁止使用 `docker compose down --volumes`。

## 5. 阿里云网络规则

- TCP 80：优先仅允许学校或使用人员固定公网 IP/CIDR。
- TCP 22：仅允许运维固定公网 IP。
- TCP 443、8000 和数据库端口：不开放。
- 宿主机防火墙不得比安全组更宽。
- 若 80 对全网开放，只能使用脱敏数据演示。

## 6. 验收

1. Compose 配置可解析且不含真实密钥。
2. 只发布 Nginx 80，未发布 443 或 Web 8000。
3. Nginx 不引用 TLS 文件、不执行 HTTPS 跳转。
4. Nginx 向 Django 传递 `X-Forwarded-Proto: http`。
5. SQLite、媒体、静态和备份目录全部持久化。
6. Web 使用 UID 10001、只读根文件系统和最小 capabilities。
7. Web 与 Nginx 均进入 healthy。
8. 重建 Web 容器后脱敏测试数据仍存在。
9. 固定公网 IPv4、CSRF 来源和安全组授权来源已复核。

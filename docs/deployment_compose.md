# DEP-04 生产Compose、Nginx与持久化合同

## 1. 范围和采购基线

本阶段交付单机Compose编排、Nginx HTTPS入口和宿主机数据持久化。
已冻结的目标是腾讯云北京节点轻量应用服务器，x86_64、2 vCPU、4 GiB内存、
单系统盘（建议80 GiB SSD）和Ubuntu Server 24.04 LTS。购买前仍需在腾讯云控制台
确认实例是AMD64、可用于备案、具备公网IPv4、至少5 Mbps带宽并支持快照。

这一规格只运行单Web实例和单Gunicorn worker。数据库、媒体和本机备份位于同一系统盘，
因此DEP-07必须再复制到COS或其他故障域；本机备份和系统盘快照不能代替异机备份。

## 2. 生产结构

```text
公网 80/443
  -> Nginx
  -> Compose内部网络
  -> Django + Gunicorn:8000
  -> /srv/party-archive/data/*
```

`8000`只由Compose内部网络暴露，宿主机和腾讯云防火墙不得开放该端口。
Nginx不直接提供`/media/`，原始Excel和其他业务文件继续由Django权限控制下载。

## 3. 服务器目录

首次部署执行：

```bash
sudo bash scripts/initialize_production_host.sh
```

脚本只创建下列固定目录，不删除或覆盖已有文件：

```text
/srv/party-archive/
  app/
  data/database/
  data/media/
  data/static/
  data/backups/
  data/logs/
  secrets/
  secrets/tls/
```

Web容器使用UID/GID `10001`，四个业务数据目录必须允许该用户读写。

## 4. 配置文件

复制Compose非敏感参数：

```bash
cp deploy/compose.env.example deploy/compose.env
```

将`WEB_IMAGE`替换为经评审的版本标签或镜像摘要，并将`NGINX_SERVER_NAME`替换为正式域名。
不得使用浮动开发分支或单独依赖`latest`。Nginx只使用这一审核过的域名生成HTTP到HTTPS的跳转。

创建真实生产配置：

```bash
sudo cp .env.production.example /srv/party-archive/secrets/.env.production
sudo chmod 600 /srv/party-archive/secrets/.env.production
sudoedit /srv/party-archive/secrets/.env.production
```

必须替换密钥、域名和CSRF来源。真实文件不进入Git、聊天、工单或PR。

## 5. TLS证书

Nginx只在下列文件存在时启动：

```text
/srv/party-archive/secrets/tls/fullchain.pem
/srv/party-archive/secrets/tls/privkey.pem
```

正式上线使用正式域名的受信任证书。域名和备案尚未就绪时，只允许使用自签名证书
在负责人IP白名单内进行脱敏演练；浏览器的证书警告不能作为正式验收通过。

## 6. 校验、启动和停止

```bash
docker compose \
  --env-file deploy/compose.env \
  -f compose.production.yml \
  config --quiet

docker compose \
  --env-file deploy/compose.env \
  -f compose.production.yml \
  up -d

docker compose \
  --env-file deploy/compose.env \
  -f compose.production.yml \
  ps

docker compose \
  --env-file deploy/compose.env \
  -f compose.production.yml \
  logs --tail 200 web nginx

docker compose \
  --env-file deploy/compose.env \
  -f compose.production.yml \
  down
```

禁止使用：

```text
docker compose down --volumes
```

本阶段使用宿主机绑定挂载，`down --volumes`通常不会删除绑定目录，但将其列为禁止命令
可以防止未来引入命名卷后形成误删习惯。

## 7. DEP-04验收

1. Compose配置可解析，且不含真实密钥。
2. Web端口`8000`没有映射到宿主机。
3. Nginx将HTTP跳转到HTTPS，并且只通过内部网络访问Web。
4. SQLite、媒体、静态文件和备份目录全部持久化。
5. Web使用UID `10001`，容器只读根文件系统与最小Linux capabilities。
6. 缺少生产配置、持久化目录或TLS证书时拒绝或无法启动，不静默降级。
7. 完整配置下Web和Nginx都进入`healthy`。
8. 重启和重建Web容器后脱敏测试数据仍存在。
9. `docker stop`后Gunicorn正常退出。
10. 磁盘、备案、监控和真实数据门禁进入DEP-06、DEP-07和DEP-10。

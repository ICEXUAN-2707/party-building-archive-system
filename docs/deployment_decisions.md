# DEP-IP-01 阿里云固定公网 IP 部署决策基线

**状态：** 架构已冻结，实际资产值待购买后登记

**决策日期：** 2026-09-03

**适用版本：** Spec V1.4

## 1. 冻结架构

第一版采用阿里云单机、固定公网 IPv4、HTTP、单 Django 实例和 SQLite：

```text
授权用户
  -> 阿里云安全组（80限制授权来源；22限制运维来源）
  -> Nginx容器（HTTP入口、静态文件、请求限制）
  -> Django + Gunicorn容器（单实例、单worker）
  -> SQLite、媒体、静态文件和备份持久化目录
```

冻结决定：

1. 使用阿里云 ECS 或轻量应用服务器，Ubuntu Server 24.04 LTS、x86_64。
2. 最低 2 vCPU、4 GiB 内存、40 GiB 系统盘，建议 80 GiB SSD。
3. 使用 Docker Engine 与 Docker Compose v2，不使用 Kubernetes。
4. 用户只通过 `http://<固定公网IPv4>/` 访问，不配置域名、DNS、TLS 或 443。
5. 公网 IPv4 必须固定；实例地址不稳定时绑定 EIP。
6. Nginx 是唯一公网入口；Django 8000 端口只在 Compose 内部网络暴露。
7. 第一版继续使用 SQLite，只运行一个 Web 实例和一个 Gunicorn worker。
8. 正式数据全部位于 `/srv/party-archive/data` 的宿主机绑定目录。
9. 生产部署只使用已评审 Git tag、固定提交和不可变镜像标签。

## 2. HTTP 风险边界

本项目负责人为降低首版配置难度，明确选择公网 IP + HTTP。HTTP 不提供传输加密，登录凭据、
Session Cookie 和业务响应可能被链路观察者读取，因此必须执行以下补偿控制：

1. 阿里云安全组的 TCP 80 优先只允许学校、负责人或实际使用人员的固定公网 IP/CIDR。
2. TCP 22 只允许登记的运维公网 IP，禁止 `0.0.0.0/0`。
3. 443、8000、数据库端口及其他管理端口不得向公网开放。
4. 同步配置宿主机防火墙，规则不得宽于阿里云安全组。
5. 管理员使用强密码；Session 保持 HttpOnly、SameSite=Lax，并设置合理有效期。
6. Nginx 对登录和上传入口限流，限制请求体和超时。
7. 日志不得记录密码、Cookie、Session、Excel 正文或完整学生资料。
8. 如果 TCP 80 必须向全网开放，只允许脱敏演示，不得导入真实学生数据。

未来若改用 HTTPS，必须升级 Spec 并重新评审 Cookie、CSRF、代理头、证书和监控配置，不得仅开放
443 端口后直接上线。

## 3. 网络与生产配置

| 项目 | 决策 |
| --- | --- |
| 正式地址 | `http://<固定公网IPv4>/` |
| 对公网开放 | TCP 80，来源优先限制为授权 IP/CIDR |
| SSH | TCP 22，仅允许运维固定 IP |
| 不开放 | TCP 443、8000、数据库及其他管理端口 |
| Django Host | `DJANGO_ALLOWED_HOSTS=<固定公网IPv4>` |
| CSRF来源 | `DJANGO_CSRF_TRUSTED_ORIGINS=http://<固定公网IPv4>` |
| Nginx Host | `NGINX_SERVER_NAME=<固定公网IPv4>` |

生产环境必须 `DEBUG=False`，使用至少 50 字符的随机密钥，并显式配置全部持久化路径。生产设置
必须拒绝域名、通配符、本地地址、私网地址、多个 Host 和与 Host 不一致的 CSRF 来源。

## 4. 数据目录

```text
/srv/party-archive/
  app/
  data/database/
  data/media/
  data/static/
  data/backups/
  data/logs/
  secrets/
```

`.env` 权限为 0600，不进入 Git。数据库、媒体和备份不得写入镜像可写层。删除或重建容器后，
正式数据必须保留。

## 5. 备份与发布边界

本阶段不修改现有异机备份实现；腾讯云 COS 到阿里云 OSS 的迁移由后续 DEP-ALI-04 单独完成。
在 OSS 迁移和异机恢复演练通过前，只允许脱敏部署演练，不完成正式数据 Go 决策。

每次发布前保存数据库一致性备份、媒体索引、环境变量键名清单和镜像摘要。至少保留当前版本及
上一个已验证版本。恢复 SQLite 时必须先停止 Web 写入，禁止在线替换数据库。

## 6. 待登记资产

| 资产 | 必填内容 |
| --- | --- |
| 阿里云资源 | ECS/轻量应用服务器、地域、可用区、实例 ID |
| 主机规格 | CPU、内存、磁盘、系统镜像、架构 |
| 公网入口 | 固定公网 IPv4 或 EIP，不写入 Git |
| 网络规则 | 80 与 22 的授权来源、宿主机防火墙 |
| 数据目录 | 默认 `/srv/party-archive` 或批准的替代目录 |
| 异机备份 | 后续 OSS Bucket、地域、版本和生命周期策略 |
| 责任人 | 项目、云资源、应用运维、数据和安全负责人 |

## 7. 本阶段完成判定

1. Spec、决策、配置与测试均使用阿里云固定公网 IPv4 + HTTP。
2. Nginx 只监听并发布 80，且只通过内部网络访问 Web。
3. 443、TLS 文件和 HTTP 到 HTTPS 跳转全部移除。
4. Django 只接受单一固定公网 IPv4 及对应 HTTP CSRF 来源。
5. SQLite、媒体、静态和备份目录保持持久化。
6. HTTP 风险与安全组白名单门禁在文档中明确记录。

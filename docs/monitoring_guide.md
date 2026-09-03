# DEP-IP-03 健康检查、日志与监控合同

## 1. 分层健康检查

- Web 容器通过 `/health/ready/` 检查 Django 与 SQLite，只返回通用状态。
- Nginx 容器通过 HTTP `/nginx-health` 检查入口进程。
- 宿主机每五分钟检查两个容器、HTTP 入口、磁盘、异机备份新鲜度和时间同步。
- 固定公网 IP + HTTP 模式不执行 TLS 证书或 443 端口检查。
- 健康端点不得输出路径、异常正文、版本、学生信息或密钥。

## 2. 日志

Django、Gunicorn 和 Nginx 写标准输出和错误输出，Compose 使用 Docker `local` 日志驱动，
每个服务最多保留五个 20 MiB 分片。日志不得记录密码、Cookie、Session、Excel 正文或完整学生资料。

```bash
docker compose --env-file deploy/compose.env -f compose.production.yml logs --tail 200 web nginx
journalctl -u party-archive-health.service --since today
```

## 3. 定时检查

将 systemd 模板复制到 `/etc/systemd/system/` 后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now party-archive-health.timer
systemctl list-timers party-archive-health.timer
```

`/srv/party-archive/secrets/monitoring.env` 可以覆盖路径和阈值，权限必须为 0600。仓库不得保存
Webhook 或其他告警凭据。

## 4. 阈值

| 信号 | 警告 | 严重 |
| --- | --- | --- |
| 磁盘 | 使用率达到 80% | 使用率达到 90% |
| 异机备份 | — | 成功标记超过 25 小时 |
| 容器/HTTP | 单次失败 | 连续 3 次失败 |
| 时间同步 | 未同步 | 长期未恢复 |

监控恢复前不得通过删除检查或放宽阈值掩盖故障。HTTP 的明文传输风险由阿里云安全组和宿主机
防火墙的访问来源白名单控制；安全组审计属于正式发布验收项。

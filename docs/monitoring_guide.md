# DEP-06 健康检查、日志与监控合同

## 1. 分层健康检查

- Web容器通过`/health/ready/`验证Django响应和SQLite只读查询；失败只返回通用503。
- Nginx容器通过`/nginx-health`验证TLS入口进程。
- 宿主机每5分钟检查两个容器、HTTPS入口、磁盘、TLS、异机备份新鲜度和时间同步。
- 健康端点不得输出数据库路径、异常正文、版本、学生信息或密钥。

## 2. 日志

Django、Gunicorn和Nginx继续写标准输出/错误。Compose使用Docker `local`日志驱动，
每个服务最多保留5个20 MiB分片。业务审计继续写`OperationLog`，不得把密码、Cookie、
Session、Excel正文或完整学生资料写入运行日志。

查看日志：

```bash
docker compose --env-file deploy/compose.env -f compose.production.yml logs --tail 200 web nginx
journalctl -u party-archive-health.service --since today
```

## 3. 安装定时检查

创建仅有Docker只读检查权限的`party-archive-ops`运维账号，将systemd模板复制到
`/etc/systemd/system/`后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now party-archive-health.timer
systemctl list-timers party-archive-health.timer
```

`/srv/party-archive/secrets/monitoring.env`可覆盖阈值和路径，权限必须为0600。告警平台应监听
service失败状态；第一版允许接入腾讯云监控、邮件或企业微信，但仓库不保存Webhook或凭据。

## 4. 阈值

| 信号 | 警告 | 严重 |
| --- | --- | --- |
| 磁盘 | 使用率≥80% | 使用率≥90% |
| TLS | 30天内到期 | 7天内到期 |
| 异机备份 | — | 成功标记超过25小时 |
| 容器/HTTPS | 单次失败 | 连续3次失败 |

监控脚本返回0表示无严重故障，返回2表示需要告警。告警恢复前不得通过删除检查或放宽阈值
掩盖故障。DEP-07负责在远端备份验证成功后原子更新`.last-offsite-success`。

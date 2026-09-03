# 日常运维手册（DEP-09）

## 1. 每日检查

```bash
cd /srv/party-archive/app
docker compose --env-file deploy/compose.env -f compose.production.yml ps
sudo systemctl status party-archive-health.timer party-archive-backup.timer
sudo journalctl -u party-archive-health.service --since today --no-pager
sudo journalctl -u party-archive-backup.service --since today --no-pager
df -h /srv/party-archive
```

确认容器健康、磁盘使用率低于80%、固定公网 IPv4 可达、80端口仅向登记来源开放、时间同步正常、异机备份成功标记不超过25小时。日志不得包含密码、Cookie、Session、Excel正文或完整学生信息。

## 2. 日常升级

1. 确认审批、维护窗口、固定新旧镜像摘要和回退负责人。
2. 暂停管理员写入与Excel导入；创建一致性数据库及媒体备份并上传COS，记录SHA-256和对象版本。
3. 比较候选迁移；不兼容迁移必须先完成专项恢复方案评审。
4. 修改 `deploy/compose.env` 中的固定 `WEB_IMAGE`，执行 `docker compose config --quiet`。
5. 执行 `docker compose ... up -d`，等待 healthy 后检查HTTP入口、登录、查询、导入历史、静态资源和健康端点。
6. 记录新旧版本、备份、执行人、时间和验证结果。

## 3. 应用回退

无不兼容数据库迁移时，优先只回退镜像：暂停写入，保留脱敏日志，将 `WEB_IMAGE` 恢复为上一已验证摘要，再执行 `docker compose ... up -d` 并复查。不得使用浮动标签。

存在不兼容迁移或数据损坏时必须保持停机，先验证备份，再按 `docs/backup_restore_guide.md` 执行批准的数据恢复。禁止自动逆向迁移、在线替换SQLite、手工删除WAL/SHM文件。恢复后先运行 `migrate --check` 和 `check`。

## 4. 备份和恢复

- 每日及每次正式导入前后备份；本机备份不能替代COS异机备份。
- COS对象使用私有访问、服务端加密、版本控制和最小权限凭据。
- 每季度或重大变更前执行异机恢复演练；目标 RPO≤24小时、RTO≤4小时。
- 普通错误导入优先使用业务回滚；SQLite灾难恢复只用于数据库损坏或业务回滚不可用。

## 5. 账号、网络和秘密

运维账号使用个人SSH密钥，不共享密码；离岗立即撤权。生产 `.env` 权限必须为0600。固定公网 IPv4 的HTTP入口必须限制可信来源；若业务需要向不受信任公网开放，必须升级到HTTPS后再发布。COS和管理员凭据不得进入Git、聊天、工单或普通日志。

## 6. 完成标准

容器 healthy、HTTP入口与静态资源正常、8000未暴露、九支部和关键数据量正确、导入历史可查、备份上传成功、监控无严重告警、回退点可用，并由执行人与复核人共同记录结论。

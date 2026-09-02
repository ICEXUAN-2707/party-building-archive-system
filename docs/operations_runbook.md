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

确认容器健康、磁盘低于80%、TLS剩余超过30天、时间同步正常、异机备份成功标记不超过25小时。日志不得包含密码、Cookie、Session、Excel正文或完整学生信息。

## 2. 日常升级

1. 确认审批、维护窗口、固定新旧镜像摘要及回退负责人。
2. 暂停管理员写入和Excel导入；创建一致性数据库及媒体备份并上传COS，记录SHA-256和对象版本。
3. 比较候选迁移；不兼容迁移必须先完成专项恢复方案评审。
4. 修改`deploy/compose.env`中的固定`WEB_IMAGE`，执行`docker compose config --quiet`。
5. `docker compose ... up -d`，等待healthy后检查登录、查询、导入历史、静态资源和健康端点。
6. 记录新旧版本、备份、执行人、开始/结束时间和验证结果。

## 3. 应用回退

无不兼容数据库迁移时，优先只回退镜像：暂停写入，保留现场日志，将`WEB_IMAGE`恢复为上一已验证摘要，再执行`docker compose ... up -d`并复查。不得使用浮动标签。

存在不兼容迁移或数据损坏时必须保持停机，先验证备份，再按`docs/backup_restore_guide.md`执行批准的数据恢复。禁止自动逆向迁移、在线替换SQLite、手工删除WAL/SHM文件。恢复后先运行`migrate --check`和`check`，再恢复服务。

## 4. 备份和恢复

- 每日及每次正式导入前后执行备份；本机备份不能替代COS异机备份。
- COS对象必须使用私有访问、服务端加密、版本控制及最小权限凭据。
- 每季度或重大变更前执行异机恢复演练，记录RPO和RTO；目标RPO不超过24小时、RTO不超过4小时。
- 普通错误导入优先使用业务回滚；SQLite灾难恢复仅用于业务回滚不可用或数据库损坏。

## 5. 账号、证书和秘密

运维账号使用个人SSH密钥，不共享密码；离岗立即撤权。生产`.env`权限必须为0600。TLS、COS和管理员凭据按学校制度轮换，秘密不得进入Git、聊天、工单或普通日志。

## 6. 变更完成标准

容器healthy、HTTPS和静态资源正常、九支部及关键数据量正确、导入历史可查、备份上传成功、监控无严重告警、回退点可用，并由执行人和复核人共同记录结论。

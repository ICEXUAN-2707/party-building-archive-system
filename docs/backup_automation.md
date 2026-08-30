# DEP-07 本机与COS异机备份自动化合同

## 1. 备份闭环

每日备份使用SQLite Backup API生成一致性数据库副本，执行`PRAGMA integrity_check`，并将数据库、
媒体文件、SHA-256清单和发布标识写入原子生成的`tar.gz`。创建后立即执行一次完整解包校验。
本机默认保留最近7个每日备份和最近10个导入前后备份文件组。

```bash
docker compose exec -T web python manage.py create_production_backup --reason daily
docker compose exec -T web python manage.py create_production_backup --verify /data/backups/<archive>.tar.gz
```

## 2. COS要求

使用私有、已启用版本控制的腾讯云COS存储桶。上传通过HTTPS和最小权限子账号完成，并强制指定
SSE-COS AES256。上传成功后必须通过HEAD校验对象大小、自定义SHA-256、加密头和版本ID；任一项
缺失均不更新`.last-offsite-success`监控标记。

真实`backup.env`放在`/srv/party-archive/secrets/backup.env`且权限0600，不进入Git。脚本仅通过
`docker exec --env-file`把凭据注入单次上传进程，不把COS密钥放入长期运行的Web进程。建议CAM仅授权
指定存储桶前缀的PutObject、HeadObject、GetObject和版本读取操作。存储桶启用版本控制、默认
SSE-COS、生命周期规则和访问日志。

## 3. 调度和失败处理

`party-archive-backup.timer`每天北京时间02:30执行本机备份、校验、COS上传和远端元数据校验。
任何步骤失败即返回非零，由DEP-06监控告警；失败时不得清理本机新备份，也不得伪造成功标记。

## 4. 恢复演练

至少每季度从COS下载指定版本到隔离主机，先核对SHA并执行`create_production_backup --verify`，
再在停机状态恢复数据库和媒体。恢复前备份现状，恢复后检查迁移状态、九支部、身份、查询、
导入历史和媒体证据。正式上线前必须形成一次异机恢复报告，证明RPO不超过24小时、RTO不超过4小时。

下载必须显式指定对象版本：

```bash
python manage.py download_backup_from_cos \
  --object-key party-archive/production/<archive>.tar.gz \
  --version-id <COS版本ID> \
  --filename <archive>.tar.gz
```

COS SDK的加密与对象元数据行为依据腾讯云官方SSE-COS、HEAD Object和CRC64文档；版本控制必须在
存储桶侧启用，代码只验证返回的版本ID，不尝试擅自更改桶级策略。

# SQLite备份与灾难恢复指南

本指南适用于第一版单机SQLite部署。普通导入撤销优先使用管理员页面的“最近成功批次回滚”；只有业务回滚不可用或数据库文件损坏时，才使用SQLite灾难恢复命令。

## 1. 恢复能力边界

- 恢复源只能是正式导入前生成的`media/imports/batch_<id>/pre_import.sqlite3`；
- 命令会校验SQLite完整性、关键表、批次ID、批次导入前状态和原Excel哈希绑定；
- 默认只校验，不修改数据库；
- 恢复只能在Web及所有其他数据库进程停止后执行；
- 不存在Web在线替换数据库的入口；
- 原始恢复源不会被移动、覆盖或删除。

## 2. Excel到达后的上线流程

真实数据尚未到达时，可以使用测试或合成Excel执行同样流程。真实Excel到达后：

1. 按部署指南完成环境变量、迁移、九个党支部和data_admin初始化；
2. data_admin在Excel上传页提交文件；
3. 检查文件哈希、工作表识别、有效行、错误、警告和跳过数量；
4. 对无法识别、列错位、重复学号等错误先修正Excel，再重新上传；
5. 仅对预览无阻断冲突且存在有效候选数据的批次确认导入；
6. 在管理员查询和学生查询中抽查支部、阶段、申请时间、汇报总数及明细；
7. 保存批次ID、原文件哈希和验收记录；
8. 重启服务后复查查询及导入历史，确认SQLite和`media/imports`位于持久化存储。

系统不会根据文件名直接导入，不接受客户端重建预览，也不会导入错误行。

## 3. 恢复前只读验证

可在服务运行时执行只读验证：

```powershell
python manage.py restore_import_backup --batch-id <批次ID> --verify-only
```

省略模式参数时仍然只验证：

```powershell
python manage.py restore_import_backup --batch-id <批次ID>
```

验证成功会输出恢复源路径和SHA-256，并明确提示数据库未修改。

## 4. 停机恢复

1. 停止Web容器、开发服务器以及所有可能访问SQLite的脚本；
2. 确认没有`db.sqlite3-journal`、`db.sqlite3-wal`或`db.sqlite3-shm`边车文件；不要手工删除活动进程仍在使用的文件；
3. 先执行`--verify-only`；
4. 执行正式恢复：

```powershell
python manage.py restore_import_backup --batch-id <批次ID> --confirm --maintenance-mode
```

命令在替换前会使用SQLite backup API保存当前数据库，并生成SHA-256。保护备份位于正式数据库同目录下的：

```text
disaster_restore_backups/
```

恢复源会先复制到正式数据库同目录的随机临时文件，通过完整性和批次绑定校验后再原子替换。替换后验证失败时，命令会自动尝试用恢复前保护备份回退。

## 5. 恢复后检查

恢复成功后，在重新启动Web前执行：

```powershell
python manage.py migrate --check
python manage.py check
python manage.py showmigrations
```

然后启动单一Web实例并核对：

- 管理员和学生登录；
- 学生数量及九个支部分布；
- 申请记录、思想汇报汇总和有效明细；
- 导入历史、原Excel、预览和回滚证据；
- 恢复目标批次之后的数据是否已按预期消失。

不要在灾难恢复后直接执行普通`migrate`修改数据库；应先确认代码版本与备份的迁移状态一致。

## 6. 安全拒绝与故障处理

以下情况命令不会替换数据库：

- 非SQLite或内存SQLite；
- 批次、备份或当前数据库不存在；
- 备份为空、损坏、缺少关键表或批次绑定不一致；
- 恢复源等于当前数据库；
- 没有显式提供停机确认；
- 检测到SQLite journal、WAL或SHM边车文件；
- 恢复前保护备份创建或校验失败；
- 同目录临时恢复文件校验失败。

若命令报告自动回退失败，保持服务停机，不要继续写入；使用输出的恢复前保护备份进行人工处理并保留全部日志和文件现场。

## 7. 保存与异机备份

正式环境至少持久化：

- 当前SQLite数据库；
- `media/imports`中的原Excel和批次证据；
- `disaster_restore_backups`；
- 配置备份和必要日志。

至少保留最近五个导入批次的原文件及导入前后备份，并将最近一次验证可恢复的完整备份复制到学院授权的另一存储位置。不得将真实数据库、真实Excel或备份提交到Git。

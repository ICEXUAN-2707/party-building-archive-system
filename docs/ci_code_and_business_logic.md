# 项目CI代码与业务逻辑说明

## 1. 两层门禁

```text
代码层CI
  → Repository policy
  → Windows/Ubuntu Django检查、迁移和全量测试

部署层CI
  → 容器合同
  → 候选SHA镜像构建
  → Trivy漏洞扫描
  → 固定公网IPv4 + HTTP Compose冒烟
```

两层必须同时通过。容器启动不能替代业务测试，单元测试也不能替代真实镜像与Compose验证。

## 2. 仓库与数据边界

`scripts/ci_guard.py`禁止提交 `.env`、SQLite、Excel、上传文件、备份、虚拟环境和Python缓存，并检查测试后污染。真实学生数据和运维秘密不得进入Git历史、CI日志或制品。

## 3. 业务回归范围

- 学生认证只使用服务端Session中的 `student_id`，管理员和学生Session隔离。
- `viewer_admin`只读，`data_admin`执行导入、下载与回滚等写操作。
- Excel解析动态识别工作表、字段和思想汇报列，预览阶段不写业务表。
- 正式导入在事务中重新验证文件与快照，失败不得部分写入。
- 业务回滚只处理最近成功批次；SQLite灾难恢复必须停机并先验证备份。
- 备份使用SQLite Backup API、SHA-256和COS对象版本；健康端点不泄露内部错误。

## 4. 容器冒烟

冒烟脚本在 `RUNNER_TEMP` 创建隔离工作区，显式执行迁移和九支部初始化，再启动Gunicorn与Nginx。它验证HTTP健康端点、本地Bootstrap、Web 8000未发布、非Root用户、只读根文件系统和重启后数据持久化。临时HTTP端口只绑定回环地址。

## 5. CI不能替代的工作

CI不拥有真实服务器、安全组、COS生产凭据或学生数据，因此不能证明系统已经上线。仍须在WorkBuddy服务器完成脱敏部署演练，再在自购服务器完成安全组、备份、恢复、回退、监控和正式审批。

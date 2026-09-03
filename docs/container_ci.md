# DEP-08 容器CI实现说明

## 1. 目标

Container CI在双平台Django测试之后补充生产容器动态验证。它不发布镜像、不连接云服务器、不使用生产秘密，只在GitHub Ubuntu Runner构建当前候选SHA、执行安全扫描并启动临时Compose。

## 2. 作业结构

`Container policy and contracts`运行仓库策略及容器合同测试。`Build, scan, and smoke production containers`构建 `party-archive-web:${GITHUB_SHA}`，执行Trivy扫描，再调用 `scripts/container_smoke_test.py`。

冒烟执行器只允许在GitHub Actions运行，工作目录必须位于 `RUNNER_TEMP` 下。它创建数据库、媒体、静态和备份目录，生成虚假生产变量，只把HTTP端口绑定到 `127.0.0.1:18080`。结束后删除环境文件，并使用不带 `--volumes` 的Compose清理。

## 3. 动态检查

1. 镜像用户UID为10001。
2. 镜像不包含环境文件、Excel、SQLite、测试或Git历史。
3. 缺少生产变量时拒绝启动。
4. 空库迁移和九支部初始化成功。
5. Web与Nginx生产Compose启动成功。
6. Nginx、存活、就绪和本地Bootstrap资源可通过HTTP访问。
7. Web的8000端口未发布到宿主机。
8. 重启Web后九支部仍存在，证明SQLite挂载有效。
9. 候选镜像不存在已有修复版本的CRITICAL漏洞。

## 4. 安全边界

CI权限仅为 `contents: read`，Checkout关闭凭据持久化。Trivy Action固定到完整提交SHA。CI不上传临时数据库或Compose环境文件，脚本不得打印环境变量值。HTTP只绑定Runner回环地址，不能证明公网部署安全。

## 5. 失败处理

任何构建、扫描、迁移、健康、HTTP、静态资源、端口或持久化检查失败都会阻断PR。Compose启动后无论成功失败都输出 `ps` 与最后200行脱敏容器日志，并清理容器和网络。需要豁免的漏洞必须登记影响、修复计划、负责人和到期日。

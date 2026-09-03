# DEP-08 容器CI实现说明

## 1. 目标

Container CI在现有双平台Django测试之后补充生产容器动态验证。它不发布镜像、不连接云服务器、
不使用生产密钥，只在GitHub Ubuntu Runner上构建当前候选SHA、执行安全扫描并启动临时Compose。

## 2. 作业结构

`Container policy and contracts`负责仓库策略和容器合同测试。`Build, scan, and smoke production
containers`在前一作业通过后构建`party-archive-web:${GITHUB_SHA}`，执行Trivy扫描，再调用
`scripts/container_smoke_test.py`。

冒烟执行器只允许在GitHub Actions运行，工作目录必须位于`RUNNER_TEMP`下。它生成短期自签名
证书和虚假生产变量，端口只绑定`127.0.0.1:18080/18443`。测试结束后删除环境文件和证书，
并执行不带`--volumes`的Compose清理。

## 3. 动态检查

1. 镜像用户UID为10001；
2. 镜像不包含环境文件、Excel、SQLite、测试或Git历史；
3. 缺少生产变量时拒绝启动；
4. 空库迁移和九支部初始化成功；
5. Web与Nginx组成的生产Compose可启动；
6. HTTP跳转HTTPS；
7. Nginx、存活、就绪和本地Bootstrap资源可访问；
8. Web的8000端口没有发布到宿主机；
9. 重启Web后九支部仍存在，证明SQLite绑定挂载有效；
10. 候选镜像不存在有修复版本的CRITICAL漏洞。

## 4. 安全边界

CI权限仅为`contents: read`，Checkout关闭凭据持久化。Trivy Action固定到v0.36.0对应的完整提交
`ed142fd0673e97e23eac54620cfb913e5ce36c25`。CI不会上传临时证书、数据库或Compose环境文件。
冒烟日志可能进入Actions日志，因此脚本不得打印环境变量或证书内容。

## 5. 失败处理

任何构建、扫描、迁移、健康、HTTPS、静态资源、端口或持久化检查失败都会阻断PR。Compose启动
后无论成功失败都输出`ps`和最后200行容器日志，并执行容器与网络清理。日志不得作为放宽安全
门禁的理由；需要豁免的漏洞必须单独登记影响、修复计划、负责人和到期日。

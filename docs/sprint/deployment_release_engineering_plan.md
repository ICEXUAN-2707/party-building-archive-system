# 部署发布工程阶段开发方案

## 1. 方案信息

| 项目 | 内容 |
| --- | --- |
| 制定日期 | 2026-08-31 |
| 前置基线 | PR #34，发布候选代码`72653d96d0f8728736d1ae9baf3274897fed3f63` |
| 基线结论 | Go；本地全量、1500条验收及双平台CI通过 |
| 阶段范围 | DEP-08容器CI、DEP-09运维手册、DEP-10脱敏发布候选演练 |
| 阶段目标 | 从“可部署代码”推进到“可重复演练、可回退、可审计的发布候选” |
| 非目标 | 不导入真实学生数据，不擅自购买云资源，不创建正式生产Tag，不开放公网 |

本方案以`docs/spec.md`、`docs/deployment_decisions.md`和现有DEP-03至DEP-07合同为冻结输入。
若发现冻结规则冲突，停止对应实现并提交决策项，不在部署脚本中静默改变业务规则。

## 2. 总体交付路径

```text
PR A：DEP-08 容器构建与冒烟CI
  ↓ 容器门禁通过
PR B：DEP-09 部署、升级、回退和故障Runbook
  ↓ 干净环境可按文档复现
PR C：DEP-10 脱敏发布候选与异机恢复演练
  ↓ 演练签字通过
develop → main发布PR → RC Tag → 正式发布审批
```

三个PR必须顺序合并。后续PR基于前一PR进入`develop`后的固定SHA，不允许长期并行修改
同一工作流、Compose或部署文档。

## 3. DEP-08：容器构建与冒烟CI

### 3.1 目标

把当前Dockerfile和Compose的静态合同验证升级为真实构建、真实启动和健康检查门禁，确保每个
面向`develop`或`main`的候选都能在GitHub Ubuntu Runner上复现生产容器结构。

### 3.2 计划文件

```text
.github/workflows/container-ci.yml
scripts/container_smoke_test.py
tests/test_container_ci_contract.py
docs/container_ci.md
```

仅在确需修复动态验证缺陷时修改：

```text
Dockerfile
compose.production.yml
scripts/docker_entrypoint.py
deploy/nginx/*
```

### 3.3 CI作业设计

#### Job 1：容器策略检查

- 校验Dockerfile、Compose、Nginx、entrypoint及示例环境文件存在；
- 运行现有镜像、Compose、静态资源和可观测性合同测试；
- 检查工作流内第三方Action固定到完整提交SHA；
- 检查工作流权限保持`contents: read`，不向PR代码暴露生产凭据；
- 检查镜像标签只使用候选SHA，不使用`latest`作为验收依据。

#### Job 2：Web镜像真实构建

- 使用Ubuntu Runner和冻结Python基础镜像构建Web镜像；
- 镜像本地标签使用`party-archive-web:${GITHUB_SHA}`；
- 导出镜像ID、RepoDigest可用信息、基础镜像和依赖版本；
- 检查默认用户为UID/GID 10001，工作目录为`/app`；
- 检查镜像中不存在`.env`、SQLite、Excel、媒体、测试、Git历史和备份；
- 缺少生产密钥、域名或CSRF来源时，容器必须拒绝启动；
- 生产变量完整时`collectstatic`成功，Gunicorn仅有一个worker。

#### Job 3：Compose与HTTPS冒烟

- 在Runner临时目录创建数据库、媒体、静态、备份和TLS目录；
- 生成仅用于CI的短期自签名证书，不上传为Artifact；
- 生成不含真实秘密的临时生产环境文件；
- 显式执行数据库迁移和九支部初始化；
- 启动单Web实例和Nginx；
- 等待两个容器进入`healthy`，设置明确总超时；
- 验证HTTP跳转HTTPS、`/nginx-health`、`/health/live/`和`/health/ready/`；
- 验证宿主机没有映射8000端口；
- 验证本地Bootstrap资源通过HTTPS返回；
- 重启Web容器并复查九支部和健康状态，证明持久化目录有效；
- 无论成功失败都收集脱敏后的`docker compose ps`和最后200行日志；
- `always()`清理容器、网络、临时证书和临时数据库。

#### Job 4：安全扫描

- 对候选镜像生成依赖和系统包清单；
- 使用经评审且固定SHA的扫描工具执行镜像漏洞扫描；
- CRITICAL且有可用修复的漏洞阻断合并；
- HIGH漏洞必须逐项登记影响、修复版本和负责人，不允许静默忽略；
- 扫描豁免必须有到期日、理由和审批人，不把永久忽略规则写成默认配置；
- 扫描报告不得包含环境变量值、文件内容或凭据。

### 3.4 触发与并发

- `pull_request`目标为`develop`、`main`；
- `push`目标为`develop`、`main`；
- 支持`workflow_dispatch`；
- 对Dockerfile、Compose、requirements、部署脚本、Nginx、生产设置发生变化时必跑；
- 发布候选PR即使只改业务代码，也至少运行Web镜像构建和基础健康冒烟；
- 使用并发组取消同一PR的旧运行，禁止跨PR互相取消。

### 3.5 完成定义

1. 全新Ubuntu Runner可构建镜像；
2. 缺配置拒绝启动、完整配置正常启动；
3. Web和Nginx均healthy；
4. HTTPS、静态资源、数据库和持久化冒烟通过；
5. 非Root、单worker、只读根文件系统和端口边界通过；
6. 漏洞结论已处理；
7. 失败时可从脱敏日志定位原因；
8. 现有Repository policy及Windows/Ubuntu Django测试继续通过。

## 4. DEP-09：部署与运维Runbook

### 4.1 目标

将当前分散在镜像、Compose、监控和备份文档中的说明收敛成一套能由第二名成员在干净主机上
逐条执行的操作手册。命令必须可复制，参数必须明确标出替换位置，危险操作必须设置停机和备份门禁。

### 4.2 计划文件

```text
docs/deployment_guide.md
docs/operations_runbook.md
docs/release_checklist.md
docs/incident_response.md
scripts/validate_production_host.sh
tests/test_operations_docs_contract.py
```

### 4.3 文档结构

#### 首次部署

- Ubuntu、CPU、内存、磁盘、时区、时间同步和Docker版本检查；
- 专用运维账号、SSH密钥、安全组和宿主机防火墙；
- `/srv/party-archive`目录及UID/GID 10001权限；
- 固定Git Tag或提交、不可变镜像标签和摘要核对；
- 环境变量、TLS证书、Compose参数和COS配置；
- 迁移、九支部初始化、首个管理员创建；
- 启动、健康检查、日志和脱敏数据验证。

#### 日常升级

- 发布审批和变更窗口；
- 升级前数据库与媒体备份、COS上传及校验；
- 拉取固定镜像摘要，不部署浮动分支；
- 停止写入、迁移评估、启动和健康复查；
- 记录旧/新版本、数据库备份、媒体索引和操作人。

#### 应用回退

- 区分“仅应用回退”和“应用加数据恢复”；
- 无数据库迁移变化时优先只回退镜像；
- 存在不兼容迁移时必须按已评审的数据恢复方案停机处理；
- 禁止自动逆向迁移或在线替换SQLite；
- 回退后复查登录、查询、导入历史、静态资源和健康状态。

#### 故障处置

- 容器不健康、502/503、磁盘不足、TLS临期、备份过期和SQLite损坏；
- 每类故障提供观察命令、判断条件、允许操作、禁止操作和升级联系人；
- 日志和工单不得包含密码、Cookie、Session、真实Excel正文或完整学生资料；
- 明确停机、数据封存和恢复演练升级条件。

### 4.4 可执行性验证

- 文档合同测试检查关键章节、命令和禁止项存在；
- 主机验证脚本只读检查系统与目录，不安装软件、不修改防火墙；
- 由未参与编写的成员在空白Ubuntu环境按文档复现；
- 记录每条命令的结果、耗时、偏差和修订项；
- 文档中的版本、路径、服务名和环境变量必须与仓库配置一致。

### 4.5 完成定义

1. 第二名成员可以从零部署脱敏环境；
2. 升级、应用回退、停机恢复和故障处置都有明确步骤；
3. 所有危险命令带前置备份和确认条件；
4. 文档与Dockerfile、Compose、systemd和管理命令一致；
5. 文档合同测试与干净主机复现通过。

## 5. DEP-10：脱敏发布候选与恢复演练

### 5.1 目标

在满足最低规格的Ubuntu 24.04主机上，以固定候选SHA和不可变镜像完成一次接近生产的脱敏发布、
重启、升级、回退、COS备份和异机恢复演练，形成可签字的发布证据。

### 5.2 计划文件

```text
docs/release_acceptance_template.md
docs/disaster_recovery_drill_template.md
docs/asset_register_template.md
scripts/run_deployment_acceptance.sh
tests/test_release_acceptance_contract.py
```

真实资产值、IP、域名、联系人和凭据只进入授权运维台账，不提交仓库。

### 5.3 演练阶段

#### 阶段A：资产与安全门禁

- 核对2 vCPU、4 GiB内存、磁盘可用空间、Ubuntu 24.04和x86_64；
- 登记安全组、SSH来源、域名/TLS方案、COS桶、快照和责任人；
- 自签名证书只用于受限IP演练，正式上线必须使用受信任证书；
- 演练主机不导入真实学生数据。

#### 阶段B：首次部署

- 从固定Tag候选或固定提交构建/拉取不可变镜像；
- 记录镜像摘要、Compose配置摘要和环境变量键名清单；
- 完成迁移、支部初始化和脱敏管理员创建；
- 导入固定种子1500条合成数据；
- 检查登录、查询、导入、回滚、静态资源和审计日志。

#### 阶段C：稳定性与持久化

- 重启Web容器、重启Compose、重启宿主机；
- 每次重启后核对数据量、九支部、导入历史、媒体证据和健康端点；
- 运行磁盘、TLS、时间同步和备份新鲜度监控；
- 验证日志轮换且日志不包含敏感正文。

#### 阶段D：备份与异机恢复

- 创建本机一致性备份并完成解包校验；
- 上传私有COS并核对大小、SHA-256、加密头和版本ID；
- 从指定对象版本下载到隔离恢复主机；
- 在停机状态恢复数据库和媒体；
- 核对迁移、九支部、1500名学生、4500条有效思想汇报、导入历史和文件哈希；
- 记录实际RPO和RTO，必须满足RPO≤24小时、RTO≤4小时。

#### 阶段E：升级与回退

- 从上一验证版本升级到候选版本；
- 执行升级前备份、启动和业务抽查；
- 回退到上一不可变镜像；
- 数据结构兼容时不得无故恢复旧数据库；
- 如模拟不兼容迁移，必须保持停机并按批准的数据库恢复路径处理。

### 5.4 Go/No-Go门禁

**Go必须同时满足：**

1. DEP-08容器CI在候选SHA通过；
2. DEP-09由第二名成员完成干净主机复现；
3. 1500条脱敏数据部署、重启和查询通过；
4. COS指定版本异机恢复通过；
5. 应用回退通过；
6. RPO、RTO、健康、磁盘和TLS门禁满足；
7. 不存在未接受的P0/P1缺陷；
8. 五类责任人和正式资产已登记；
9. 项目、运维、数据和安全负责人共同签字。

任何一项缺失均不得创建正式版本Tag或导入真实数据。

## 6. 测试与证据策略

每个PR必须保留：

- 固定Git SHA；
- Repository policy、Ubuntu、Windows和容器CI链接；
- 测试数量、耗时和平台；
- 镜像ID/摘要、基础镜像和扫描结论；
- Compose健康状态和脱敏日志；
- 演练报告、RPO、RTO及签字状态；
- 缺陷编号、级别、负责人和处理结论。

不得提交：真实`.env`、TLS私钥、COS凭据、真实Excel、SQLite、媒体、备份、IP、联系人或完整日志。

## 7. 建议排期与责任接口

| 阶段 | 建议工期 | 主要责任角色 | 前置依赖 |
| --- | ---: | --- | --- |
| DEP-08容器CI | 1.5—2天 | CI/集成负责人、应用运维 | PR #34合入`develop` |
| DEP-09统一Runbook | 1.5—2天 | 应用运维、文档复核人 | DEP-08接口稳定 |
| DEP-10脱敏演练 | 2—3天 | 运维、数据、安全负责人 | DEP-08、DEP-09、演练资产 |
| 发布评审 | 0.5天 | 项目负责人及五类责任人 | DEP-10通过 |

纯开发和文档预计3—4个工作日；包含云主机、COS、域名/TLS协调和完整演练预计5—7个工作日。
外部资产未就绪时可以完成DEP-08和DEP-09，但DEP-10不得用本地单元测试代替。

## 8. 开工顺序

1. 合并PR #34到`develop`并记录合并SHA；
2. 从最新`develop`创建`feat/dep08-container-ci`；
3. 完成容器CI并通过后合入；
4. 创建`docs/dep09-operations-runbook`完成Runbook与复现；
5. 创建`release/dep10-dry-run`执行脱敏主机演练；
6. DEP-10 Go后再规划`develop`到`main`发布PR和RC Tag。

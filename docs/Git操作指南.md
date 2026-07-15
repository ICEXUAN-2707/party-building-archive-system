# Git 完整协作规范手册
## 一、Git 第一性原理：理解底层逻辑
### 1. 快照而非差异
Git 每次提交（commit）存储的是项目当时的完整目录快照，而非简单的代码行修改记录。如果文件未变，Git 会复用旧文件的哈希值，实现高效去重。

### 2. 四种核心对象
- Blob：只存储文件的纯数据内容，不包含文件名。
- Tree：相当于文件夹，记录文件名、权限，并指向具体的 Blob 或子 Tree。
- Commit：提交对象，指向一个顶层的 Tree（代表整个项目目录），并包含提交者信息和时间戳。
- Tag：给某个特定的 Commit 打上一个不可变的标签（如 v1.0.0）。

四类对象通过 SHA-1 哈希值互相链接，构成 Git 的底层数据库。

### 3. 分支的本质
分支只是一个指向特定 Commit 的轻量级指针。创建和切换分支仅在 `.git/refs/heads/` 目录下新建/移动文本文件，资源开销极低。

### 4. 有向无环图（DAG）
Git 提交历史依靠父指针串联形成图谱。合并提交存在多父节点，因此历史并非单一线性结构，而是网状有向无环图。

## 二、环境准备：安装与基础配置
### 1. 安装指南
- Windows：访问 Git 官网下载安装包，安装时勾选「Add Git Bash Here」。
- macOS：终端执行 `git --version`，按提示安装 Xcode Command Line Tools。
- Linux：
  Debian/Ubuntu：
  ```bash
  sudo apt-get install git
  ```
  CentOS/RHEL：
  ```bash
  sudo yum install git
  ```

### 2. 核心配置命令（首次使用必做）
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
git config --global init.defaultBranch main
git config --global color.ui auto
git config --global core.autocrlf true  # Windows 专属，解决换行符冲突
```

### 3. 配置验证方法
1. 查看全部全局配置：
```bash
git config --global --list
```
2. 单独查看用户名配置：
```bash
git config --global user.name
```

## 三、协作地基：建库与分支初始化（组长主导）
仓库地址：`https://github.com/ICEXUAN-2707/party-building-archive-system`

### 1. 远程仓库创建
在 GitHub 新建仓库时，必须勾选对应技术栈的 `.gitignore` 模板，自动过滤编译缓存、日志、依赖包等无用文件。
本项目仓库地址：https://github.com/ICEXUAN-2707/party-building-archive-system

### 2. 本地主分支初始化
克隆仓库并创建开发主线 develop：
```bash
git clone https://github.com/ICEXUAN-2707/party-building-archive-system
cd party-building-archive-system
git checkout -b develop
git push -u origin develop
```
执行完成后远程仓库存在两条核心分支：
- main：线上稳定版本分支
- develop：团队统一开发主线

### 3. 组员接入流程
所有成员本地执行如下命令同步仓库与开发分支：
```bash
git clone https://github.com/ICEXUAN-2707/party-building-archive-system
cd party-building-archive-system
git checkout develop
git pull origin develop
```

### 4. 功能分支命名规范
统一格式：`feature/功能名`，示例：`feature/user-login`
> ⚠️ 禁止直接在 develop、main 分支编写业务代码，所有新功能独立新建功能分支开发。

## 四、日常开发工作流：从编码到合并
### 1. 开发基础三步曲
修改本地代码 → 添加至暂存区 → 提交本地仓库
```bash
git add .
git commit -m "清晰描述本次修改内容"
```

### 2. Pull Request (PR) 机制
#### 使用必要性
1. 避免多人并行开发代码覆盖；
2. 支持团队代码评审；
3. 完整留存版本迭代与协作记录。

#### PR 发起流程
GitHub 仓库页面点击「Compare & pull request」，参数规范：
- Base（目标分支）：develop
- Compare（源分支）：个人 feature 功能分支

### 3. 代码冲突（Conflict）标准解决四步
1. 拉取开发分支最新代码：
```bash
git pull origin develop
```
2. VS Code 区分冲突代码块：Current Change（本地修改）、Incoming Change（远程新代码）
3. 手动选择保留单方代码，或选择 Accept Both 合并两边修改
4. 冲突处理完成后重新提交推送
```bash
git add .
git commit -m "解决代码冲突"
git push origin feature/你的功能名
```

## 五、集成测试实操指南
### 1. 集成方案选择：大爆炸集成
适用于课程/项目开发场景：项目规模小、模块接口定义清晰，全部功能开发完成后统一合并至 develop 分支集中测试，效率最高。

### 2. 集成测试操作步骤
1. 切换至开发分支并同步远端最新代码
```bash
git checkout develop
git pull origin develop
```
2. 启动项目执行端到端（E2E）完整业务联调
3. 核心校验点：前后端接口数据字段完全匹配，以接口文档（Spec）为准。

### 3. 开发避坑建议
1. 高频小规模合并：避免一次性堆积大量代码再合并；
2. 文件按人拆分分工，减少文件修改重叠；
3. 修改共用文件前，团队群提前沟通，降低冲突概率。

## 六、Git 常用命令速查表
| 常用命令 | 作用说明 |
| ---- | ---- |
| git status | 查看工作区、暂存区文件修改状态 |
| git add . | 将当前目录全部修改文件加入暂存区 |
| git commit -m "msg" | 暂存区内容提交至本地仓库，备注修改信息 |
| git branch | 查看本地所有分支列表 |
| git checkout -b name | 创建新分支并直接切换至该分支 |
| git pull origin dev | 拉取远程 develop 分支代码并自动合并 |
| git push origin name | 将本地指定分支推送至远程仓库 |
| git log | 查看完整提交历史记录 |
| git reset HEAD file | 撤销单个文件在暂存区的缓存 |
| git checkout -- file | 撤销工作区内单个文件的未暂存修改 |


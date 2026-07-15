# Git Workflow


## Branch


main

正式版本


develop

集成测试版本


feature/xxx

个人开发版本



---

# 开发流程（有问题随时问AI，哪一步不会直接截图问）


1.

从develop创建feature


git checkout develop

git checkout -b feature/student-auth



2.

开发


3.

提交


git add .

git commit -m "feat: add student login"



4.
推送至分支

push


5.

创建PR


feature

↓

develop



6.

Review


7.
合并分支至develop

Merge



---

# 禁止


禁止：

直接push main

直接修改develop

force push


---

# Commit格式


feat:

新增功能


fix:

修复bug


docs:

文档


test:

测试


refactor:

重构



例如：

feat(student-auth): add login session


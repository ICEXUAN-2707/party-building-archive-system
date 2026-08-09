# 任务卡：成员7 第二轮迭代Excel导入闭环

## 任务目标

实现data_admin专用的上传→解析→预览→确认导入→历史→审计，并在回滚契约获批后实现最近一次成功批次回滚。

## 任务背景

解析器已稳定，但当前上传POST为405，预览和历史均为占位；正式写库依赖管理员权限和回滚策略。

## 前置依赖

- `excel_parser_contract.md`
- `admin_permission_contract.md`及成员5最终实现SHA
- 新增`excel_import_contract.md`
- 负责人批准的回滚数据策略

## 允许范围

- `apps/imports/`上传、预览、确认、历史和回滚服务/视图/路由
- imports模板
- 必要且获批的导入快照或变更记录模型/迁移
- 导入与回滚测试
- `docs/04_module_notes/excel_import.md`
- `docs/integration_contracts/excel_import_contract.md`

## 禁止范围

- 不复制`parse_workbook`、角色判断或审计服务。
- 不允许viewer_admin写入或回滚。
- 不在预览阶段写Student/materials业务表。
- 不提交真实Excel、固定绝对路径或共享管理员账号。
- 未冻结回滚模型前不实现临时回滚。
- 不修改学生认证和管理员查询业务。

## 接口契约

冻结：上传类型/大小/随机文件名/哈希；ImportBatch状态；ParseResult映射；预览零写入；确认幂等和事务；Student/ApplicationRecord/Summary/Report更新规则；错误警告落库；审计事件；最近一次可回滚判定和恢复范围。

建议服务边界：

```text
create_import_preview(uploaded_file, operator)
confirm_import(batch_id, operator)
rollback_latest_import(batch_id, operator)
```

具体返回结构必须在契约中冻结后编码。

## 实施建议

### 阶段一：上传与预览

校验`.xlsx`和大小，随机化存储名，计算哈希，创建预览批次，调用`parse_workbook(Path)`并展示全部统计、错误和警告。预览阶段业务表零写入。

### 阶段二：确认导入

重新验证文件哈希和批次状态；整批业务写入使用明确事务。错误行不写入；有效行按学号新增或更新；空申请日期不删除旧值；缺席学生不改变状态；思想汇报替换规则以Spec和契约为准。

### 阶段三：日志与历史

持久化错误/警告、统计和结果，调用成员5审计服务记录upload/confirm，限制原文件下载权限。

### 阶段四：回滚

仅在负责人批准快照/变更模型后实施。只允许最新成功、未回滚批次；二次确认；事务恢复；保留文件、批次、错误警告和审计记录。

## 必须测试

- 非xlsx、超限、同名文件、随机存储名和哈希。
- viewer_admin 403、data_admin允许。
- 预览前后业务表逐项不变。
- ParseResult错误/警告/统计完整展示。
- 重复确认幂等或明确拒绝。
- 新增学生、更新学生、空值保留、错误行保留旧数据、缺席学生不变。
- 思想汇报汇总与明细规则。
- 系统异常事务回滚，无半导入状态。
- 原文件下载权限和OperationLog。
- 获批后测试最近一次回滚、非最新拒绝、重复回滚拒绝及回滚后查询一致。

## 验收标准

- data_admin可完成经确认的导入闭环。
- 预览零业务写入，确认无半成功状态。
- 所有统计与ParseResult语义一致。
- 查询页面能看到导入后的数据。
- 回滚只有在契约和恢复证据完整时标记完成。

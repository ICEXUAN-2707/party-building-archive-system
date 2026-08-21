# Excel合成数据联合验收指南

本指南用于真实Excel到达前，以不含真实个人信息的确定性合成数据验证完整业务链路。验收工具只写入指定的独立输出目录，不得指向正式数据库或正式媒体目录。

## 生成数据集

```powershell
python scripts/generate_acceptance_excel.py `
  --output-dir artifacts/acceptance/dataset-only `
  --student-count 1500 `
  --seed 20260822
```

生成两份九支部可确认主工作簿，以及覆盖非法阶段、非法日期、缺少必填项、未知支部、空表、坏表头和重复学号的负向工作簿。固定种子生成的文件字节一致，不包含真实个人信息。

## 运行完整验收

输出目录必须不存在或为空：

```powershell
python scripts/run_excel_acceptance.py `
  --output-dir artifacts/acceptance/run-1500 `
  --student-count 1500 `
  --seed 20260822
```

执行器使用独立SQLite及媒体目录，完成迁移、九支部初始化、负向上传、第一次上传预览和确认、管理员与学生查询、第二次导入、最近批次回滚、审计和证据核对，并启动新的Python进程复查持久性。

成功后生成`acceptance_report.json`，记录Git SHA、随机种子、输入规模、每批有效/跳过/新建/更新统计、回滚后数据库数量、负向场景、审计、证据SHA-256、耗时和重启复查结果。生成目录已被Git忽略，不得提交Excel、SQLite或媒体证据。

## 报告有效性

报告必须满足：

- `git_sha`等于待发布候选SHA；
- `student_count`约为1500且九个支部均有数据；
- 两次确认导入成功，第二批次成功回滚；
- 管理员及学生查询通过；
- 错误扩展名、超限和冲突批次均被拒绝；
- 原Excel、preview、rollback和SQLite备份证据存在且有哈希；
- `restart_verified`为`true`。

代码、配置或依赖发生任何变更后必须重新运行。

## 真实Excel到达后

合成验收不能替代真实格式核验。真实文件到达后先只上传并检查预览，不直接确认。重点核对工作表名称、第二行表头、总行数、有效/跳过/警告统计和抽样材料字段；若与冻结格式不同，应修正Excel或形成明确规则变更，不得静默猜测列含义。

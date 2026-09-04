# 部署前合成导入压测指南

本门禁只使用生成的合成数据，不允许传入真实 Excel。输出目录必须为空，以避免覆盖既有证据。

```powershell
python scripts/run_deployment_load_test.py `
  --output-dir artifacts/deployment-load/run-1500 `
  --student-count 1500 `
  --seed 20260822
```

执行器会完成两次批量导入、查询、回滚、重启后持久性检查，并运行近同时确认/回滚并发测试。通过条件为：

- 学生数不少于 500，正式候选使用 1500；
- 所有预期成功请求通过，负向请求返回约定的 4xx；
- `http_5xx_errors` 为 0；
- `database_locked_errors` 为 0；
- 并发测试退出码为 0；
- 报告 SHA 与待发布候选 SHA 一致。

证据位于指定输出目录，包括 `deployment_load_test_report.json`、验收报告和并发测试输出。`artifacts/` 不应提交到 Git。

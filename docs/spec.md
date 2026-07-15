# 学院学生材料信息查询系统

## Spec V1.2 冻结更新说明

**版本：** V1.2
**文档状态：** MVP需求与数据模型冻结
**冻结范围：** 产品范围、Excel结构、核心数据模型、模块命名、导入规则、部署方向
**暂缓冻结：** 具体服务器参数、校园网络配置、正式部署命令

---

# 一、本版本新增确认事项

## 1. 数据规模

真实Excel预计包含约1500名学生数据。

系统第一版设计容量应至少满足：

* 约1500名学生；
* 九个党支部；
* 每名学生多条思想汇报记录；
* 约50名管理员；
* 3—4个月一次的周期性数据导入。

当前规模下，SQLite可以满足第一版查询和低频写入需求。

---

## 2. Excel整体结构

真实Excel与测试Excel的内容格式基本一致。

Excel具有以下结构：

1. 一个Excel文件包含多个工作表；
2. 每个工作表原则上对应一个党支部；
3. 表头集中在前两行；
   4.第一行为字段阶段或类别分组；
4. 第二行为正式字段名称；
5. 第三行起为学生数据；
6. 暂未发现需要处理的合并单元格；
7. 每名学生占一行；
8. 思想汇报采用横向多列表示。

解析器不得依赖固定列号，应根据第二行正式表头动态建立列名映射。

---

## 3. 思想汇报列规则

思想汇报列的正式命名规律为：

```text
第X次思想汇报
```

例如：

```text
第一次思想汇报
第二次思想汇报
第三次思想汇报
……
```

解析器必须：

1. 动态识别符合该规律的列；
2. 从列名中解析次数；
3. 不将思想汇报列数量固定为20；
4. 将中文次数转换为正整数；
5. 保存原始列名；
6. 保存思想汇报次数；
7. 保存对应提交日期。

标准化结果示例：

```text
Excel列名：第五次思想汇报
sequence_number：5
submitted_at：2025-12-30
source_column_name：第五次思想汇报
```

---

## 4. 日期规则

Excel标准日期格式为：

```text
YYYY/MM/DD
```

示例：

```text
2025/12/30
```

申请入党时间使用完整日期。

系统还应兼容：

* Excel原生日期单元格；
* `YYYY-MM-DD`；
* `YYYY.MM.DD`；
* `YYYY年M月D日`。

系统内部统一转换为：

```python
datetime.date
```

数据库使用：

```text
DateField
```

学生和管理员页面统一展示为：

```text
2025年12月30日
```

无法解析或缺少年份的日期，不自动猜测。

---

# 二、九个支部冻结值

系统预置以下九个党支部：

| 正式名称  | 内部代码     |
| ----- | -------- |
| 明理党支部 | `MINGLI` |
| 德理党支部 | `DELI`   |
| 惟理党支部 | `WEILI`  |
| 求理党支部 | `QIULI`  |
| 知理党支部 | `ZHILI`  |
| 昭理党支部 | `ZHAOLI` |
| 学理党支部 | `XUELI`  |
| 博理党支部 | `BOLI`   |
| 艺理党支部 | `YILI`   |

初始化操作必须具备幂等性，即重复执行不会重复创建支部。

建议提供：

```bash
python manage.py initialize_branches
```

工作表名称和支部名称原则上应一致。

解析时：

1. 正式支部工作表进入解析流程；
2. 未知工作表默认不自动映射；
3. 说明页、汇总页等非支部工作表应跳过并记录；
4. 工作表名称与数据内部支部信息不一致时应报错。

---

# 三、思想汇报数据模型冻结

## 1. 设计原则

Excel中的思想汇报数据包括两种不同层级：

### 汇总数据

一名学生对应一个思想汇报总篇数。

### 明细数据

一名学生对应多次思想汇报，每次具有：

* 第几次；
* 提交日期；
* Excel来源列；
* 导入批次。

因此，数据库不能把思想汇报总篇数和所有日期塞进同一条明细记录，也不能设计为：

```text
report_1_date
report_2_date
report_3_date
……
```

数据库采用“一条汇总＋多条明细”的标准化结构。

---

## 2. 思想汇报汇总模型

### Django模型

```text
IdeologicalReportSummary
```

### 推荐数据库表

```text
materials_ideologicalreportsummary
```

### 字段

```text
id
student
reported_total_count
calculated_date_count
source_import_batch
created_at
updated_at
```

### 字段含义

#### `student`

关联学生，一名学生最多对应一条思想汇报汇总记录。

使用一对一关系。

#### `reported_total_count`

Excel中“思想汇报总篇数”的原始填报值。

规则：

* 允许为空；
* 非空时必须为非负整数；
* 不由系统计算结果自动覆盖；
* 用于学生页面主要展示。

#### `calculated_date_count`

系统根据有效且去重后的思想汇报日期计算的数量。

规则：

* 必须为非负整数；
* 由导入程序自动计算；
* 用于校验和缺失值补充展示；
* 不冒充Excel原始填报值。

#### `source_import_batch`

记录当前汇总数据来源于哪个导入批次。

---

## 3. 思想汇报明细模型

### Django模型

```text
IdeologicalReport
```

### 推荐数据库表

```text
materials_ideologicalreport
```

### 字段

```text
id
student
sequence_number
submitted_at
source_column_name
import_batch
is_active
created_at
```

### 字段含义

#### `student`

关联学生。

一名学生可以对应多条思想汇报记录。

#### `sequence_number`

记录第几次思想汇报。

例如：

```text
第一次思想汇报 → 1
第十三次思想汇报 → 13
```

必须为正整数。

#### `submitted_at`

该次思想汇报的提交日期。

使用Django `DateField`。

#### `source_column_name`

保存Excel原始列名，例如：

```text
第五次思想汇报
```

用于数据核验和问题追溯。

#### `import_batch`

记录该条明细来源于哪个导入批次。

#### `is_active`

用于标识该条记录当前是否有效，并支持导入替换和回滚。

---

## 4. 思想汇报约束

系统必须保证：

1. 同一学生不能存在两个相同次数的有效记录；
2. 同一学生同一日期重复出现时产生警告；
3. 重复日期只写入一次；
4. 页面按照`sequence_number`升序展示；
5. 不因日期排序自动改变思想汇报次数；
6. 次数顺序与日期顺序不一致时产生警告；
7. 本次导入成功后，替换该学生原有思想汇报明细；
8. 错误行不得删除或改变该学生已有记录。

建议数据库唯一约束为：

```text
student + sequence_number + is_active
```

实际实现中，也可以通过部分唯一约束或业务校验保证当前有效记录唯一。

---

# 四、思想汇报总篇数展示规则

系统同时保留：

| 数据概念       | 字段或来源                   |
| ---------- | ----------------------- |
| Excel填报总篇数 | `reported_total_count`  |
| 系统识别日期数量   | `calculated_date_count` |
| 页面展示总篇数    | 根据以下规则选择                |

页面逻辑：

```text
reported_total_count不为空
→ 展示reported_total_count

reported_total_count为空
→ 展示calculated_date_count
→ 标记“根据已记录日期计算”
```

例如：

```text
思想汇报总篇数：5篇
```

当使用系统计算值时，管理员页面应补充：

```text
统计来源：系统根据提交日期计算
```

学生端可以采用较轻量的提示：

```text
根据当前已记录提交时间统计
```

---

## 总篇数与日期数不一致

例如：

```text
Excel填报总篇数：8
有效日期数量：7
```

处理方式：

1. 产生警告；
2. 允许导入；
3. 学生页面展示8篇；
4. 页面只展示7条实际日期；
5. 不自动补造第8条日期；
6. 不把7写回Excel填报总篇数；
7. 管理员导入预览显示不一致情况。

警告代码建议为：

```text
REPORT_COUNT_MISMATCH
```

---

# 五、Excel解析规则冻结

## 1. 表头识别

解析器默认：

```text
第1行：字段分组说明
第2行：正式字段名称
第3行起：学生数据
```

实现时不得仅依赖固定行号，应：

1. 优先检查前两行；
2. 在前两行中查找“学号”“姓名”“发展阶段”等核心字段；
3. 找到正式字段行后再建立映射；
4. 无法确定正式表头时，该工作表解析失败；
5. 不自动把普通学生数据行识别为表头。

---

## 2. 列识别

必须基于正式表头建立：

```text
字段名 → Excel列索引
```

禁止通过固定列号读取字段。

需要识别：

```text
学号
姓名
发展阶段
职务
申请入党时间
思想汇报总篇数
第X次思想汇报
```

“思想汇报总篇数”允许为空或个别工作表缺失。

若列存在但单元格为空：

* 原始填报值保存为空；
* 系统根据日期计算数量。

若整个工作表缺少该列：

* 不阻止解析；
* `reported_total_count = None`；
* `calculated_date_count`正常计算；
* 记录工作表级警告。

建议警告代码：

```text
REPORT_TOTAL_COLUMN_MISSING
```

---

## 3. 多工作表处理

解析器需要逐工作表处理。

每个工作表的解析结果包括：

```text
sheet_name
branch_code
valid_rows
error_rows
warning_rows
summary
```

整份Excel解析结果还需要包含全局汇总。

某一个工作表解析失败时：

* 不应导致其他有效工作表完全无法预览；
* 该工作表记为失败；
* 其学生数据不进入有效行；
* 导入预览应明确提示失败工作表。

是否允许跳过失败工作表后继续导入其他支部，第一版暂定允许，但确认按钮必须明确展示跳过的工作表和学生数量。

---

## 4. 行错位检测

测试Excel中已经发现可能存在部分数据行与正式表头错位的问题。

系统需要检测：

* 正式姓名列为空，但相邻列出现疑似姓名；
* 发展阶段列值不合法，但相邻列出现合法阶段；
* 性别、民族、发展阶段等字段明显整体偏移；
* 一行字段类型与表头大范围不匹配。

发生疑似错位时：

* 不自动移动单元格；
* 不猜测正确位置；
* 整行跳过；
* 展示Excel行号；
* 提示人工修正Excel。

错误代码冻结为：

```text
ROW_COLUMN_SHIFT_SUSPECTED
```

---

# 六、核心数据模型V1.2

## 1. `PartyBranch`

```text
id
name
code
is_active
created_at
updated_at
```

---

## 2. `Student`

```text
id
name
student_number
branch
development_stage
position
status
source_import_batch
created_at
updated_at
```

说明：

* 思想汇报总篇数从学生模型中移除；
* 学生模型只保存学生身份和当前状态；
* 学号在系统内全局唯一；
* 学号不作为数据库主键，数据库仍使用自动生成的`id`；
* 学生登录使用姓名＋学号联合校验；
* 同一学号对应不同姓名视为数据冲突。

---

## 3. `ApplicationRecord`

```text
id
student
applied_at
source_import_batch
created_at
updated_at
```

每名学生最多一条。

---

## 4. `IdeologicalReportSummary`

```text
id
student
reported_total_count
calculated_date_count
source_import_batch
created_at
updated_at
```

每名学生最多一条。

---

## 5. `IdeologicalReport`

```text
id
student
sequence_number
submitted_at
source_column_name
import_batch
is_active
created_at
```

每名学生可以有多条。

---

## 6. `AdminUser`

```text
id
username
password
display_name
role
is_active
last_login
created_at
```

角色：

```text
viewer_admin
data_admin
```

---

## 7. `ImportBatch`

```text
id
batch_label
original_filename
stored_file
file_hash
imported_by
imported_at
status
total_sheets
success_sheets
failed_sheets
total_rows
success_rows
skipped_rows
warning_rows
created_students
updated_students
created_reports
updated_applications
count_mismatch_rows
unknown_branch_rows
invalid_stage_rows
column_shift_rows
rolled_back_at
rolled_back_by
```

批次状态：

```text
previewed
success
failed
rolled_back
```

---

## 8. `ImportErrorRecord`

```text
id
import_batch
sheet_name
excel_row_number
student_name
student_number
field_name
error_code
error_message
created_at
```

新增`sheet_name`，用于定位多工作表中的错误。

---

## 9. `ImportWarningRecord`

```text
id
import_batch
sheet_name
excel_row_number
student_name
student_number
warning_code
warning_message
source_value
parsed_value
created_at
```

---

## 10. `OperationLog`

```text
id
operator
operator_role
action
target_type
target_id
description
ip_address
created_at
```

---

# 七、页面展示调整

## 1. 学生个人页

展示：

* 姓名；
* 学号；
* 所属支部；
* 发展阶段；
* 申请入党时间；
* 思想汇报总篇数；
* 全部思想汇报记录；
* 最近更新时间。

思想汇报记录示例：

```text
第1次思想汇报　2024年12月28日
第2次思想汇报　2025年3月30日
第3次思想汇报　2025年6月30日
```

页面按照次数升序，而非仅按照日期升序。

---

## 2. 管理员详情页

除学生端信息外，可以展示：

* Excel填报总篇数；
* 系统计算日期数；
* 页面当前采用的统计来源；
* 数据来源批次；
* 最近导入时间。

---

## 3. 导入预览页

新增展示：

* Excel工作表总数；
* 成功识别工作表数；
* 失败工作表数；
* 各工作表对应支部；
* 缺少总篇数列的工作表；
* 疑似列错位行数；
* 思想汇报次数与日期顺序异常数量。

新增错误或警告代码：

```text
ROW_COLUMN_SHIFT_SUSPECTED
REPORT_TOTAL_COLUMN_MISSING
REPORT_COUNT_MISMATCH
REPORT_DATE_SEQUENCE_INCONSISTENT
UNKNOWN_SHEET
HEADER_NOT_FOUND
```

---

# 八、技术栈更新

## 1. 应用技术栈

```text
Python 3.12
Django 5.x
Django Template
Bootstrap 5
openpyxl
SQLite
Git
GitHub
```

## 2. 部署方向

正式部署方向冻结为：

> Docker容器化＋校园内网部署。

可能的部署结构为：

```text
校园内网浏览器
→ 宿主机内网IP与端口
→ Docker Compose
→ Web容器
→ Django应用
→ SQLite持久化文件
```

后续可以根据实际环境增加：

```text
Nginx容器
```

最终可能形成：

```text
校园内网浏览器
→ Nginx
→ Django Web容器
→ SQLite持久化卷
```

---

# 九、Docker部署原则

本版本只冻结部署原则，不冻结具体机器参数。

## 1. 可迁移性

部署不能依赖某一名成员电脑上的：

* 绝对路径；
* Python全局环境；
* IDE设置；
* 手工安装的依赖；
* 个人账号；
* 临时文件。

换一台符合条件的电脑后，应能够依据操作指南重新部署。

---

## 2. 需要纳入项目的部署文件

项目后续应包含：

```text
Dockerfile
compose.yaml
.dockerignore
.env.example
docs/deployment_guide.md
docs/backup_restore_guide.md
scripts/
```

不得提交：

```text
.env
真实密码
真实学生Excel
正式db.sqlite3
备份数据库
```

---

## 3. SQLite持久化

SQLite数据库不能只存在于容器内部临时文件系统。

必须使用：

* Docker命名卷；或
* 宿主机绑定目录。

需要持久化：

```text
SQLite数据库
原始Excel文件
上传文件
备份文件
必要日志
```

删除或重建Web容器时，正式数据不得随之消失。

---

## 4. 单机部署定位

第一版Docker部署定位为：

> 一台校园内网固定主机上的单机部署。

暂不设计：

* 多服务器集群；
* 容器编排平台；
* Kubernetes；
* Redis；
* Celery；
* 高可用数据库；
* 多实例Django并行写入。

SQLite和多Web实例组合可能产生写入锁和一致性问题，因此第一版只运行一个主要Web应用实例。

---

# 十、部署操作指南目标

后续部署阶段必须生成一份可以交接的操作指南。

指南目标是：

> 换一台符合要求的电脑后，具备基础计算机操作能力的项目成员可以按照文档重新启动系统。

操作指南至少包含：

1. 适用的操作系统；
2. 硬件和磁盘要求；
3. Docker安装；
4. 获取GitHub代码；
5. 配置环境变量；
6. 首次构建镜像；
7. 启动容器；
8. 执行数据库迁移；
9. 初始化九个支部；
10. 创建首个管理员；
11. 导入测试数据；
12. 校园内网访问方式；
13. 查看运行状态；
14. 查看日志；
15. 停止和重启；
16. 更新代码；
17. 数据库备份；
18. 原始Excel备份；
19. 恢复数据；
20. 更换部署电脑；
21. 常见故障排查；
22. 紧急回退。

建议最终形成两个文档：

```text
docs/deployment_guide.md
docs/backup_restore_guide.md
```

部署指南将在系统功能稳定后推进，不作为当前Codex项目骨架的完整交付要求。

---

# 十一、开发阶段的Docker范围

## 项目骨架阶段必须做到

Codex搭建项目骨架时应：

* 保留Docker部署目录位置；
* 使用环境变量管理配置；
* 避免宿主机绝对路径；
* 统一静态文件、媒体文件和数据库位置；
* 提供`.env.example`；
* 在README中说明未来采用Docker部署。

## 项目骨架阶段暂不强制做到

* 完整生产Dockerfile；
* 完整Nginx配置；
* 校园网端口开放；
* 自动HTTPS；
* 宿主机自启动；
* 正式备份脚本；
* 正式部署演练。

原因是应用模型和文件路径仍可能在业务开发阶段调整。

---

# 十二、备份规则

虽然业务数据约3—4个月更新一次，但备份不能只按更新周期执行。

## 1. 导入前

正式导入前自动或人工备份：

```text
SQLite数据库
当前原始Excel目录索引
关键配置
```

## 2. 导入后

正式导入成功后再次备份。

## 3. 周期备份

系统正式运行期间，建议至少每周备份一次。

## 4. 保存数量

第一版至少保留：

* 最近5个导入批次的原始Excel；
* 最近5次导入前后的数据库备份；
* 当前有效数据库；
* 最近一次可验证恢复的完整备份。

## 5. 备份位置

备份文件不能只存放在应用容器内部。

建议至少保存在：

* 宿主机持久化目录；
* 学院授权的另一个存储位置。

是否需要离线或异机备份，在部署阶段结合学院条件确认。

---

# 十三、页面视觉规范

页面风格冻结为：

> 简约、年轻、清晰、轻量，符合高校学生使用习惯，并以搜索与信息查询为核心。

设计要求：

* 留白充足；
* 颜色克制；
* 卡片层级清晰；
* 字体清楚；
* 主操作突出；
* 避免传统复杂政务后台风格；
* 避免大量高饱和色按钮；
* 避免无意义动画；
* 保证电脑端主要体验。

“丝滑交互”主要通过以下方式实现：

* 表单提交加载状态；
* 搜索条件保留；
* 页面反馈及时；
* 导入步骤清晰；
* 错误定位明确；
* 高风险操作二次确认；
* 页面布局稳定；
* 不因数据为空出现明显跳动。

第一版不为动画效果引入Vue或React。

---

# 十四、待确认事项更新

## 已确认

* 真实数据约1500条；
* Excel与测试文件基本一致；
* 表头集中于前两行；
* 第二行为正式表头；
* 思想汇报列规律为“第X次思想汇报”；
* Excel包含多个工作表；
* 暂无合并单元格；
* 职务无特殊格式；
* 申请入党时间为完整日期；
* SQLite作为第一版数据库；
* 数据约3—4个月更新；
* 九个支部名称无误；
* 日期规则无误；
* 页面采用简约高校年轻风格；
* 正式部署采用Docker化校园内网方向。

## 仍待部署阶段确认

* 最终部署电脑或服务器；
* 宿主机操作系统；
* 校园网固定IP或主机名；
* 开放端口；
* 是否增加Nginx；
* 是否使用HTTPS；
* Docker数据目录；
* 自动启动方式；
* 备份目标位置；
* 学院运维负责人；
* 设备更换和交接流程。

以上事项不阻止当前项目骨架与业务模块开发。

---

# 十五、V1.2冻结结论

V1.2冻结以下内容：

1. MVP范围；
2. 三类用户权限；
3. 九个支部；
4. Excel多工作表结构；
5. 前两行表头结构；
6. `第X次思想汇报`列规则；
7. 日期标准；
8. 思想汇报汇总与明细双层模型；
9. 思想汇报次数字段；
10. Excel填报值与系统计算值分离；
11. 行错位检测；
12. 错误行整行跳过；
13. 有效学生局部覆盖；
14. 最近一次批次回滚；
15. SQLite数据库；
16. Django单体架构；
17. Docker化校园内网部署方向；
18. 可迁移部署与操作指南要求；
19. 简约高校年轻视觉风格；
20. 七人功能闭环分工方式。

后续业务规则变更必须更新Spec版本，并同步更新：

```text
docs/data_dictionary.md
docs/module_interfaces.md
docs/excel_mapping.md
docs/error_codes.md
docs/test_cases.md
```

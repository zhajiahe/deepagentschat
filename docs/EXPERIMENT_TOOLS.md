# Experiment Tools 使用指南

## 📋 概述

`experiment_tools` 是一套强大的数据分析工具集，专为 AI Agent 设计，提供文件读写、URL 读取、SQL 查询和数据统计等功能。

## 🎯 设计理念

**"Agent 拥有完整的 Linux Shell 权限"**

- 通过 `shell_exec` 工具调用 Python 脚本
- 无需学习复杂的 API，直接使用命令行
- 支持管道操作和复杂工作流
- 所有操作在用户隔离的工作目录中执行

## 📦 工具位置

所有工具脚本位于: `/tmp/user_files/.tools/`

```
/tmp/user_files/.tools/
├── files/              # 文件读写工具
│   ├── read_file.py    # 文件读取
│   └── read_url.py     # URL 读取
├── query/              # 数据查询工具
│   └── data_query.py   # SQL 查询
└── statistics/         # 数据统计工具
    ├── describe.py     # 描述性统计
    ├── head.py         # 数据预览
    └── unique.py       # 唯一值分析
```

## 🔧 工具详解

### 1. 文件读取工具

#### read_file.py - 智能文件读取

```bash
python /tmp/user_files/.tools/files/read_file.py <filename>
```

**功能特性**:
- ✅ 智能编码检测 (utf-8, gbk, gb2312, latin-1)
- ✅ 大文件警告 (>10MB)
- ✅ 自动截断显示 (2000 字符)
- ✅ 文件存在性检查

**使用示例**:
```bash
# 读取文本文件
python /tmp/user_files/.tools/files/read_file.py config.json

# 读取日志文件
python /tmp/user_files/.tools/files/read_file.py app.log
```

#### read_url.py - URL 内容读取

```bash
python /tmp/user_files/.tools/files/read_url.py <url> [options]
```

**功能特性**:
- ✅ 支持 HTTP/HTTPS 协议
- ✅ 自动编码检测
- ✅ 内容类型识别 (文本/二进制)
- ✅ 大小限制保护 (默认 10MB)
- ✅ 超时控制 (默认 30 秒)

**选项参数**:
- `--timeout <seconds>`: 请求超时时间
- `--max-size <bytes>`: 最大内容大小
- `--max-display <chars>`: 最大显示字符数
- `--save <file>`: 保存内容到文件
- `--headers "<Key>: <Value>"`: 添加 HTTP 请求头
- `--show-headers`: 显示响应头信息
- `--no-verify-ssl`: 跳过 SSL 证书验证

**使用示例**:
```bash
# 读取 JSON API
python /tmp/user_files/.tools/files/read_url.py https://api.github.com/repos/python/cpython

# 下载文件
python /tmp/user_files/.tools/files/read_url.py https://example.com/data.csv --save data.csv

# 自定义请求头
python /tmp/user_files/.tools/files/read_url.py https://api.example.com/data \
  --headers "Authorization: Bearer token" \
  --timeout 60
```

### 2. 数据查询工具

#### data_query.py - SQL 查询引擎

```bash
python /tmp/user_files/.tools/query/data_query.py "SELECT * FROM 'data.csv'"
```

**功能特性**:
- ✅ 基于 DuckDB，支持完整 SQL 语法
- ✅ 支持格式: CSV, JSON, Parquet, Excel
- ✅ 文件可直接作为表名
- ✅ 内存限制保护 (2GB)
- ✅ 智能结果显示 (自动截断大结果)

**支持的 SQL 操作**:
- SELECT, WHERE, GROUP BY, ORDER BY
- JOIN (INNER, LEFT, RIGHT, OUTER)
- 聚合函数 (COUNT, SUM, AVG, MIN, MAX)
- 窗口函数
- COPY TO (导出结果)

**使用示例**:
```bash
# 基本查询
python /tmp/user_files/.tools/query/data_query.py "SELECT * FROM 'sales.csv' LIMIT 10"

# 聚合分析
python /tmp/user_files/.tools/query/data_query.py \
  "SELECT product, SUM(amount) as total
   FROM 'sales.csv'
   GROUP BY product
   ORDER BY total DESC"

# 多表关联
python /tmp/user_files/.tools/query/data_query.py \
  "SELECT a.*, b.category
   FROM 'orders.csv' a
   JOIN 'products.json' b ON a.product_id = b.id"

# 导出结果
python /tmp/user_files/.tools/query/data_query.py \
  "COPY (SELECT * FROM 'data.csv' WHERE amount > 100) TO 'filtered.csv'"

# 格式转换
python /tmp/user_files/.tools/query/data_query.py \
  "COPY (SELECT * FROM 'data.xlsx') TO 'data.parquet'"
```

### 3. 数据统计工具

#### describe.py - 描述性统计

```bash
python /tmp/user_files/.tools/statistics/describe.py <file> [--format auto]
```

**功能特性**:
- ✅ 显示每列的统计信息
- ✅ count, unique, mean, std, min, max, q25, q50, q75
- ✅ 自动格式检测

**使用示例**:
```bash
# 自动检测格式
python /tmp/user_files/.tools/statistics/describe.py data.csv

# 指定格式
python /tmp/user_files/.tools/statistics/describe.py data.xlsx --format xlsx
```

#### head.py - 数据预览

```bash
python /tmp/user_files/.tools/statistics/head.py <file> [--limit 10]
```

**功能特性**:
- ✅ 显示数据前 N 行
- ✅ 快速了解数据结构
- ✅ 支持多种格式

**使用示例**:
```bash
# 显示前 10 行
python /tmp/user_files/.tools/statistics/head.py data.csv

# 显示前 20 行
python /tmp/user_files/.tools/statistics/head.py data.csv --limit 20
```

#### unique.py - 唯一值分析

```bash
python /tmp/user_files/.tools/statistics/unique.py <file> [--topk 10]
```

**功能特性**:
- ✅ 显示每列的 Top K 最常见值
- ✅ 显示每个值的出现次数
- ✅ 用于数据质量检查

**使用示例**:
```bash
# 显示 Top 10 值
python /tmp/user_files/.tools/statistics/unique.py data.csv

# 显示 Top 5 值
python /tmp/user_files/.tools/statistics/unique.py data.csv --topk 5
```

## 📚 推荐工作流

### 数据探索流程

```bash
# 1. 快速预览数据结构
python /tmp/user_files/.tools/statistics/head.py data.csv --limit 5

# 2. 查看统计摘要
python /tmp/user_files/.tools/statistics/describe.py data.csv

# 3. 检查数据质量
python /tmp/user_files/.tools/statistics/unique.py data.csv

# 4. 执行分析查询
python /tmp/user_files/.tools/query/data_query.py \
  "SELECT category, COUNT(*) as count, AVG(amount) as avg_amount
   FROM 'data.csv'
   GROUP BY category"
```

### 数据清洗流程

```bash
# 1. 检查缺失值
python /tmp/user_files/.tools/query/data_query.py \
  "SELECT COUNT(*) - COUNT(column_name) as missing_count
   FROM 'data.csv'"

# 2. 过滤异常值
python /tmp/user_files/.tools/query/data_query.py \
  "COPY (SELECT * FROM 'data.csv' WHERE amount BETWEEN 0 AND 10000)
   TO 'cleaned.csv'"

# 3. 去重
python /tmp/user_files/.tools/query/data_query.py \
  "COPY (SELECT DISTINCT * FROM 'data.csv') TO 'deduped.csv'"
```

### 数据转换流程

```bash
# Excel → CSV
python /tmp/user_files/.tools/query/data_query.py \
  "COPY (SELECT * FROM 'data.xlsx') TO 'data.csv'"

# CSV → Parquet (更高性能)
python /tmp/user_files/.tools/query/data_query.py \
  "COPY (SELECT * FROM 'data.csv') TO 'data.parquet'"

# 多文件合并
python /tmp/user_files/.tools/query/data_query.py \
  "COPY (
    SELECT * FROM 'file1.csv'
    UNION ALL
    SELECT * FROM 'file2.csv'
  ) TO 'merged.csv'"
```

## 🔥 高级技巧

### 1. 管道操作

```bash
# 组合 Linux 工具和数据分析工具
cat access.log | grep "ERROR" | \
  python /tmp/user_files/.tools/query/data_query.py \
  "SELECT timestamp, COUNT(*) FROM stdin GROUP BY timestamp"
```

### 2. 复杂 SQL 查询

```bash
# 窗口函数
python /tmp/user_files/.tools/query/data_query.py \
  "SELECT *,
   ROW_NUMBER() OVER (PARTITION BY category ORDER BY amount DESC) as rank
   FROM 'sales.csv'"

# CTE (公共表表达式)
python /tmp/user_files/.tools/query/data_query.py \
  "WITH top_products AS (
     SELECT product, SUM(amount) as total
     FROM 'sales.csv'
     GROUP BY product
     ORDER BY total DESC
     LIMIT 10
   )
   SELECT * FROM top_products"
```

### 3. 数据可视化准备

```bash
# 生成时间序列数据
python /tmp/user_files/.tools/query/data_query.py \
  "SELECT DATE_TRUNC('day', timestamp) as date,
   COUNT(*) as count,
   SUM(amount) as revenue
   FROM 'sales.csv'
   GROUP BY date
   ORDER BY date" > timeseries.csv
```

## ⚠️ 注意事项

### 性能优化

1. **大文件处理**:
   - 优先使用 Parquet 格式 (列式存储，压缩率高)
   - 使用 SQL 查询而非完整读取
   - 添加 LIMIT 限制结果数量

2. **内存管理**:
   - DuckDB 默认内存限制 2GB
   - 大结果集使用 COPY TO 导出
   - 避免 SELECT * 在大表上

3. **查询优化**:
   - 使用 WHERE 过滤数据
   - 避免不必要的 JOIN
   - 利用索引 (DuckDB 自动优化)

### 安全性

1. **路径安全**:
   - 所有操作限制在用户工作目录
   - 自动防止路径遍历攻击 (../)

2. **资源限制**:
   - URL 读取大小限制 (10MB)
   - SQL 查询内存限制 (2GB)
   - 超时控制 (30 秒)

### 错误处理

1. **文件不存在**:
   ```bash
   ❌ 文件不存在: data.csv
   ```

2. **SQL 语法错误**:
   ```bash
   ❌ SQL 语法错误: Parser Error: syntax error at or near "SELEC"
   ```

3. **内存不足**:
   ```bash
   ❌ 内存不足，建议:
     1. 在查询末尾添加 LIMIT
     2. 使用 COPY TO 导出: COPY (...) TO 'output.csv'
   ```

## 🧪 测试验证

运行测试脚本验证工具是否正常工作:

```bash
# 简化测试 (推荐)
python test_experiment_tools_simple.py

# 完整测试 (需要 LangChain)
python test_experiment_tools.py
```

## 📖 Agent 使用示例

### 在 Agent 中使用

```python
from app.tools import shell_exec, UserContext
from langchain.tools import ToolRuntime

# 创建 runtime
runtime = ToolRuntime(context=UserContext(user_id="user-123"))

# 数据预览
result = await shell_exec.ainvoke({
    "command": "python /tmp/user_files/.tools/statistics/head.py sales.csv",
    "runtime": runtime,
})

# SQL 查询
result = await shell_exec.ainvoke({
    "command": "python /tmp/user_files/.tools/query/data_query.py \"SELECT * FROM 'sales.csv' LIMIT 10\"",
    "runtime": runtime,
})
```

### Agent Prompt 建议

在 Agent 的系统提示词中添加:

```markdown
## 数据分析能力

你拥有强大的数据分析工具，位于 `/tmp/user_files/.tools/`:

### 推荐工作流
1. **数据探索**: 使用 `head.py` 和 `describe.py` 了解数据
2. **数据分析**: 使用 `data_query.py` 执行 SQL 查询
3. **数据质量**: 使用 `unique.py` 检查异常值

### 最佳实践
- 大文件优先使用 SQL 查询
- 复杂分析使用 DuckDB 的高级 SQL 功能
- 结果导出使用 COPY TO 命令
```

## 🔗 相关文档

- [SYSTEM.md](../app/experiment_tools/SYSTEM.md) - 系统角色与功能说明
- [INTEGRATION_DESIGN.md](../app/experiment_tools/INTEGRATION_DESIGN.md) - 集成设计文档
- [tools.py](../app/tools.py) - 工具实现源码

## 📝 更新日志

### v1.0.0 (2025-11-22)
- ✅ 初始版本发布
- ✅ 集成文件读写工具
- ✅ 集成 SQL 查询工具
- ✅ 集成数据统计工具
- ✅ 添加完整测试套件
- ✅ 添加使用文档

---

**维护者**: AI Assistant
**最后更新**: 2025-11-22

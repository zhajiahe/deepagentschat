# Docker 工具系统常见问题

## ❓ Docker tools 和 files.py 的关系

### 简短回答

**是的，files.py 完全兼容！** 使用 Docker tools 不影响文件上传、浏览等功能。

### 详细说明

#### 1. 文件存储架构

```
/tmp/user_files/
├── {user_id_1}/          # 用户1的文件
│   ├── data.csv
│   ├── script.py
│   └── .tools/           # 自动部署的工具（仅 tools.py）
├── {user_id_2}/          # 用户2的文件
│   ├── report.xlsx
│   └── analysis.py
└── public/               # 公共文件（可选）
```

#### 2. 工作流程

```
用户操作流程:

1. 上传文件 (files.py)
   ↓
   POST /api/v1/files/upload
   ↓
   文件保存到 /tmp/user_files/{user_id}/data.csv

2. 浏览文件 (files.py)
   ↓
   GET /api/v1/files/list
   ↓
   返回 /tmp/user_files/{user_id}/ 下的文件列表

3. 执行命令 (tools_docker.py)
   ↓
   Agent 调用 shell_exec("python analysis.py")
   ↓
   Docker 容器启动，挂载 /tmp/user_files/{user_id}/ 到容器的 /workspace
   ↓
   容器内执行: python /workspace/analysis.py
   ↓
   结果返回给 Agent
```

#### 3. 关键点

##### 3.1 文件存储层（共享）

- **files.py**: 直接操作宿主机文件系统
- **tools_docker.py**: 通过 Docker 挂载访问相同的文件系统

```python
# files.py 上传文件
file_path = /tmp/user_files/{user_id}/data.csv
with open(file_path, "wb") as f:
    f.write(content)

# tools_docker.py 访问文件
# Docker 挂载: /tmp/user_files/{user_id}/ -> /workspace
# 容器内看到: /workspace/data.csv
```

##### 3.2 文件访问方式

| 功能 | files.py | tools_docker.py |
|------|----------|-----------------|
| 上传文件 | ✅ 直接写入宿主机 | ❌ 不负责上传 |
| 下载文件 | ✅ 直接读取宿主机 | ❌ 不负责下载 |
| 浏览文件 | ✅ 列出宿主机文件 | ❌ 不负责浏览 |
| 执行命令 | ❌ 不负责执行 | ✅ 容器内执行 |
| 读取文件内容 | ✅ read_file 工具 | ✅ shell_exec("cat file") |
| 写入文件内容 | ✅ write_file 工具 | ✅ shell_exec("echo > file") |

## 🔄 完整使用示例

### 场景：数据分析工作流

#### 步骤 1: 上传数据文件（使用 files.py）

```bash
# 前端或 API 调用
curl -X POST http://localhost:8000/api/v1/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sales_data.csv"

# 响应
{
  "success": true,
  "data": {
    "filename": "sales_data.csv",
    "path": "sales_data.csv",
    "size": 1024000
  }
}
```

**文件位置**: `/tmp/user_files/{user_id}/sales_data.csv`

#### 步骤 2: 浏览文件（使用 files.py）

```bash
# 列出用户文件
curl -X GET http://localhost:8000/api/v1/files/list \
  -H "Authorization: Bearer $TOKEN"

# 响应
{
  "success": true,
  "data": {
    "files": [
      {
        "filename": "sales_data.csv",
        "size": 1024000,
        "path": "sales_data.csv",
        "is_dir": false
      }
    ],
    "total": 1
  }
}
```

#### 步骤 3: 分析数据（使用 tools_docker.py）

**用户对话**:
```
用户: 分析 sales_data.csv 文件，统计每个产品的销售额
```

**Agent 执行**（使用 Docker tools）:

```python
# Agent 内部调用
result = await shell_exec(
    "python -c \"import pandas as pd; df = pd.read_csv('sales_data.csv'); print(df.groupby('product')['amount'].sum())\"",
    runtime
)
```

**Docker 执行过程**:
```
1. Docker 创建容器
2. 挂载: /tmp/user_files/{user_id}/ -> /workspace (容器内)
3. 容器内执行:
   cd /workspace
   python -c "import pandas as pd; ..."
4. 容器内可以看到: /workspace/sales_data.csv
5. 执行完成，返回结果
6. 容器自动删除
```

#### 步骤 4: 下载结果（使用 files.py）

如果 Agent 生成了新文件：

```python
# Agent 可能执行
await shell_exec(
    "python -c \"import pandas as pd; df = pd.read_csv('sales_data.csv'); df.groupby('product')['amount'].sum().to_csv('result.csv')\"",
    runtime
)
```

**文件生成**: `/tmp/user_files/{user_id}/result.csv`

**用户下载**:
```bash
curl -X GET http://localhost:8000/api/v1/files/download/result.csv \
  -H "Authorization: Bearer $TOKEN" \
  -O result.csv
```

## 🔍 技术细节

### Docker 挂载机制

```python
# tools_docker.py 中的挂载配置
mounts = [
    Mount(
        target="/workspace",           # 容器内路径
        source=str(work_path.absolute()),  # 宿主机路径: /tmp/user_files/{user_id}/
        type="bind",
        read_only=False,  # 允许读写
    )
]
```

**效果**:
- 宿主机: `/tmp/user_files/user-123/data.csv`
- 容器内: `/workspace/data.csv`
- 两者指向同一个文件！

### 文件权限

#### 问题：容器内用户 UID 不匹配

```
容器内用户: UID 1000
宿主机文件: UID 0 (root) 或其他
```

#### 解决方案：

```bash
# 确保文件权限正确
sudo chown -R 1000:1000 /tmp/user_files/
```

或者在 Dockerfile 中使用动态 UID（高级）。

## 📊 对比表格

### files.py vs tools_docker.py

| 功能 | files.py | tools_docker.py | 说明 |
|------|----------|-----------------|------|
| **文件管理** | | | |
| 上传文件 | ✅ | ❌ | files.py 负责 |
| 下载文件 | ✅ | ❌ | files.py 负责 |
| 列出文件 | ✅ | ❌ | files.py 负责 |
| 删除文件 | ✅ | ❌ | files.py 负责 |
| 预览文件 | ✅ | ❌ | files.py 负责 |
| **文件操作** | | | |
| 读取文件内容 | ❌ | ✅ | Agent 工具 |
| 写入文件内容 | ❌ | ✅ | Agent 工具 |
| 执行脚本 | ❌ | ✅ | Agent 工具 |
| 数据分析 | ❌ | ✅ | Agent 工具 |
| **访问方式** | | | |
| API 端点 | ✅ | ❌ | REST API |
| Agent 工具 | ❌ | ✅ | LangChain Tool |
| **隔离性** | | | |
| 用户隔离 | ✅ | ✅ | 都支持 |
| 进程隔离 | ❌ | ✅ | Docker 提供 |
| 资源限制 | ❌ | ✅ | Docker 提供 |

## 🎯 最佳实践

### 1. 文件管理使用 files.py

```python
# ✅ 推荐：使用 files.py API
POST /api/v1/files/upload
GET  /api/v1/files/list
GET  /api/v1/files/download/{filename}
DELETE /api/v1/files/{filename}
```

### 2. 文件处理使用 tools_docker.py

```python
# ✅ 推荐：Agent 使用 Docker tools
await shell_exec("python analysis.py", runtime)
await shell_exec("cat data.csv | grep 'keyword'", runtime)
```

### 3. 不要混淆职责

```python
# ❌ 不推荐：用 Agent 工具上传文件
# 应该使用 files.py API

# ❌ 不推荐：用 files.py 执行复杂分析
# 应该使用 Agent 工具
```

## 🔐 安全考虑

### 1. 路径遍历防护

```python
# files.py 和 tools_docker.py 都有路径验证
# 防止访问用户目录外的文件

# ❌ 会被拒绝
GET /api/v1/files/download/../../etc/passwd
shell_exec("cat ../../etc/passwd", runtime)

# ✅ 只能访问用户目录
GET /api/v1/files/download/data.csv
shell_exec("cat data.csv", runtime)
```

### 2. 文件大小限制

```python
# files.py 可以配置上传大小限制
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB

# tools_docker.py 通过容器资源限制
DOCKER_MEMORY_LIMIT = "512m"
```

## 💡 常见场景

### 场景 1: 数据分析

```
1. 用户上传 CSV (files.py)
2. Agent 分析数据 (tools_docker.py)
3. 生成报告文件 (tools_docker.py)
4. 用户下载报告 (files.py)
```

### 场景 2: 代码执行

```
1. 用户上传 Python 脚本 (files.py)
2. Agent 执行脚本 (tools_docker.py)
3. 查看执行结果 (tools_docker.py)
4. 下载输出文件 (files.py)
```

### 场景 3: 文件转换

```
1. 用户上传 Excel (files.py)
2. Agent 转换为 CSV (tools_docker.py)
3. 用户下载 CSV (files.py)
```

## 📝 总结

### 关键点

1. **files.py 和 tools_docker.py 是互补的**
   - files.py: 文件管理（上传/下载/浏览）
   - tools_docker.py: 文件处理（分析/转换/执行）

2. **共享相同的文件系统**
   - 都操作 `/tmp/user_files/{user_id}/`
   - Docker 通过挂载访问

3. **职责分离**
   - API 层（files.py）: 用户直接交互
   - Agent 层（tools_docker.py）: AI 自动化处理

4. **完全兼容**
   - 使用 Docker tools 不影响 files.py
   - 可以同时使用两者

### 推荐架构

```
用户
  ↓
前端 UI
  ↓
┌─────────────┬─────────────────┐
│  files.py   │  Agent (AI)     │
│  (API)      │  (tools_docker) │
└─────────────┴─────────────────┘
        ↓              ↓
    /tmp/user_files/{user_id}/
    (共享文件系统)
```

---

**结论**: Docker tools 和 files.py 完美配合，提供完整的文件管理和处理能力！

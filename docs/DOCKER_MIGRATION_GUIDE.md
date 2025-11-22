# Docker 工具系统迁移指南

## 📋 概述

本指南说明如何从传统的进程隔离工具系统 (`tools.py`) 迁移到 Docker 容器隔离系统 (`tools_docker.py`)。

## 🔄 代码调整建议

### 1. 统一存储配置（推荐但可选）

为了更好的代码复用，建议使用统一的存储配置模块。

#### 新增文件: `app/core/storage.py`

已创建，包含：
- `STORAGE_ROOT`: 存储根目录
- `get_user_storage_path()`: 获取用户目录
- `sanitize_path()`: 路径安全验证
- `sanitize_filename()`: 文件名清理

#### 需要调整的文件

##### 1.1 `app/tools.py`

**当前代码**:
```python
# 文件存储根目录
STORAGE_ROOT = Path("/tmp/user_files")
PUBLIC_DIR = STORAGE_ROOT / "public"
TOOLS_VENV_DIR = STORAGE_ROOT / ".tools_venv"

def get_work_path(user_id: str | None = None) -> Path:
    # ... 实现
```

**建议修改**:
```python
from app.core.storage import (
    STORAGE_ROOT,
    PUBLIC_DIR,
    TOOLS_VENV_DIR,
    get_work_path,
    sanitize_path,
)

# 移除重复的定义和函数
```

##### 1.2 `app/tools_docker.py`

**当前代码**:
```python
# 文件存储根目录
STORAGE_ROOT = Path("/tmp/user_files")
PUBLIC_DIR = STORAGE_ROOT / "public"

def get_work_path(user_id: str | None = None) -> Path:
    # ... 实现

def sanitize_path(user_id: str | None, filename: str) -> Path:
    # ... 实现
```

**建议修改**:
```python
from app.core.storage import (
    STORAGE_ROOT,
    PUBLIC_DIR,
    get_work_path,
    sanitize_path,
)

# 移除重复的定义和函数
```

##### 1.3 `app/api/files.py`

**当前代码**:
```python
# 文件存储根目录
STORAGE_ROOT = Path("/tmp/user_files")

def get_user_storage_path(user_id: uuid.UUID) -> Path:
    user_path = STORAGE_ROOT / str(user_id)
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path
```

**建议修改**:
```python
from app.core.storage import (
    STORAGE_ROOT,
    get_user_storage_path,
    sanitize_filename,
)

# 移除重复的定义

# 在 upload_file 中使用 sanitize_filename
safe_filename = sanitize_filename(file.filename or "unnamed")
```

### 2. Agent 配置调整

#### 2.1 使用 Docker 版本

在 `app/agent.py` 中：

```python
# 方式 1: 完全替换为 Docker 版本
from app.tools_docker import ALL_TOOLS

# 方式 2: 根据环境变量选择
import os
if os.getenv("USE_DOCKER_TOOLS", "false").lower() == "true":
    from app.tools_docker import ALL_TOOLS
else:
    from app.tools import ALL_TOOLS
```

#### 2.2 混合使用（高级）

```python
from app.tools import (
    write_file as write_file_fast,
    read_file as read_file_fast,
)
from app.tools_docker import (
    shell_exec as shell_exec_safe,
)

# 组合工具列表
ALL_TOOLS = [
    write_file_fast,  # 文件读写使用快速版本
    read_file_fast,
    shell_exec_safe,  # 命令执行使用安全版本
]
```

### 3. 环境变量配置

在 `.env` 文件中添加：

```env
# Docker 工具配置（可选）
USE_DOCKER_TOOLS=false  # 开发环境使用 false，生产环境使用 true
DOCKER_IMAGE=deepagentschat-tools:latest
DOCKER_CPU_LIMIT=1.0
DOCKER_MEMORY_LIMIT=512m
DOCKER_NETWORK_MODE=none
DOCKER_TIMEOUT=30
```

在 `app/core/config.py` 中添加：

```python
class Settings(BaseSettings):
    # ... 现有配置

    # Docker 工具配置
    USE_DOCKER_TOOLS: bool = False
    DOCKER_IMAGE: str = "deepagentschat-tools:latest"
    DOCKER_CPU_LIMIT: float = 1.0
    DOCKER_MEMORY_LIMIT: str = "512m"
    DOCKER_NETWORK_MODE: str = "none"
    DOCKER_TIMEOUT: int = 30
```

### 4. 依赖更新

在 `pyproject.toml` 中添加：

```toml
[project]
dependencies = [
    # ... 现有依赖
    "docker>=7.1.0",  # Docker SDK（可选）
]

[project.optional-dependencies]
docker = [
    "docker>=7.1.0",
]
```

安装：
```bash
# 安装 Docker 支持
uv add docker

# 或作为可选依赖
uv sync --extra docker
```

## 🚀 迁移步骤

### 步骤 1: 准备 Docker 环境

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 重新登录
exit
# 重新登录到服务器

# 3. 验证 Docker
docker --version
docker ps
```

### 步骤 2: 构建工具镜像

```bash
# 构建镜像
bash docker/build-tools.sh

# 验证镜像
docker images | grep deepagentschat-tools

# 测试镜像
docker run --rm deepagentschat-tools:latest python -c "import pandas; print('OK')"
```

### 步骤 3: 安装依赖

```bash
# 安装 Docker SDK
uv add docker
```

### 步骤 4: 代码调整（可选）

```bash
# 1. 统一存储配置（推荐）
# 按照上面的说明修改 tools.py, tools_docker.py, files.py

# 2. 更新 agent.py
# 选择使用 Docker 版本或混合使用
```

### 步骤 5: 配置环境变量

```bash
# 编辑 .env
echo "USE_DOCKER_TOOLS=true" >> .env
echo "DOCKER_IMAGE=deepagentschat-tools:latest" >> .env
```

### 步骤 6: 测试

```bash
# 运行对比测试
python examples/tools_comparison.py

# 启动应用测试
make dev
```

### 步骤 7: 监控和调优

```bash
# 监控容器资源使用
docker stats

# 查看容器日志
docker logs <container_id>

# 根据实际情况调整资源限制
```

## 🔄 回滚方案

如果遇到问题，可以快速回滚：

### 方式 1: 环境变量切换

```bash
# 在 .env 中设置
USE_DOCKER_TOOLS=false
```

### 方式 2: 代码回滚

```python
# 在 app/agent.py 中
from app.tools import ALL_TOOLS  # 使用原版本
```

## ⚠️ 注意事项

### 1. 性能影响

- Docker 版本启动时间增加 1-2 秒
- 适合对安全性要求高的场景
- 不适合对性能要求极高的场景

### 2. 资源要求

- 需要 Docker 环境
- 镜像占用约 500MB 磁盘空间
- 每次执行占用配置的内存限制（默认 512MB）

### 3. 网络访问

- 默认无网络访问（最安全）
- 如需网络访问，设置 `DOCKER_NETWORK_MODE=bridge`
- 注意安全风险

### 4. 文件权限

- 容器内使用 UID 1000
- 确保 `/tmp/user_files` 权限正确：
  ```bash
  sudo chown -R 1000:1000 /tmp/user_files/
  ```

## 📊 迁移检查清单

- [ ] Docker 环境已安装并测试
- [ ] 工具镜像已构建
- [ ] Docker SDK 已安装
- [ ] 环境变量已配置
- [ ] 代码已调整（如果需要）
- [ ] 测试通过
- [ ] 监控已设置
- [ ] 回滚方案已准备

## 🎯 最佳实践

### 开发环境

```python
# 使用快速版本
from app.tools import ALL_TOOLS
```

### 生产环境

```python
# 使用安全版本
from app.tools_docker import ALL_TOOLS
```

### 混合环境

```python
# 根据任务类型选择
import os

if os.getenv("USE_DOCKER_TOOLS", "false").lower() == "true":
    from app.tools_docker import shell_exec
else:
    from app.tools import shell_exec
```

## 📚 相关文档

- [Docker 工具文档](./DOCKER_TOOLS.md)
- [工具系统文档](../app/tools.py)
- [存储配置文档](../app/core/storage.py)

---

**提示**: 迁移是可选的。如果当前系统运行良好，可以继续使用 `tools.py`。Docker 版本主要用于提升安全性。

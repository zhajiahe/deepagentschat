# Docker 容器版工具系统

## 📖 概述

`tools_docker.py` 提供了基于 Docker 容器的工具执行环境，相比传统的进程隔离方式，提供了更强的安全性和资源控制。

## ✨ 主要特性

### 🔒 安全隔离

- **进程隔离**: 每次执行在独立容器中运行
- **文件系统隔离**: 只能访问挂载的用户目录
- **网络隔离**: 默认无网络访问（可配置）
- **权限限制**: 非 root 用户执行，移除所有 capabilities
- **禁止提权**: 使用 `no-new-privileges` 安全选项

### 📊 资源控制

- **CPU 限制**: 默认限制为 1 核
- **内存限制**: 默认限制为 512MB
- **超时控制**: 防止长时间运行的任务
- **自动清理**: 执行完成后自动删除容器

### 🛡️ 防护措施

- **路径遍历防护**: 防止访问用户目录外的文件
- **输出截断**: 防止超大输出占用内存
- **错误隔离**: 容器崩溃不影响主应用

## 🏗️ 架构对比

### 传统方式 (tools.py)

```
FastAPI App
    ↓
subprocess
    ↓
Host OS Process
    ├── 虚拟环境隔离
    ├── 文件系统访问限制
    └── 进程超时控制
```

**优点**: 启动快，资源占用少
**缺点**: 隔离性较弱，安全风险较高

### Docker 方式 (tools_docker.py)

```
FastAPI App
    ↓
Docker Client
    ↓
Docker Container (per execution)
    ├── 完全隔离的文件系统
    ├── 独立的网络栈
    ├── 资源限制 (CPU/内存)
    └── 安全配置 (非root/无capabilities)
```

**优点**: 强隔离，高安全性，资源可控
**缺点**: 启动慢（~1-2秒），需要 Docker 环境

## 🚀 快速开始

### 1. 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 重新登录以应用组权限
```

### 2. 安装 Python Docker SDK

```bash
uv add docker
# 或
pip install docker
```

### 3. 构建工具镜像

```bash
cd /path/to/project
docker build -t deepagentschat-tools:latest -f docker/Dockerfile.tools .
```

### 4. 配置环境变量

在 `.env` 文件中添加：

```env
# Docker 工具配置
DOCKER_IMAGE=deepagentschat-tools:latest
DOCKER_CPU_LIMIT=1.0
DOCKER_MEMORY_LIMIT=512m
DOCKER_NETWORK_MODE=none
DOCKER_TIMEOUT=30
```

### 5. 使用 Docker 版工具

在 `app/agent.py` 中：

```python
# 替换
from app.tools import ALL_TOOLS

# 为
from app.tools_docker import ALL_TOOLS
```

## 📝 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOCKER_IMAGE` | `deepagentschat-tools:latest` | 工具容器镜像名称 |
| `DOCKER_CPU_LIMIT` | `1.0` | CPU 限制（核数） |
| `DOCKER_MEMORY_LIMIT` | `512m` | 内存限制 |
| `DOCKER_NETWORK_MODE` | `none` | 网络模式 |
| `DOCKER_TIMEOUT` | `30` | 执行超时（秒） |

### 网络模式

- **none** (默认): 无网络访问，最安全
- **bridge**: 允许访问外部网络
- **host**: 使用宿主机网络（不推荐）

### 资源限制建议

| 场景 | CPU | 内存 | 说明 |
|------|-----|------|------|
| 轻量级任务 | 0.5 | 256m | 简单脚本、文本处理 |
| 标准任务 | 1.0 | 512m | 数据分析、SQL 查询 |
| 重型任务 | 2.0 | 1g | 大数据处理、机器学习 |

## 🔧 自定义镜像

### 添加额外的 Python 包

编辑 `docker/Dockerfile.tools`:

```dockerfile
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    # 添加你需要的包
    scikit-learn \
    tensorflow \
    pytorch
```

### 添加系统工具

```dockerfile
RUN apt-get update && apt-get install -y \
    # 添加你需要的工具
    imagemagick \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

### 重新构建

```bash
docker build -t deepagentschat-tools:latest -f docker/Dockerfile.tools .
```

## 🧪 测试

### 基本测试

```python
import asyncio
from app.tools_docker import shell_exec, UserContext, ToolRuntime

async def test_basic():
    runtime = ToolRuntime(context=UserContext(user_id="test-user"))

    # 测试基本命令
    result = await shell_exec("echo 'Hello from Docker!'", runtime)
    print(result)

    # 测试 Python
    result = await shell_exec("python -c 'print(2 + 2)'", runtime)
    print(result)

    # 测试数据分析
    result = await shell_exec("python -c 'import pandas; print(pandas.__version__)'", runtime)
    print(result)

asyncio.run(test_basic())
```

### 性能测试

```python
import time
import asyncio
from app.tools_docker import shell_exec, UserContext, ToolRuntime

async def benchmark():
    runtime = ToolRuntime(context=UserContext(user_id="test-user"))

    # 测试启动时间
    start = time.time()
    await shell_exec("echo 'test'", runtime)
    print(f"First run: {time.time() - start:.2f}s")

    # 测试后续执行
    start = time.time()
    for _ in range(10):
        await shell_exec("echo 'test'", runtime)
    print(f"10 runs: {time.time() - start:.2f}s")

asyncio.run(benchmark())
```

## 🔍 故障排查

### 问题 1: Docker 连接失败

```
RuntimeError: Failed to connect to Docker: ...
```

**解决方案**:
1. 确认 Docker 服务正在运行: `sudo systemctl status docker`
2. 确认当前用户在 docker 组: `groups | grep docker`
3. 重新登录以应用组权限

### 问题 2: 镜像不存在

```
RuntimeError: Docker image deepagentschat-tools:latest not found
```

**解决方案**:
```bash
docker build -t deepagentschat-tools:latest -f docker/Dockerfile.tools .
```

### 问题 3: 权限错误

```
PermissionError: [Errno 13] Permission denied: '/workspace/...'
```

**解决方案**:
确保用户目录权限正确:
```bash
sudo chown -R 1000:1000 /tmp/user_files/
```

### 问题 4: 容器启动慢

**原因**: 首次启动需要拉取镜像和初始化

**优化方案**:
1. 使用更小的基础镜像
2. 预热镜像: `docker pull deepagentschat-tools:latest`
3. 考虑使用容器池（高级）

## 📊 性能对比

### 执行时间对比

| 操作 | tools.py | tools_docker.py |
|------|----------|-----------------|
| 简单命令 (echo) | ~10ms | ~1-2s |
| Python 脚本 | ~50ms | ~1.5-2.5s |
| 数据分析 (pandas) | ~100ms | ~2-3s |

### 资源占用对比

| 指标 | tools.py | tools_docker.py |
|------|----------|-----------------|
| 内存占用 | 主进程共享 | 512MB (隔离) |
| CPU 占用 | 无限制 | 1核 (可配置) |
| 磁盘占用 | 虚拟环境 (~100MB) | 镜像 (~500MB) |

## 🎯 使用建议

### 何时使用 tools.py

- ✅ 开发环境
- ✅ 可信用户
- ✅ 对性能要求高
- ✅ 简单任务

### 何时使用 tools_docker.py

- ✅ 生产环境
- ✅ 不可信用户
- ✅ 需要强隔离
- ✅ 需要资源限制
- ✅ 多租户场景

### 混合使用

可以根据任务类型动态选择：

```python
from app.tools import shell_exec as shell_exec_fast
from app.tools_docker import shell_exec as shell_exec_safe

# 简单任务使用快速版本
result = await shell_exec_fast("ls -la", runtime)

# 复杂/不可信任务使用安全版本
result = await shell_exec_safe(user_code, runtime)
```

## 🔐 安全最佳实践

1. **始终使用最小权限原则**
   - 非 root 用户
   - 移除不必要的 capabilities
   - 限制网络访问

2. **资源限制**
   - 设置合理的 CPU/内存限制
   - 设置执行超时
   - 限制磁盘使用

3. **定期更新**
   - 更新基础镜像
   - 更新依赖包
   - 应用安全补丁

4. **监控和审计**
   - 记录所有执行日志
   - 监控资源使用
   - 异常行为告警

## 📚 参考资料

- [Docker Security](https://docs.docker.com/engine/security/)
- [Docker Resource Constraints](https://docs.docker.com/config/containers/resource_constraints/)
- [Python Docker SDK](https://docker-py.readthedocs.io/)

---

**注意**: Docker 容器版本提供了更强的安全性，但会牺牲一些性能。请根据实际需求选择合适的版本。

"""
Agent Tools - Docker 共享容器版本

使用一个长期运行的共享 Docker 容器，所有用户通过目录隔离。
文件系统完全在容器内，通过 Docker API 操作。

## 主要特性

- 🔒 **安全隔离**: 用户通过目录隔离，文件系统在容器内
- 📦 **资源限制**: CPU、内存、磁盘空间限制
- 🚫 **网络隔离**: 可选的网络访问控制
- ⏱️ **超时控制**: 防止长时间运行的任务
- 🗂️ **文件隔离**: 每个用户独立目录 /workspace/{user_id}/
- 🚀 **高性能**: 共享容器，无需每次创建

## 架构设计

```
FastAPI App
    ↓
Docker Client API
    ↓
Shared Long-Running Container
    ├── Docker Volume: /workspace
    ├── /workspace/{user_id_1}/  # 用户1目录
    ├── /workspace/{user_id_2}/  # 用户2目录
    └── 执行命令（在用户目录内）
```

## 使用方式

与 tools.py 相同的 API，但底层使用共享 Docker 容器执行。

## 配置

环境变量:
- DOCKER_IMAGE: 工具容器镜像 (默认: deepagentschat-tools:latest)
- DOCKER_CPU_LIMIT: CPU 限制 (默认: 2.0)
- DOCKER_MEMORY_LIMIT: 内存限制 (默认: 1g)
- DOCKER_NETWORK_MODE: 网络模式 (默认: none, 可选: bridge, host)
- DOCKER_TIMEOUT: 执行超时 (默认: 30秒)
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langchain.tools import ToolRuntime, tool
from loguru import logger

try:
    import docker  # noqa: F401

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger.warning("Docker SDK not installed. Install with: pip install docker")

# 文件存储根目录
STORAGE_ROOT = Path("/tmp/user_files")
PUBLIC_DIR = STORAGE_ROOT / "public"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

# Docker 配置
DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "deepagentschat-tools:latest")
DOCKER_CPU_LIMIT = float(os.getenv("DOCKER_CPU_LIMIT", "1.0"))
DOCKER_MEMORY_LIMIT = os.getenv("DOCKER_MEMORY_LIMIT", "512m")
DOCKER_NETWORK_MODE = os.getenv("DOCKER_NETWORK_MODE", "none")  # none, bridge, host
DOCKER_TIMEOUT = int(os.getenv("DOCKER_TIMEOUT", "30"))


# ============ Context Schema ============
@dataclass
class UserContext:
    """用户上下文，通过 ToolRuntime 自动注入"""

    user_id: str


# ============ 工具定义 ============


@tool(parse_docstring=True)
async def shell_exec(
    command: str,
    runtime: ToolRuntime[UserContext],
    timeout: int = 30,
) -> str:
    """在共享 Docker 容器中执行 Bash 命令（安全隔离）。

    **安全特性**:
    - 在共享 Docker 容器中执行
    - 用户目录隔离 (/workspace/{user_id}/)
    - CPU 和内存限制
    - 默认无网络访问
    - 非 root 用户执行
    - 自动超时控制

    **可用命令**:
    - 所有标准 Linux 命令 (ls, cat, grep, awk, sed 等)
    - Python 3.12+ 和常用数据分析库
    - 数据分析工具 (pandas, duckdb, polars 等)

    **注意事项**:
    - 命令在共享容器中执行，但用户目录隔离
    - 默认无网络访问（可通过环境变量配置）
    - 文件操作限制在用户目录内

    Args:
        command: 要执行的 Bash 命令
        timeout: 命令执行超时时间(秒)，默认30秒
    """
    try:
        # 从 runtime context 获取 user_id
        user_id = runtime.context.user_id if runtime and runtime.context else None
        if not user_id:
            return "[错误] 需要用户上下文"

        # 使用共享容器管理器
        from app.core.shared_container import get_shared_container_manager

        manager = get_shared_container_manager()

        # 在共享容器中执行命令
        output, exit_code = manager.exec_command(user_id=user_id, command=command, timeout=timeout)

        if exit_code != 0:
            output += f"\n[Exit Code: {exit_code}]"

        # 截断过长输出
        if len(output) > 5000:
            output = output[:5000] + f"\n\n... (输出过长，已截断，共 {len(output)} 字符)"

        return output or "[命令执行成功，无输出]"

    except Exception as e:
        logger.error(f"shell_exec error: {e}")
        return f"[错误] {str(e)}"


@tool(parse_docstring=True)
async def write_file(
    filename: str,
    content: str,
    runtime: ToolRuntime[UserContext],
    mode: Literal["overwrite", "append"] = "overwrite",
) -> str:
    """写入文件到共享容器。

    Args:
        filename: 文件名或相对路径
        content: 要写入的文件内容
        mode: 写入模式，"overwrite"(覆盖) 或 "append"(追加)
    """
    try:
        user_id = runtime.context.user_id if runtime and runtime.context else None
        if not user_id:
            return "[错误] 需要用户上下文"

        # 验证文件名（防止路径遍历）
        if ".." in filename or filename.startswith("/"):
            return "[错误] 文件名不能包含 '..' 或以 '/' 开头"

        # 使用共享容器管理器
        from app.core.shared_container import get_shared_container_manager

        manager = get_shared_container_manager()

        # 使用 shell 命令写入文件
        if mode == "append":
            # 追加模式
            escaped_content = content.replace("'", "'\\''")
            command = f"echo '{escaped_content}' >> {filename}"
        else:
            # 覆盖模式
            escaped_content = content.replace("'", "'\\''")
            command = f"echo '{escaped_content}' > {filename}"

        output, exit_code = manager.exec_command(user_id=user_id, command=command)

        if exit_code == 0:
            action = "追加到" if mode == "append" else "写入"
            return f"[成功] {action}文件: {filename}"
        else:
            return f"[错误] 写入文件失败: {output}"

    except Exception as e:
        logger.error(f"write_file error: {e}")
        return f"[错误] 写入文件失败: {str(e)}"


@tool(parse_docstring=True)
async def read_file(
    filename: str,
    runtime: ToolRuntime[UserContext],
    max_chars: int = 2000,
) -> str:
    """读取共享容器中的文件内容。

    Args:
        filename: 文件名或相对路径
        max_chars: 最大读取字符数，默认2000（防止读取过大文件）
    """
    try:
        user_id = runtime.context.user_id if runtime and runtime.context else None
        if not user_id:
            return "[错误] 需要用户上下文"

        # 验证文件名（防止路径遍历）
        if ".." in filename or filename.startswith("/"):
            return "[错误] 文件名不能包含 '..' 或以 '/' 开头"

        # 使用共享容器管理器
        from app.core.shared_container import get_shared_container_manager

        manager = get_shared_container_manager()

        # 检查文件是否存在
        output, exit_code = manager.exec_command(
            user_id=user_id, command=f"test -f {filename} && echo 'EXISTS' || echo 'NOT_FOUND'"
        )

        if "NOT_FOUND" in output:
            return f"[错误] 文件不存在: {filename}"

        # 获取文件大小
        output, _ = manager.exec_command(user_id=user_id, command=f"wc -c < {filename}")
        try:
            file_size = int(output.strip())
        except ValueError:
            file_size = 0

        if file_size > max_chars * 2:
            return f"[警告] 文件过大 ({file_size} bytes)，建议使用 shell_exec 配合 head/tail 命令查看"

        # 读取文件内容（限制字符数）
        output, exit_code = manager.exec_command(user_id=user_id, command=f"head -c {max_chars} {filename}")

        if exit_code == 0:
            if len(output) >= max_chars:
                output += f"\n\n... (文件过长，已截断，总大小: {file_size} bytes)"
            return output
        else:
            return f"[错误] 读取文件失败: {output}"

    except Exception as e:
        logger.error(f"read_file error: {e}")
        return f"[错误] 读取文件失败: {str(e)}"


# ============ 工具列表导出 ============
ALL_TOOLS = [
    shell_exec,
    write_file,
    read_file,
]


# ============ Docker 镜像构建说明 ============
"""
## 构建 Docker 镜像

创建 `docker/Dockerfile.tools`:

```dockerfile
FROM python:3.13-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    bash \\
    coreutils \\
    grep \\
    sed \\
    awk \\
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 数据分析库
RUN pip install --no-cache-dir \\
    pandas \\
    openpyxl \\
    duckdb \\
    polars \\
    tabulate

# 创建非 root 用户
RUN useradd -m -u 1000 -s /bin/bash tooluser

# 设置工作目录
WORKDIR /workspace

# 切换到非 root 用户
USER tooluser

# 默认命令
CMD ["/bin/bash"]
```

构建命令:
```bash
docker build -t deepagentschat-tools:latest -f docker/Dockerfile.tools .
```

## 测试

```python
import asyncio
from app.tools_docker import shell_exec, UserContext, ToolRuntime

async def test():
    runtime = ToolRuntime(context=UserContext(user_id="test-user"))
    result = await shell_exec("echo 'Hello from Docker!'", runtime)
    print(result)

asyncio.run(test())
```
"""

"""
Agent Tools - 支持用户隔离的工具集

使用 ToolRuntime 实现可选的用户隔离：
- 如果提供 user_id（通过 context），操作限制在用户目录
- 如果未提供 user_id，使用公共目录

## 数据分析工具集成 (experiment_tools)

项目集成了强大的数据分析工具，每个用户目录下自动部署到 `.tools/` 目录，可通过 shell_exec 调用：

### 自动部署
- 用户首次使用时，自动复制工具到用户目录的 `.tools/` 子目录
- 自动安装工具依赖 (duckdb, pandas, openpyxl, polars, tabulate 等)
- 每个用户拥有独立的工具副本，互不干扰
- 工具路径相对于用户工作目录，使用简洁

### 文件读写工具 (.tools/files/)
1. **文件读取**: `python .tools/files/read_file.py <filename>`
   - 智能编码检测 (utf-8, gbk, gb2312, latin-1)
   - 大文件警告和截断
   - 支持所有文本格式

2. **URL 读取**: `python .tools/files/read_url.py <url> [options]`
   - 支持 HTTP/HTTPS 协议
   - 自动编码检测和内容类型识别
   - 选项: --timeout, --max-size, --save, --headers, --show-headers

### 数据查询工具 (.tools/query/)
**SQL 查询**: `python .tools/query/data_query.py "SELECT * FROM 'data.csv'"`
- 基于 DuckDB，支持 CSV/JSON/Parquet/Excel
- 文件可直接作为表名
- 支持复杂 SQL: JOIN, GROUP BY, 聚合函数等
- 示例:
  ```bash
  # 基本查询
  python .tools/query/data_query.py "SELECT * FROM 'sales.csv' LIMIT 10"

  # 聚合分析
  python .tools/query/data_query.py "SELECT product, SUM(amount) FROM 'sales.csv' GROUP BY product"

  # 导出结果
  python .tools/query/data_query.py "COPY (SELECT * FROM 'data.csv') TO 'output.csv'"
  ```

### 数据统计工具 (.tools/statistics/)
1. **描述性统计**: `python .tools/statistics/describe.py <file> [--format auto]`
   - 显示 count, unique, mean, std, min, max 等统计信息
   - 支持 CSV/JSON/Parquet/Excel

2. **数据预览**: `python .tools/statistics/head.py <file> [--limit 10]`
   - 显示数据前 N 行
   - 快速了解数据结构

3. **唯一值分析**: `python .tools/statistics/unique.py <file> [--topk 10]`
   - 显示每列的 Top K 最常见值
   - 用于数据质量检查

### 推荐工作流
```bash
# 1. 数据探索
python .tools/statistics/head.py data.csv
python .tools/statistics/describe.py data.csv

# 2. 数据分析
python .tools/query/data_query.py "SELECT category, COUNT(*) FROM 'data.csv' GROUP BY category"

# 3. 数据质量检查
python .tools/statistics/unique.py data.csv
```

### 注意事项
- 工具自动部署到每个用户的 `.tools/` 目录
- 所有工具在用户工作目录下执行 (通过 shell_exec 的 cwd)
- 大文件建议使用 SQL 查询而非完整读取
- 支持管道操作: `cat data.csv | grep "2024" | ...`
"""

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langchain.tools import ToolRuntime, tool

from app.core.storage import (
    TOOLS_VENV_DIR,
    sanitize_path,
)
from app.core.storage import (
    get_work_path as _get_storage_path,
)


# ============ Context Schema ============
@dataclass
class UserContext:
    """用户上下文，通过 ToolRuntime 自动注入"""

    user_id: str


def get_work_path(user_id: str | None = None) -> Path:
    """
    获取工作目录，并确保工具已部署

    Args:
        user_id: 用户 ID（可选），如果为 None 则返回公共目录

    Returns:
        Path: 工作目录路径
    """
    path = _get_storage_path(user_id)
    if user_id:
        # 自动初始化用户工具
        _ensure_user_tools(path)
    return path


def _ensure_tools_dependencies() -> None:
    """
    确保工具虚拟环境的依赖已安装（全局共享，只需安装一次）
    """
    import subprocess

    deps_marker = TOOLS_VENV_DIR / ".deps_installed"

    # 如果依赖已安装，跳过
    if deps_marker.exists():
        return

    source_tools = Path(__file__).parent / "experiment_tools"
    requirements_file = source_tools / "requirements.txt"

    if not requirements_file.exists():
        print(f"[WARNING] requirements.txt 不存在: {requirements_file}")
        return

    print("[INFO] 正在安装工具依赖到全局工具虚拟环境...")
    try:
        # 确保工具虚拟环境存在
        venv_bin = ensure_tools_venv()
        venv_python = venv_bin / "python"

        # 使用工具虚拟环境的 pip 安装依赖
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file), "-q"],
            capture_output=True,
            text=True,
            timeout=180,  # 3分钟超时
        )

        if result.returncode == 0:
            # 创建标记文件
            deps_marker.write_text("installed")
            print("[INFO] 工具依赖安装成功")
        else:
            print(f"[WARNING] 工具依赖安装失败: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("[WARNING] 依赖安装超时，跳过")
    except Exception as e:
        print(f"[WARNING] 安装依赖时出错: {e}")


def _ensure_user_tools(user_path: Path) -> None:
    """
    确保用户目录下有数据分析工具

    Args:
        user_path: 用户工作目录
    """
    # 先确保全局工具依赖已安装（即使用户目录的工具已存在）
    _ensure_tools_dependencies()

    tools_dir = user_path / ".tools"

    # 如果工具目录已存在，跳过复制
    if tools_dir.exists():
        return

    # 复制工具到用户目录
    import shutil

    source_tools = Path(__file__).parent / "experiment_tools"

    if not source_tools.exists():
        print(f"[WARNING] 工具源目录不存在: {source_tools}")
        return

    try:
        # 复制整个 experiment_tools 目录到用户的 .tools 目录
        shutil.copytree(source_tools, tools_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        print(f"[INFO] 已为用户初始化数据分析工具: {tools_dir}")

    except Exception as e:
        print(f"[ERROR] 复制工具失败: {e}")


def ensure_tools_venv() -> Path:
    """
    确保工具虚拟环境存在,如果不存在则创建(使用符号链接共享项目依赖)

    Returns:
        Path: 工具虚拟环境的 bin 目录路径
    """
    import subprocess
    import sys

    venv_bin = TOOLS_VENV_DIR / "bin"
    venv_python = venv_bin / "python"

    # 如果虚拟环境已存在,直接返回
    if venv_python.exists():
        return venv_bin

    # 创建虚拟环境
    print(f"[INFO] 首次使用,正在创建工具虚拟环境: {TOOLS_VENV_DIR}")
    try:
        # 获取项目虚拟环境的 Python
        project_root = Path(__file__).parent.parent
        project_venv = project_root / ".venv"
        project_python_path = project_venv / "bin" / "python"

        if not project_python_path.exists():
            # 如果项目虚拟环境不存在,使用系统 Python
            python_executable = sys.executable
            print("[WARNING] 项目虚拟环境不存在,使用系统 Python")
        else:
            python_executable = str(project_python_path)

        # 创建虚拟环境
        subprocess.run(
            [python_executable, "-m", "venv", str(TOOLS_VENV_DIR)],
            check=True,
            capture_output=True,
        )

        # 不链接项目依赖，保持工具虚拟环境完全独立
        # 这样可以避免依赖冲突（如 numpy 版本不兼容）

        print(f"[INFO] 工具虚拟环境创建成功: {TOOLS_VENV_DIR}")
        return venv_bin
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 创建虚拟环境失败: {e}")
        print(f"[ERROR] stdout: {e.stdout.decode() if e.stdout else 'N/A'}")
        print(f"[ERROR] stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        # 创建失败,回退到项目虚拟环境
        project_root = Path(__file__).parent.parent
        return project_root / ".venv" / "bin"


# ============ 工具实现 ============


@tool(parse_docstring=True)
async def shell_exec(
    command: str,
    runtime: ToolRuntime[UserContext],
    timeout: int = 30,
) -> str:
    """## 执行Bash命令(使用独立的工具虚拟环境)

    ### 基础命令工具
    - **文件浏览**: `ls`, `tree`, `cat`, `head`, `tail`
    - **搜索与处理**: `grep`, `sed`, `awk`, `jq` (处理 JSON)
    - **编程环境**: `python` (用于复杂逻辑或数学计算,使用独立的工具虚拟环境)
    - **网络**: `curl` (获取网页内容)

    ### 数据分析工具 (自动部署到 .tools/ 目录)

    **数据预览与统计**:
    - `python .tools/statistics/head.py <file> [--limit 10]` - 显示数据前N行
    - `python .tools/statistics/describe.py <file>` - 描述性统计(count, mean, std, min, max等)
    - `python .tools/statistics/unique.py <file> [--topk 10]` - 分析每列Top K最常见值

    **SQL查询** (支持 CSV/JSON/Parquet/Excel):
    - `python .tools/query/data_query.py "SELECT * FROM 'data.csv' LIMIT 10"` - 基本查询
    - `python .tools/query/data_query.py "SELECT col, COUNT(*) FROM 'data.csv' GROUP BY col"` - 聚合分析
    - `python .tools/query/data_query.py "COPY (SELECT * FROM 'data.csv') TO 'output.csv'"` - 导出结果

    **文件读取**:
    - `python .tools/files/read_file.py <filename>` - 查看文本文件内容
    - `python .tools/files/read_url.py <url> [--timeout 30]` - 读取URL内容

    **推荐工作流**:
    1. 数据探索: `head.py` → `describe.py` → `unique.py`
    2. 数据分析: `data_query.py` 执行SQL查询
    3. 结果导出: 使用 `COPY TO` 命令

    Args:
        command: 要执行的 Bash 命令
        timeout: 命令执行超时时间(秒)，默认30秒
    """
    try:
        # 从 runtime context 获取 user_id（可能为 None）
        user_id = runtime.context.user_id if runtime and runtime.context else None
        work_path = get_work_path(user_id)

        # 确保工具虚拟环境存在并获取其 bin 目录
        venv_bin = ensure_tools_venv()
        venv_python = venv_bin / "python"

        # 如果命令是运行 .tools/ 下的 Python 脚本，替换为工具虚拟环境的 python
        if command.strip().startswith("python .tools/") and venv_python.exists():
            command = command.replace("python .tools/", f"{venv_python} .tools/", 1)

        # 构建环境变量,使用独立的工具虚拟环境
        env = os.environ.copy()
        if venv_bin.exists():
            # 设置虚拟环境变量
            env["VIRTUAL_ENV"] = str(TOOLS_VENV_DIR)
            # 将虚拟环境的 bin 目录添加到 PATH 最前面
            env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
            # 移除 PYTHONHOME(如果存在),避免冲突
            env.pop("PYTHONHOME", None)

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash",
            cwd=str(work_path),
            env=env,  # 传入修改后的环境变量
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            return f"[错误] 命令执行超时 (>{timeout}秒)"

        output = stdout.decode("utf-8")
        if stderr:
            output += f"\n[STDERR]:\n{stderr.decode('utf-8')}"

        if process.returncode != 0:
            output += f"\n[Exit Code: {process.returncode}]"

        if len(output) > 5000:
            output = output[:5000] + f"\n\n... (输出过长，已截断，共 {len(output)} 字符)"

        return output or "[命令执行成功，无输出]"

    except Exception as e:
        return f"[错误] {str(e)}"


@tool(parse_docstring=True)
async def write_file(
    filename: str,
    content: str,
    runtime: ToolRuntime[UserContext],
    mode: Literal["overwrite", "append"] = "overwrite",
) -> str:
    """写入文件。

    Args:
        filename: 文件名或相对路径
        content: 要写入的文件内容
        mode: 写入模式，"overwrite"(覆盖) 或 "append"(追加)
    """
    try:
        user_id = runtime.context.user_id if runtime and runtime.context else None
        file_path = sanitize_path(user_id, filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        write_mode = "a" if mode == "append" else "w"

        def _write():
            with open(file_path, write_mode, encoding="utf-8") as f:
                f.write(content)

        await asyncio.to_thread(_write)

        size = len(content)
        lines = content.count("\n") + 1
        action = "追加到" if mode == "append" else "写入"

        work_path = get_work_path(user_id)
        relative_path = file_path.relative_to(work_path)

        return f"✓ 成功{action}文件: {relative_path} ({size} 字符, {lines} 行)"

    except ValueError as e:
        return f"[安全错误] {str(e)}"
    except Exception as e:
        return f"[错误] 写入文件失败: {str(e)}"


@tool(parse_docstring=True)
async def read_file(
    filename: str,
    runtime: ToolRuntime[UserContext],
    max_chars: int = 2000,
) -> str:
    """读取文件。

    Args:
        filename: 文件名或相对路径
        max_chars: 最大读取字符数，超过会自动截断，默认2000
    """
    try:
        user_id = runtime.context.user_id if runtime and runtime.context else None
        file_path = sanitize_path(user_id, filename)

        if not file_path.exists():
            return f"[错误] 文件不存在: {filename}"

        file_size = file_path.stat().st_size

        def _read():
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.read(max_chars + 1)

        content = await asyncio.to_thread(_read)

        if len(content) > max_chars:
            content = content[:max_chars]
            return f"{content}\n\n... [文件过大已截断，显示前 {max_chars} 字符，总大小: {file_size} 字节]"

        return str(content)

    except ValueError as e:
        return f"[安全错误] {str(e)}"
    except Exception as e:
        return f"[错误] 读取文件失败: {str(e)}"


# ============ 工具列表导出 ============
ALL_TOOLS = [
    shell_exec,
    write_file,
    read_file,
]


# ============ 使用示例 ============
if __name__ == "__main__":
    import asyncio
    from typing import Any

    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    # 示例 1: 使用用户隔离
    agent: Any = create_agent(
        model,
        tools=ALL_TOOLS,
        context_schema=UserContext,
    )

    async def test_with_user():
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "创建一个 hello.txt 文件"}]},
            context=UserContext(user_id="user-123"),
        )
        print(result["messages"][-1].content)

    # 示例 2: 使用公共目录（不传 context）
    agent_public: Any = create_agent(
        model,
        tools=ALL_TOOLS,
    )

    async def test_public():
        result = await agent_public.ainvoke({"messages": [{"role": "user", "content": "列出当前目录文件"}]})
        print(result["messages"][-1].content)

    asyncio.run(test_with_user())

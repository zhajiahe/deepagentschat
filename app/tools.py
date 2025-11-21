"""
Agent Tools - 支持用户隔离的工具集

使用 ToolRuntime 实现可选的用户隔离：
- 如果提供 user_id（通过 context），操作限制在用户目录
- 如果未提供 user_id，使用公共目录
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langchain.tools import ToolRuntime, tool

# 文件存储根目录
STORAGE_ROOT = Path("/tmp/user_files")
PUBLIC_DIR = STORAGE_ROOT / "public"  # 公共目录
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


# ============ Context Schema ============
@dataclass
class UserContext:
    """用户上下文，通过 ToolRuntime 自动注入"""

    user_id: str


def get_work_path(user_id: str | None = None) -> Path:
    """
    获取工作目录

    Args:
        user_id: 用户 ID（可选），如果为 None 则返回公共目录

    Returns:
        Path: 工作目录路径
    """
    if user_id:
        user_path = STORAGE_ROOT / str(user_id)
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path
    return PUBLIC_DIR


def sanitize_path(user_id: str | None, filename: str) -> Path:
    """
    清理并验证文件路径

    Args:
        user_id: 用户 ID（可选）
        filename: 文件名或相对路径

    Returns:
        Path: 安全的绝对路径

    Raises:
        ValueError: 如果路径试图逃逸工作目录
    """
    work_path = get_work_path(user_id)

    # 移除路径中的危险字符和序列
    safe_filename = filename.replace("../", "").replace("..\\", "")

    # 构建完整路径
    full_path = (work_path / safe_filename).resolve()

    # 确保路径在工作目录内
    if not str(full_path).startswith(str(work_path.resolve())):
        raise ValueError(f"路径 '{filename}' 超出工作目录范围")

    return full_path


# ============ 工具实现 ============


@tool(parse_docstring=True)
async def shell_exec(command: str, timeout: int = 30, runtime: ToolRuntime[UserContext] = None) -> str:
    """## 执行Bash命令
    - **文件浏览**: `ls`, `tree`, `cat`, `head`, `tail`
    - **搜索与处理**: `grep`, `sed`, `awk`, `jq` (处理 JSON)
    - **编程环境**: `python` (用于复杂逻辑或数学计算)
    - **网络**: `curl` (获取网页内容)

    Args:
        command: 要执行的 Bash 命令
        timeout: 命令执行超时时间(秒)，默认30秒
    """
    try:
        # 从 runtime context 获取 user_id（可能为 None）
        user_id = runtime.context.user_id if runtime and runtime.context else None
        work_path = get_work_path(user_id)

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash",
            cwd=str(work_path),
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
    mode: Literal["overwrite", "append"] = "overwrite",
    runtime: ToolRuntime[UserContext] = None,
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
async def read_file(filename: str, max_chars: int = 2000, runtime: ToolRuntime[UserContext] = None) -> str:
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
            return f"{content}\n\n" f"... [文件过大已截断，显示前 {max_chars} 字符，" f"总大小: {file_size} 字节]"

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

    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    # 示例 1: 使用用户隔离
    agent = create_agent(
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
    agent_public = create_agent(
        model,
        tools=ALL_TOOLS,
    )

    async def test_public():
        result = await agent_public.ainvoke({"messages": [{"role": "user", "content": "列出当前目录文件"}]})
        print(result["messages"][-1].content)

    asyncio.run(test_with_user())

"""
Agent Tools - 支持用户隔离的工具集

使用 ToolRuntime 实现可选的用户隔离：
- 如果提供 user_id（通过 context），操作限制在用户目录
- 如果未提供 user_id，使用公共目录
"""

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langchain.tools import ToolRuntime, tool

# 文件存储根目录
STORAGE_ROOT = Path("/tmp/user_files")
PUBLIC_DIR = STORAGE_ROOT / "public"  # 公共目录
TOOLS_VENV_DIR = STORAGE_ROOT / ".tools_venv"  # 工具专用虚拟环境
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

        # 创建 pyvenv.cfg 文件,设置 include-system-site-packages = true
        pyvenv_cfg = TOOLS_VENV_DIR / "pyvenv.cfg"
        if pyvenv_cfg.exists() and project_venv.exists():
            # 读取原有配置
            cfg_content = pyvenv_cfg.read_text()
            # 添加项目虚拟环境的 site-packages 到 PYTHONPATH
            # 通过修改 pyvenv.cfg 实现
            cfg_lines = cfg_content.split("\n")
            new_lines = []
            for line in cfg_lines:
                if line.startswith("include-system-site-packages"):
                    new_lines.append("include-system-site-packages = true")
                else:
                    new_lines.append(line)
            # 添加项目虚拟环境路径
            new_lines.append(f"# Project venv: {project_venv}")
            pyvenv_cfg.write_text("\n".join(new_lines))

            # 创建 .pth 文件,将项目虚拟环境的 site-packages 添加到 Python 路径
            site_packages = (
                TOOLS_VENV_DIR / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
            )
            site_packages.mkdir(parents=True, exist_ok=True)
            pth_file = site_packages / "project_venv.pth"
            project_site_packages = (
                project_venv / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
            )
            if project_site_packages.exists():
                pth_file.write_text(str(project_site_packages))
                print(f"[INFO] 已链接项目依赖: {project_site_packages}")

        print(f"[INFO] 工具虚拟环境创建成功: {TOOLS_VENV_DIR}")
        return venv_bin
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 创建虚拟环境失败: {e}")
        print(f"[ERROR] stdout: {e.stdout.decode() if e.stdout else 'N/A'}")
        print(f"[ERROR] stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        # 创建失败,回退到项目虚拟环境
        project_root = Path(__file__).parent.parent
        return project_root / ".venv" / "bin"


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
async def shell_exec(command: str, timeout: int = 30, runtime: ToolRuntime[UserContext] | None = None) -> str:
    """## 执行Bash命令(使用独立的工具虚拟环境)
    - **文件浏览**: `ls`, `tree`, `cat`, `head`, `tail`
    - **搜索与处理**: `grep`, `sed`, `awk`, `jq` (处理 JSON)
    - **编程环境**: `python` (用于复杂逻辑或数学计算,使用独立的工具虚拟环境)
    - **网络**: `curl` (获取网页内容)

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
    mode: Literal["overwrite", "append"] = "overwrite",
    runtime: ToolRuntime[UserContext] | None = None,
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
async def read_file(filename: str, max_chars: int = 2000, runtime: ToolRuntime[UserContext] | None = None) -> str:
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

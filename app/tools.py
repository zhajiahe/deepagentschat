"""
Agent CLI Environment - LangChain Tool Implementation
将 Shell 命令执行能力封装为 LangChain Tool
"""

import os
import subprocess

from langchain.tools import BaseTool
from pydantic import BaseModel, Field


# ============ 输入模式定义 ============
class ShellCommandInput(BaseModel):
    """Shell 命令执行的输入参数"""

    command: str = Field(description="要执行的 Bash 命令。支持管道、重定向等所有 Shell 特性")
    timeout: int = Field(default=30, description="命令执行超时时间(秒)，默认30秒")


class WriteFileInput(BaseModel):
    """写入文件的输入参数"""

    filename: str = Field(description="目标文件路径")
    content: str = Field(description="要写入的文件内容")


class ReadFileInput(BaseModel):
    """读取文件的输入参数"""

    filename: str = Field(description="要读取的文件路径")
    max_chars: int = Field(default=2000, description="最大读取字符数，超过会自动截断")


# ============ 核心工具实现 ============
class ShellExecutorTool(BaseTool):
    """执行 Shell 命令的工具"""

    name: str = "shell_executor"
    description: str = """
    执行 Linux Shell 命令。支持所有 Bash 特性：
    - 文件操作: ls, cat, grep, sed, awk
    - 数据处理: jq (JSON), sort, uniq
    - 管道和重定向: | > >>
    - Python 脚本: python3
    - 网络请求: curl

    示例:
    - "ls -la | grep .py"
    - "cat data.json | jq '.items[] | .name'"
    - "python3 script.py > output.txt"
    """
    args_schema: type[BaseModel] = ShellCommandInput

    def _run(self, command: str, timeout: int = 30) -> str:
        """执行命令并返回结果"""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout, executable="/bin/bash"
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]:\n{result.stderr}"

            if result.returncode != 0:
                output += f"\n[Exit Code: {result.returncode}]"

            # 限制输出长度，避免 Token 过多
            if len(output) > 5000:
                output = output[:5000] + f"\n\n... (输出过长，已截断，共 {len(output)} 字符)"

            return output or "[命令执行成功，无输出]"

        except subprocess.TimeoutExpired:
            return f"[错误] 命令执行超时 (>{timeout}秒)"
        except Exception as e:
            return f"[错误] {str(e)}"

    async def _arun(self, command: str, timeout: int = 30) -> str:
        """异步执行 (使用同步实现)"""
        return self._run(command, timeout)


class WriteFileTool(BaseTool):
    """安全写入文件的工具"""

    name: str = "write_file"
    description: str = """
    安全地将内容写入文件，自动处理转义和编码问题。
    避免在 Shell 中手动处理复杂的引号转义。

    示例:
    - filename: "script.py", content: "print('hello world')"
    - filename: "config.json", content: '{"key": "value"}'
    """
    args_schema: type[BaseModel] = WriteFileInput

    def _run(self, filename: str, content: str) -> str:
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)

            size = len(content)
            lines = content.count("\n") + 1
            return f"✓ 成功写入文件: {filename} ({size} 字符, {lines} 行)"

        except Exception as e:
            return f"[错误] 写入文件失败: {str(e)}"

    async def _arun(self, filename: str, content: str) -> str:
        return self._run(filename, content)


class ReadFileTool(BaseTool):
    """智能读取文件的工具"""

    name: str = "read_file"
    description: str = """
    读取文件内容。如果文件过大会自动截断，节省 Token。
    适合读取日志、配置文件、代码等。

    示例:
    - filename: "log.txt"
    - filename: "data.json", max_chars: 5000
    """
    args_schema: type[BaseModel] = ReadFileInput

    def _run(self, filename: str, max_chars: int = 2000) -> str:
        try:
            if not os.path.exists(filename):
                return f"[错误] 文件不存在: {filename}"

            file_size = os.path.getsize(filename)

            with open(filename, encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars + 1)

            if len(content) > max_chars:
                content = content[:max_chars]
                return f"{content}\n\n" f"... [文件过大已截断，显示前 {max_chars} 字符，" f"总大小: {file_size} 字节]"

            return content

        except Exception as e:
            return f"[错误] 读取文件失败: {str(e)}"

    async def _arun(self, filename: str, max_chars: int = 2000) -> str:
        return self._run(filename, max_chars)


# ============ 使用示例 ============
if __name__ == "__main__":
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    # 1. 创建工具集
    tools = [ShellExecutorTool(), WriteFileTool(), ReadFileTool()]

    # 2. 创建 LLM
    llm = ChatOpenAI(model="gpt-4", temperature=0)

    # 3. 创建 Prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你是一个拥有 Linux Shell 权限的智能助手。

可用工具:
- shell_executor: 执行任何 Bash 命令
- write_file: 安全写入文件
- read_file: 智能读取文件

最佳实践:
1. 使用管道组合命令: cat file.json | jq .key
2. 输出重定向到文件: python script.py > result.txt
3. 复杂任务先写脚本再执行
4. 读取大文件前先用 head 预览
""",
            ),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # 4. 创建 Agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)

    # 5. 测试示例
    print("=== 测试 1: 文件操作 ===")
    result = agent_executor.invoke({"input": "创建一个 Python 脚本计算斐波那契数列前10项，然后执行它"})
    print(result["output"])

    print("\n=== 测试 2: 数据处理 ===")
    result = agent_executor.invoke({"input": "列出当前目录所有 .py 文件，统计总行数"})
    print(result["output"])

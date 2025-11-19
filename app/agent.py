"""
示例 Agent 实现

这是一个示例的聊天机器人节点实现，使用 LangChain v1 的 create_agent API
"""

import os
from typing import Any

from deepagents.middleware import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.tools import tool
from langchain_core.runnables import Runnable
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.backends import FilesystemSandboxBackend

load_dotenv()
client = MultiServerMCPClient(
    {
        "langchain_doc": {
            "url": "https://docs.langchain.com/mcp",
            "transport": "streamable_http",
        }
    }
)


@tool
def math_tool(expression: str) -> str:
    """
    Calculate the result of a mathematical expression.
    Args:
        expression: The mathematical expression to evaluate.

    Returns:
        The result of the expression as a string.
    """
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


async def get_agent(
    checkpointer: Any | None = None,
    llm_model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    max_tokens: int = 4096,
    user_id: Any | None = None,
) -> Runnable:
    """
    创建并返回 Agent 图

    Args:
        checkpointer: 可选的检查点保存器,用于状态持久化
        llm_model: LLM 模型名称
        api_key: API 密钥
        base_url: API 基础 URL
        max_tokens: 最大 token 数
        user_id: 用户 ID（UUID），用于创建独立的工作目录

    Returns:
        Runnable: 编译后的 Agent 图
    """
    api_key_value = api_key or os.getenv("OPENAI_API_KEY")
    secret_api_key: SecretStr | None = SecretStr(api_key_value) if api_key_value else None

    model = ChatOpenAI(
        model=llm_model or os.getenv("DEFAULT_LLM_MODEL", "Qwen/Qwen3-8B"),
        api_key=secret_api_key,
        base_url=base_url or os.getenv("OPENAI_API_BASE"),
        max_completion_tokens=max_tokens,
        streaming=True,  # 启用流式输出
    )
    tools = await client.get_tools()
    # 为每个用户创建独立的工作目录
    root_dir = f"/tmp/{user_id}" if user_id else "/tmp/default"
    backend = FilesystemSandboxBackend(
        root_dir=root_dir,
        virtual_mode=True,  # 使用虚拟文件系统（内存）
    )
    agent: Runnable = create_agent(
        model,
        tools=tools,
        checkpointer=checkpointer,
        middleware=[
            TodoListMiddleware(),
            FilesystemMiddleware(backend=backend),
            PatchToolCallsMiddleware(),
            SummarizationMiddleware(model=model, max_tokens_before_summary=170000, messages_to_keep=10),
        ],
    ).with_config({"recursion_limit": 1000})  # 防止过早停止
    return agent


if __name__ == "__main__":
    import asyncio

    async def main():
        agent = await get_agent()
        result = await agent.ainvoke({"messages": [{"role": "user", "content": "What is 1231972 / 8723?"}]})
        print(result)

    asyncio.run(main())

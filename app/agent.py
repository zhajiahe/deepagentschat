"""
示例 Agent 实现

这是一个示例的聊天机器人节点实现，使用 LangChain v1 的 create_agent API
"""

import os
from typing import Any

from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain_core.runnables import Runnable
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.tools import ALL_TOOLS, UserContext

load_dotenv()
client = MultiServerMCPClient(
    {
        "langchain_doc": {
            "url": "https://docs.langchain.com/mcp",
            "transport": "streamable_http",
        }
    }
)


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
        model=llm_model or os.getenv("DEFAULT_LLM_MODEL") or "Qwen/Qwen3-8B",
        api_key=secret_api_key,
        base_url=base_url or os.getenv("OPENAI_API_BASE"),
        max_completion_tokens=max_tokens,
        streaming=True,  # 启用流式输出
    )

    # 获取 MCP 工具
    mcp_tools = await client.get_tools()

    # 使用 deepagents 默认 backend + 用户隔离工具
    agent: Runnable = create_agent(
        model,
        tools=[*mcp_tools, *ALL_TOOLS],
        checkpointer=checkpointer,
        context_schema=UserContext,  # 指定 context schema
        middleware=[
            TodoListMiddleware(),
            PatchToolCallsMiddleware(),
            SummarizationMiddleware(model=model, max_tokens_before_summary=170000, messages_to_keep=10),
        ],
    ).with_config({"recursion_limit": 1000})
    return agent


if __name__ == "__main__":
    import asyncio

    async def main():
        agent = await get_agent()
        async for token, metadata in agent.astream(
            {"messages": [{"role": "user", "content": "列举当前文件夹文件列表"}]},
            stream_mode="messages",
        ):
            # `token` contains token-level contentBlocks; metadata tells which node produced it
            print(token.content_blocks, metadata)

    asyncio.run(main())

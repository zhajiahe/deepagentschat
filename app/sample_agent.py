"""
示例 Agent 实现

这是一个示例的聊天机器人节点实现，使用 LangChain v1 的 create_agent API
"""

import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()


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


def get_agent(
    checkpointer: Any | None = None,
    llm_model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    max_tokens: int = 4096,
) -> Runnable:
    """
    创建并返回 Agent 图

    Args:
        checkpointer: 可选的检查点保存器，用于状态持久化

    Returns:
        CompiledGraph: 编译后的 Agent 图
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
    agent: Runnable = create_agent(model, tools=[math_tool], checkpointer=checkpointer)
    return agent


if __name__ == "__main__":
    agent = get_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": "What is 1231972 / 8723?"}]})
    print(result)

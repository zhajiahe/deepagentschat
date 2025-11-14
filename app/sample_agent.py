"""
示例 Agent 实现

这是一个示例的聊天机器人节点实现，使用 LangChain v1 的 create_agent API
"""

import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI

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


def get_agent(checkpointer=None):
    """
    创建并返回 Agent 图

    Args:
        checkpointer: 可选的检查点保存器，用于状态持久化

    Returns:
        CompiledGraph: 编译后的 Agent 图
    """
    model = ChatOpenAI(
        model=os.getenv("SILICONFLOW_LLM_MODEL", "Qwen/Qwen3-8B"),
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url=os.getenv("SILICONFLOW_API_BASE"),
        max_tokens=500,
        temperature=0,
        extra_body={"thinking_budget": 20},
    )
    agent = create_agent(model, tools=[math_tool], checkpointer=checkpointer)
    return agent


if __name__ == "__main__":
    agent = get_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": "What is 1231972 / 8723?"}]})
    print(result)

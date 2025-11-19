"""
LangGraph 图定义

定义对话流程的图结构和节点
"""

from typing import Any

from app.agent import get_agent


async def create_graph(
    checkpointer=None,
    llm_model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    max_tokens: int = 4096,
    user_id: Any | None = None,
):
    """
    创建 LangGraph 对话流程图

    使用 LangChain v1 的 create_agent API 创建 Agent 图

    Args:
        checkpointer: 可选的检查点保存器，用于状态持久化
        llm_model: 可选的 LLM 模型
        api_key: 可选的 API 密钥
        base_url: 可选的 API 基础 URL
        max_tokens: 可选的最大 token 数
        user_id: 用户 ID（UUID），用于创建独立的工作目录
    Returns:
        Runnable: 可运行的 Agent 图
    """
    return await get_agent(
        checkpointer=checkpointer,
        llm_model=llm_model,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
        user_id=user_id,
    )

"""
LangGraph 图定义

定义对话流程的图结构和节点
"""

from app.sample_agent import get_agent


def create_graph(checkpointer=None):
    """
    创建 LangGraph 对话流程图

    使用 LangChain v1 的 create_agent API 创建 Agent 图

    Args:
        checkpointer: 可选的检查点保存器，用于状态持久化

    Returns:
        CompiledGraph: 编译后的 Agent 图
    """
    # create_agent 返回的已经是编译后的图，可以直接使用
    return get_agent(checkpointer=checkpointer)

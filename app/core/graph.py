"""
LangGraph 图定义

定义对话流程的图结构和节点
"""

import asyncio

from langchain_core.messages import AIMessage
from langgraph.graph import END, MessagesState, StateGraph


def create_graph():
    """
    创建 LangGraph 对话流程图

    Returns:
        StateGraph: 未编译的图对象
    """
    workflow = StateGraph(MessagesState)

    async def chatbot(state: MessagesState):
        """
        异步聊天机器人节点

        这是一个示例节点，实际使用时应该替换为真实的 LLM 调用

        Args:
            state: 消息状态

        Returns:
            dict: 包含新消息的字典
        """
        # 获取最后一条用户消息
        user_message = state["messages"][-1].content

        # 模拟异步 LLM 调用
        await asyncio.sleep(0.1)  # 模拟网络延迟

        # TODO: 替换为实际的 LLM 调用
        # 例如:
        # from langchain_openai import ChatOpenAI
        # llm = ChatOpenAI(model="gpt-4")
        # response = await llm.ainvoke(state["messages"])

        # 简单的 Echo 响应
        response = f"Echo: {user_message}"

        return {"messages": [AIMessage(content=response)]}

    # 添加节点
    workflow.add_node("chatbot", chatbot)

    # 设置入口点
    workflow.set_entry_point("chatbot")

    # 添加边
    workflow.add_edge("chatbot", END)

    return workflow

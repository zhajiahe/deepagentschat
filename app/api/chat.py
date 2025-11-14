"""
对话 API 路由

提供 LangGraph 对话功能的 API 端点
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.lifespan import get_compiled_graph
from app.models import Conversation, Message
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    异步对话接口 (非流式)

    Args:
        request: 对话请求
        background_tasks: 后台任务
        db: 数据库会话

    Returns:
        ChatResponse: 对话响应
    """
    # 获取或创建会话
    thread_id = request.thread_id
    if not thread_id:
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=request.user_id,
            title=request.message[:50] if len(request.message) > 50 else request.message,
            meta_data=request.metadata or {},
        )
        db.add(conversation)
        await db.commit()
    else:
        # 验证会话是否存在
        result = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation = conv

    config = {"configurable": {"thread_id": thread_id}}

    try:
        # 保存用户消息
        user_message = Message(
            thread_id=thread_id,
            role="user",
            content=request.message,
            meta_data=request.metadata or {},
        )
        db.add(user_message)
        await db.commit()

        # 执行图（异步）
        start_time = datetime.utcnow()
        compiled_graph = get_compiled_graph()
        graph_result = await compiled_graph.ainvoke({"messages": [HumanMessage(content=request.message)]}, config)
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        # 保存所有新产生的消息（不仅仅是最后一条）
        # graph_result["messages"] 包含所有消息，包括用户消息和所有 agent 产生的消息
        result_messages = graph_result["messages"]

        # 从第二条消息开始保存（第一条是用户消息，已经保存过了）
        for msg in result_messages[1:]:
            # 确定消息类型
            msg_type = type(msg).__name__
            if msg_type == "AIMessage":
                role = "assistant"
            elif msg_type == "HumanMessage":
                role = "user"
            elif msg_type == "SystemMessage":
                role = "system"
            elif msg_type == "ToolMessage":
                role = "tool"
            elif msg_type == "FunctionMessage":
                role = "function"
            else:
                role = msg_type.lower().replace("message", "")

            # 保存消息
            message = Message(
                thread_id=thread_id,
                role=role,
                content=str(msg.content) if msg.content else "",
                meta_data={
                    "type": msg_type,
                    "duration_ms": duration if role == "assistant" else None,
                    **(msg.additional_kwargs if hasattr(msg, "additional_kwargs") else {}),
                },
            )
            db.add(message)

        # 提取最后一条助手回复用于响应
        assistant_content = result_messages[-1].content

        # 更新会话时间
        result_conv = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
        conv_update = result_conv.scalar_one_or_none()
        if conv_update:
            conv_update.update_time = datetime.utcnow()

        await db.commit()

        return ChatResponse(thread_id=thread_id, response=assistant_content, duration_ms=int(duration))

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    异步流式对话接口

    Args:
        request: 对话请求
        db: 数据库会话

    Returns:
        StreamingResponse: 流式响应
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    if not request.thread_id:
        conversation = Conversation(
            thread_id=thread_id,
            user_id=request.user_id,
            title=request.message[:50] if len(request.message) > 50 else request.message,
            meta_data=request.metadata or {},
        )
        db.add(conversation)
        await db.commit()

    # 保存用户消息
    user_message = Message(
        thread_id=thread_id,
        role="user",
        content=request.message,
        meta_data=request.metadata or {},
    )
    db.add(user_message)
    await db.commit()

    config = {"configurable": {"thread_id": thread_id}}

    async def event_generator():
        all_messages = []
        try:
            compiled_graph = get_compiled_graph()
            # 使用异步 stream
            async for event in compiled_graph.astream(
                {"messages": [HumanMessage(content=request.message)]}, config, stream_mode="values"
            ):
                if "messages" in event and event["messages"]:
                    all_messages = event["messages"]
                    last_message = all_messages[-1]
                    if hasattr(last_message, "content"):
                        chunk = last_message.content
                        yield f"data: {json.dumps({'content': chunk, 'thread_id': thread_id})}\n\n"

            # 保存所有新产生的消息
            if len(all_messages) > 1:  # 第一条是用户消息，已保存
                async with AsyncSessionLocal() as new_session:
                    # 从第二条消息开始保存
                    for msg in all_messages[1:]:
                        # 确定消息类型
                        msg_type = type(msg).__name__
                        if msg_type == "AIMessage":
                            role = "assistant"
                        elif msg_type == "HumanMessage":
                            role = "user"
                        elif msg_type == "SystemMessage":
                            role = "system"
                        elif msg_type == "ToolMessage":
                            role = "tool"
                        elif msg_type == "FunctionMessage":
                            role = "function"
                        else:
                            role = msg_type.lower().replace("message", "")

                        message = Message(
                            thread_id=thread_id,
                            role=role,
                            content=str(msg.content) if msg.content else "",
                            meta_data={
                                "type": msg_type,
                                **(msg.additional_kwargs if hasattr(msg, "additional_kwargs") else {}),
                            },
                        )
                        new_session.add(message)

                    # 更新会话时间
                    result = await new_session.execute(select(Conversation).where(Conversation.thread_id == thread_id))
                    conversation = result.scalar_one_or_none()
                    if conversation:
                        conversation.update_time = datetime.utcnow()

                    await new_session.commit()

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

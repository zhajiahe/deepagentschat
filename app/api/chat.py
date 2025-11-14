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

        # 提取助手回复
        assistant_content = graph_result["messages"][-1].content

        # 保存助手回复
        assistant_message = Message(
            thread_id=thread_id,
            role="assistant",
            content=assistant_content,
            meta_data={"duration_ms": duration},
        )
        db.add(assistant_message)

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
        full_response = ""
        try:
            compiled_graph = get_compiled_graph()
            # 使用异步 stream
            async for event in compiled_graph.astream(
                {"messages": [HumanMessage(content=request.message)]}, config, stream_mode="values"
            ):
                if "messages" in event and event["messages"]:
                    last_message = event["messages"][-1]
                    if hasattr(last_message, "content"):
                        chunk = last_message.content
                        full_response = chunk
                        yield f"data: {json.dumps({'content': chunk, 'thread_id': thread_id})}\n\n"

            # 保存完整回复
            if full_response:
                async with AsyncSessionLocal() as new_session:
                    assistant_message = Message(
                        thread_id=thread_id,
                        role="assistant",
                        content=full_response,
                        meta_data={},
                    )
                    new_session.add(assistant_message)

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

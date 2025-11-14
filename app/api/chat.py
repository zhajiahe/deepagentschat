"""
对话 API 路由

提供 LangGraph 对话功能的 API 端点
"""

import asyncio
import json
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain.messages import HumanMessage
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import CurrentUser
from app.core.lifespan import get_compiled_graph
from app.models import Conversation, Message
from app.schemas import ChatRequest, ChatResponse
from app.utils.datetime import utc_now
from app.utils.task_manager import task_manager

router = APIRouter(prefix="/chat", tags=["Chat"])


class StopRequest(BaseModel):
    """停止请求"""

    thread_id: str = Body(..., description="会话线程ID")


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
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
            user_id=current_user.id,  # 使用当前用户ID
            title=request.message[:50] if len(request.message) > 50 else request.message,
            meta_data=request.metadata or {},
        )
        db.add(conversation)
        await db.commit()
    else:
        # 验证会话是否存在且属于当前用户
        result = await db.execute(
            select(Conversation).where(Conversation.thread_id == thread_id, Conversation.user_id == current_user.id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")
        conversation = conv

    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}

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

        # 执行图（异步）- 使用任务包装以便支持取消
        start_time = utc_now()
        compiled_graph = get_compiled_graph()

        # 创建任务并注册
        invoke_task = asyncio.create_task(
            compiled_graph.ainvoke({"messages": [HumanMessage(content=request.message)]}, config)
        )
        await task_manager.register_task(thread_id, invoke_task)

        try:
            graph_result = await invoke_task
        except asyncio.CancelledError as e:
            logger.info(f"Non-stream chat cancelled for thread_id: {thread_id}")
            await task_manager.unregister_task(thread_id)
            raise HTTPException(status_code=499, detail="Chat request was cancelled") from e

        # 检查是否被停止（在任务完成前）
        if await task_manager.is_stopped(thread_id):
            logger.info(f"Non-stream chat stopped for thread_id: {thread_id}")
            await task_manager.unregister_task(thread_id)
            raise HTTPException(status_code=499, detail="Chat request was stopped")

        await task_manager.unregister_task(thread_id)
        duration = (utc_now() - start_time).total_seconds() * 1000

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
            conv_update.update_time = utc_now()

        await db.commit()

        return ChatResponse(thread_id=thread_id, response=assistant_content, duration_ms=int(duration))

    except HTTPException:
        # 重新抛出HTTP异常（如取消、停止等）
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        # 确保注销任务
        await task_manager.unregister_task(thread_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stream")
async def chat_stream(request: ChatRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    异步流式对话接口

    Args:
        request: 对话请求
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        StreamingResponse: 流式响应
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    if not request.thread_id:
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user.id,  # 使用当前用户ID
            title=request.message[:50] if len(request.message) > 50 else request.message,
            meta_data=request.metadata or {},
        )
        db.add(conversation)
        await db.commit()
    else:
        # 验证会话是否属于当前用户
        result = await db.execute(
            select(Conversation).where(Conversation.thread_id == thread_id, Conversation.user_id == current_user.id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")

    # 保存用户消息
    user_message = Message(
        thread_id=thread_id,
        role="user",
        content=request.message,
        meta_data=request.metadata or {},
    )
    db.add(user_message)
    await db.commit()

    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}

    async def event_generator():
        all_messages = []
        stopped = False
        # 注册任务（使用当前协程作为任务标识）
        current_task = asyncio.current_task()
        if current_task:
            await task_manager.register_task(thread_id, current_task)

        try:
            compiled_graph = get_compiled_graph()
            # 使用异步 stream
            async for event in compiled_graph.astream(
                {"messages": [HumanMessage(content=request.message)]}, config, stream_mode="values"
            ):
                # 检查是否被停止
                if await task_manager.is_stopped(thread_id):
                    stopped = True
                    logger.info(f"Stream stopped by user for thread_id: {thread_id}")
                    yield f"data: {json.dumps({'stopped': True, 'thread_id': thread_id})}\n\n"
                    break

                if "messages" in event and event["messages"]:
                    all_messages = event["messages"]
                    last_message = all_messages[-1]
                    if hasattr(last_message, "content"):
                        chunk = last_message.content
                        yield f"data: {json.dumps({'content': chunk, 'thread_id': thread_id})}\n\n"

            # 如果被停止，不保存消息
            if stopped:
                await task_manager.unregister_task(thread_id)
                return

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
                        conversation.update_time = utc_now()

                    await new_session.commit()

            yield f"data: {json.dumps({'done': True})}\n\n"

        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for thread_id: {thread_id}")
            yield f"data: {json.dumps({'stopped': True, 'thread_id': thread_id})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # 确保注销任务
            await task_manager.unregister_task(thread_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/stop")
async def stop_chat(request: StopRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    停止正在进行的流式对话

    Args:
        request: 停止请求，包含 thread_id
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        dict: 停止结果
    """
    thread_id = request.thread_id

    # 验证会话是否属于当前用户
    result = await db.execute(
        select(Conversation).where(Conversation.thread_id == thread_id, Conversation.user_id == current_user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")

    # 尝试停止任务（先标记停止，然后尝试取消）
    stopped = await task_manager.stop_task(thread_id)
    if stopped:
        # 尝试强制取消任务（适用于非流式对话）
        cancelled = await task_manager.cancel_task(thread_id)
        logger.info(
            f"Stop request received for thread_id: {thread_id} by user {current_user.id}, cancelled: {cancelled}"
        )
        return {"status": "stopped", "thread_id": thread_id, "message": "Stop request sent successfully"}
    else:
        # 任务不存在，可能已经完成或从未开始
        return {"status": "not_running", "thread_id": thread_id, "message": "No running task found for this thread"}

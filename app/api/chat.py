"""
对话 API 路由

提供 LangGraph 对话功能的 API 端点
"""

import asyncio
import json
import uuid

from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse
from langchain.messages import HumanMessage
from langchain_core.messages.base import BaseMessage
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import CurrentUser
from app.core.exceptions import (
    raise_client_closed_error,
    raise_internal_error,
    raise_not_found_error,
)
from app.core.lifespan import get_compiled_graph
from app.models import Conversation, Message, UserSettings
from app.models.base import BaseResponse
from app.schemas import ChatRequest, ChatResponse
from app.utils.datetime import utc_now
from app.utils.task_manager import task_manager

router = APIRouter(prefix="/chat", tags=["Chat"])


class StopRequest(BaseModel):
    """停止请求"""

    thread_id: str = Body(..., description="会话线程ID")


def get_role(msg: BaseMessage) -> str:
    """将 LangChain 消息类型映射为标准角色名称"""
    msg_type = type(msg).__name__
    if msg_type == "AIMessage":
        return "assistant"
    elif msg_type == "HumanMessage":
        return "user"
    elif msg_type == "SystemMessage":
        return "system"
    elif msg_type == "ToolMessage":
        return "tool"
    elif msg_type == "FunctionMessage":
        return "function"
    else:
        # 回退到使用消息类型名称
        return msg_type.lower().replace("message", "")


async def get_or_create_conversation(
    thread_id: str | None,
    message: str,
    user_id: uuid.UUID,
    metadata: dict | None,
    db: AsyncSession,
) -> tuple[str, Conversation]:
    """获取或创建会话

    Args:
        thread_id: 会话线程ID（可选）
        message: 消息内容
        user_id: 用户ID
        metadata: 元数据
        db: 数据库会话

    Returns:
        tuple[str, Conversation]: (thread_id, conversation)
    """
    if not thread_id:
        # 创建新会话
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=user_id,
            title=message[:50] if len(message) > 50 else message,
            meta_data=metadata or {},
        )
        db.add(conversation)
        await db.commit()
        return thread_id, conversation
    else:
        # 验证会话是否存在且属于当前用户
        result = await db.execute(
            select(Conversation).where(Conversation.thread_id == thread_id, Conversation.user_id == user_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise_not_found_error("会话")
        # 此时conv肯定不是None
        assert conv is not None
        return thread_id, conv


async def get_user_config(user_id: uuid.UUID, thread_id: str, db: AsyncSession) -> tuple[dict, dict]:
    """获取用户配置

    Args:
        user_id: 用户ID
        thread_id: 会话线程ID
        db: 数据库会话

    Returns:
        tuple[dict, dict]: (config, context)
    """
    config: dict = {"configurable": {"thread_id": thread_id, "user_id": str(user_id)}}
    context: dict = {}

    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = result.scalar_one_or_none()

    if user_settings:
        config["configurable"].update(user_settings.config or {})
        context = user_settings.context or {}

    return config, context


async def save_user_message(thread_id: str, message: str, metadata: dict | None, db: AsyncSession) -> None:
    """保存用户消息

    Args:
        thread_id: 会话线程ID
        message: 消息内容
        metadata: 元数据
        db: 数据库会话
    """
    user_message = Message(
        thread_id=thread_id,
        role="user",
        content=message,
        meta_data=metadata or {},
    )
    db.add(user_message)
    await db.commit()


async def save_assistant_message(
    thread_id: str, messages: list[BaseMessage], db: AsyncSession, update_conversation: bool = True
) -> None:
    """保存助手消息并更新会话时间

    Args:
        thread_id: 会话线程ID
        messages: 消息列表
        db: 数据库会话
        update_conversation: 是否更新会话时间
    """
    if not messages:
        return

    last_message = messages[-1]
    role = get_role(last_message)

    # 只保存助手消息，避免重复保存用户消息
    if role == "assistant":
        message = Message(
            thread_id=thread_id,
            role=role,
            content=str(last_message.content) if last_message.content else "",
            meta_data=last_message.additional_kwargs,
        )
        db.add(message)

    # 更新会话时间
    if update_conversation:
        result = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.update_time = utc_now()

    await db.commit()


@router.post("", response_model=BaseResponse[ChatResponse])
async def chat(request: ChatRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    异步对话接口 (非流式)

    Args:
        request: 对话请求
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ChatResponse: 对话响应
    """
    # 获取或创建会话
    thread_id, _ = await get_or_create_conversation(
        request.thread_id, request.message, current_user.id, request.metadata, db
    )

    # 获取用户配置
    config, context = await get_user_config(current_user.id, thread_id, db)

    try:
        # 保存用户消息
        await save_user_message(thread_id, request.message, request.metadata, db)

        # 执行图（异步）- 使用任务包装以便支持取消
        start_time = utc_now()
        compiled_graph = get_compiled_graph()

        # 创建任务并注册
        invoke_task = asyncio.create_task(
            compiled_graph.ainvoke(
                {"messages": [HumanMessage(content=request.message)]},
                config=config,
                context=context,
            )
        )
        await task_manager.register_task(thread_id, invoke_task)

        try:
            graph_result = await invoke_task
        except asyncio.CancelledError:
            logger.info(f"Non-stream chat cancelled for thread_id: {thread_id}")
            await task_manager.unregister_task(thread_id)
            raise_client_closed_error("对话请求已被取消")

        # 检查是否被停止（在任务完成前）
        if await task_manager.is_stopped(thread_id):
            logger.info(f"Non-stream chat stopped for thread_id: {thread_id}")
            await task_manager.unregister_task(thread_id)
            raise_client_closed_error("对话请求已被停止")

        await task_manager.unregister_task(thread_id)
        duration = (utc_now() - start_time).total_seconds() * 1000

        # 保存助手消息并更新会话时间
        result_messages = graph_result["messages"]
        await save_assistant_message(thread_id, result_messages, db, update_conversation=True)

        # 提取最后一条助手回复用于响应
        assistant_content = result_messages[-1].content if result_messages else ""

        return BaseResponse(
            success=True,
            code=200,
            msg="对话成功",
            data=ChatResponse(thread_id=thread_id, response=assistant_content, duration_ms=int(duration)),
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        # 确保注销任务
        await task_manager.unregister_task(thread_id)
        raise_internal_error(str(e))


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
    # 获取或创建会话
    thread_id, _ = await get_or_create_conversation(
        request.thread_id, request.message, current_user.id, request.metadata, db
    )

    # 保存用户消息
    await save_user_message(thread_id, request.message, request.metadata, db)

    # 获取用户配置
    config, context = await get_user_config(current_user.id, thread_id, db)

    async def event_generator():
        all_messages = []
        stopped = False
        assistant_content = ""  # 累积助手消息内容
        # 注册任务（使用当前协程作为任务标识）
        current_task = asyncio.current_task()
        if current_task:
            await task_manager.register_task(thread_id, current_task)

        try:
            compiled_graph = get_compiled_graph()
            # 使用 astream_events 获取逐token流式输出
            async for event in compiled_graph.astream_events(
                {"messages": [HumanMessage(content=request.message)]},
                config=config,
                context=context,
                version="v2",
            ):
                # 检查是否被停止
                if await task_manager.is_stopped(thread_id):
                    stopped = True
                    logger.info(f"Stream stopped by user for thread_id: {thread_id}")
                    yield f"data: {json.dumps({'stopped': True, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"
                    break

                # 处理不同类型的事件
                event_type = event.get("event")

                # 处理 LLM token 流
                if event_type == "on_chat_model_stream":
                    chunk_data = event.get("data", {})
                    if "chunk" in chunk_data:
                        chunk_obj = chunk_data["chunk"]
                        if hasattr(chunk_obj, "content") and chunk_obj.content:
                            chunk_text = chunk_obj.content
                            assistant_content += chunk_text
                            # 发送增量内容
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk_text, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                # 处理工具调用开始
                elif event_type == "on_tool_start":
                    tool_data = event.get("data", {})
                    tool_name = event.get("name", "unknown")
                    tool_input = tool_data.get("input", {})
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': tool_name, 'tool_input': tool_input, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                # 处理工具调用结束
                elif event_type == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_name = event.get("name", "unknown")
                    tool_output = tool_data.get("output")
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool_name': tool_name, 'tool_output': str(tool_output), 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                # 收集最终消息用于保存
                elif event_type == "on_chain_end":
                    output = event.get("data", {}).get("output", {})
                    if "messages" in output:
                        messages = output["messages"]
                        if messages:
                            all_messages = messages

            # 如果被停止，不保存消息
            if stopped:
                await task_manager.unregister_task(thread_id)
                return

            # 保存助手消息并更新会话时间
            if all_messages:
                async with AsyncSessionLocal() as new_session:
                    await save_assistant_message(thread_id, all_messages, new_session, update_conversation=True)

            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for thread_id: {thread_id}")
            yield f"data: {json.dumps({'stopped': True, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            # 确保注销任务
            await task_manager.unregister_task(thread_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/stop")
async def stop_chat(request: StopRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    停止正在进行的对话请求

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
        raise_not_found_error("会话")

    # 尝试停止任务（先标记停止，然后尝试取消）
    stopped = await task_manager.stop_task(thread_id)
    if stopped:
        # 尝试强制取消任务（适用于非流式对话）
        cancelled = await task_manager.cancel_task(thread_id)
        logger.info(
            f"Stop request received for thread_id: {thread_id} by user {current_user.id}, cancelled: {cancelled}"
        )
        return BaseResponse(
            success=True, code=200, msg="停止请求已发送", data={"status": "stopped", "thread_id": thread_id}
        )
    else:
        # 任务不存在，可能已经完成或从未开始
        return BaseResponse(
            success=True, code=200, msg="没有找到正在运行的任务", data={"status": "not_running", "thread_id": thread_id}
        )

"""
会话管理 API 路由

提供会话的 CRUD、状态管理、导出导入等功能
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.lifespan import get_compiled_graph
from app.models import Conversation, Message
from app.schemas import (
    ChatResponse,
    CheckpointResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationExportResponse,
    ConversationImportRequest,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    SearchRequest,
    SearchResponse,
    StateResponse,
    UserStatsResponse,
)
from app.utils.datetime import utc_now

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ============= 辅助函数 =============


async def verify_conversation_ownership(thread_id: str, user_id: uuid.UUID, db: AsyncSession) -> Conversation:
    """验证会话所有权"""
    result = await db.execute(
        select(Conversation).where(Conversation.thread_id == thread_id, Conversation.user_id == user_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    return conversation


# ============= 会话管理接口 =============


@router.post("", response_model=ConversationResponse)
async def create_conversation(conv: ConversationCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    创建新会话

    Args:
        conv: 会话创建请求
        db: 数据库会话

    Returns:
        ConversationResponse: 会话响应
    """
    conversation = Conversation(
        thread_id=str(uuid.uuid4()),
        user_id=current_user.id,  # 使用当前用户ID
        title=conv.title,
        meta_data=conv.metadata or {},
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationResponse(
        id=conversation.id,
        thread_id=conversation.thread_id,
        user_id=conversation.user_id,
        title=conversation.title,
        metadata=conversation.meta_data or {},
        created_at=conversation.create_time,
        updated_at=conversation.update_time,
        message_count=0,
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: CurrentUser, skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    """
    获取用户的会话列表

    Args:
        user_id: 用户ID
        skip: 跳过数量
        limit: 返回数量
        db: 数据库会话

    Returns:
        list[ConversationResponse]: 会话列表
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_active == 1)
        .order_by(Conversation.update_time.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()

    response_list = []
    for conv in conversations:
        # 获取消息数量
        count_result = await db.execute(select(func.count(Message.id)).where(Message.thread_id == conv.thread_id))
        message_count = count_result.scalar() or 0

        response_list.append(
            ConversationResponse(
                id=conv.id,
                thread_id=conv.thread_id,
                user_id=conv.user_id,
                title=conv.title,
                metadata=conv.meta_data or {},
                created_at=conv.create_time,
                updated_at=conv.update_time,
                message_count=message_count,
            )
        )

    return response_list


@router.get("/{thread_id}", response_model=ConversationDetailResponse)
async def get_conversation(thread_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    获取单个会话详情

    Args:
        thread_id: 线程ID
        db: 数据库会话

    Returns:
        ConversationDetailResponse: 会话详情
    """
    # 验证会话所有权
    conversation = await verify_conversation_ownership(thread_id, current_user.id, db)

    messages_result = await db.execute(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.create_time)
    )
    messages = messages_result.scalars().all()

    conv_response = ConversationResponse(
        id=conversation.id,
        thread_id=conversation.thread_id,
        user_id=conversation.user_id,
        title=conversation.title,
        metadata=conversation.meta_data or {},
        created_at=conversation.create_time,
        updated_at=conversation.update_time,
        message_count=len(messages),
    )

    messages_data = [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "metadata": msg.meta_data or {},
            "created_at": msg.create_time.isoformat(),
        }
        for msg in messages
    ]

    return ConversationDetailResponse(conversation=conv_response, messages=messages_data)


@router.patch("/{thread_id}")
async def update_conversation(
    thread_id: str, update: ConversationUpdate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    """
    更新会话信息

    Args:
        thread_id: 线程ID
        update: 更新数据
        db: 数据库会话

    Returns:
        dict: 更新状态
    """
    # 验证会话所有权
    conversation = await verify_conversation_ownership(thread_id, current_user.id, db)

    if update.title is not None:
        conversation.title = update.title
    if update.metadata is not None:
        conversation.meta_data = update.metadata

    conversation.update_time = utc_now()
    await db.commit()

    return {"status": "updated", "thread_id": thread_id}


@router.delete("/{thread_id}")
async def delete_conversation(
    thread_id: str, current_user: CurrentUser, hard_delete: bool = False, db: AsyncSession = Depends(get_db)
):
    """
    删除会话（软删除或硬删除）

    Args:
        thread_id: 线程ID
        hard_delete: 是否硬删除
        db: 数据库会话

    Returns:
        dict: 删除状态
    """
    # 验证会话所有权
    conversation = await verify_conversation_ownership(thread_id, current_user.id, db)

    if hard_delete:
        # 硬删除：删除所有相关数据
        # 先删除检查点
        from app.core.checkpointer import delete_thread_checkpoints

        try:
            await delete_thread_checkpoints(thread_id)
        except Exception as e:
            logger.warning(f"Failed to delete checkpoints: {e}")

        # 删除消息
        await db.execute(delete(Message).where(Message.thread_id == thread_id))
        await db.delete(conversation)
    else:
        # 软删除
        conversation.is_active = 0

    await db.commit()
    return {"status": "deleted", "thread_id": thread_id}


@router.post("/{thread_id}/reset")
async def reset_conversation(thread_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    重置对话：清除所有检查点和消息记录，但保留会话记录

    重置后，会话将回到初始状态，可以重新开始对话。

    Args:
        thread_id: 线程ID
        current_user: 当前用户
        db: 数据库会话

    Returns:
        dict: 重置状态
    """
    # 验证会话所有权
    conversation = await verify_conversation_ownership(thread_id, current_user.id, db)

    try:
        # 1. 删除 LangGraph 检查点
        from app.core.checkpointer import delete_thread_checkpoints

        await delete_thread_checkpoints(thread_id)
        logger.info(f"✅ Deleted LangGraph checkpoints for thread: {thread_id}")

        # 2. 删除所有消息记录
        result = await db.execute(delete(Message).where(Message.thread_id == thread_id))
        # 获取删除的行数（SQLAlchemy 2.0+ 的 Result 对象有 rowcount 属性）
        deleted_count = getattr(result, "rowcount", 0)
        logger.info(f"✅ Deleted {deleted_count} messages for thread: {thread_id}")

        # 3. 更新会话时间戳
        conversation.update_time = utc_now()

        await db.commit()

        return {
            "status": "reset",
            "thread_id": thread_id,
            "message": f"Conversation reset successfully. Deleted {deleted_count} messages.",
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to reset conversation {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset conversation: {str(e)}") from e


# ============= 消息管理接口 =============


@router.get("/{thread_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    thread_id: str, current_user: CurrentUser, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    """
    获取会话消息历史

    Args:
        thread_id: 线程ID
        skip: 跳过数量
        limit: 返回数量
        db: 数据库会话

    Returns:
        list[MessageResponse]: 消息列表
    """
    # 验证会话所有权
    await verify_conversation_ownership(thread_id, current_user.id, db)

    result = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.create_time.desc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            metadata=msg.meta_data or {},
            created_at=msg.create_time,
        )
        for msg in reversed(list(messages))
    ]


# ============= 消息管理接口 =============


@router.post("/{thread_id}/messages/{message_id}/regenerate", response_model=ChatResponse)
async def regenerate_message(
    thread_id: str,
    message_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    重新生成指定消息的回复

    Args:
        thread_id: 线程ID
        message_id: 消息ID（要重新生成的助手消息）
        current_user: 当前用户
        db: 数据库会话

    Returns:
        ChatResponse: 新的回复
    """
    from langchain.messages import HumanMessage

    # 验证会话所有权
    await verify_conversation_ownership(thread_id, current_user.id, db)

    # 获取要重新生成的消息
    result = await db.execute(select(Message).where(Message.id == message_id, Message.thread_id == thread_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.role != "assistant":
        raise HTTPException(status_code=400, detail="只能重新生成助手消息")

    # 找到该消息之前的用户消息
    result = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_id, Message.create_time < message.create_time, Message.role == "user")
        .order_by(Message.create_time.desc())
        .limit(1)
    )
    user_message = result.scalar_one_or_none()

    if not user_message:
        raise HTTPException(status_code=400, detail="找不到对应的用户消息")

    # 删除该消息及之后的所有消息（先提交删除操作）
    await db.execute(delete(Message).where(Message.thread_id == thread_id, Message.create_time >= message.create_time))
    await db.commit()  # 先提交删除操作

    # 删除 LangGraph 检查点（从该消息之后）
    from app.core.checkpointer import delete_thread_checkpoints

    try:
        await delete_thread_checkpoints(thread_id)
        logger.info(f"✅ Deleted LangGraph checkpoints for thread: {thread_id}")
    except Exception as e:
        logger.warning(f"Failed to delete checkpoints: {e}")

    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}

    try:
        # 重新执行图
        start_time = utc_now()
        compiled_graph = get_compiled_graph()
        graph_result = await compiled_graph.ainvoke({"messages": [HumanMessage(content=user_message.content)]}, config)
        duration = (utc_now() - start_time).total_seconds() * 1000

        # 保存新产生的消息
        result_messages = graph_result["messages"]

        # 从第二条消息开始保存（第一条是用户消息）
        for msg in result_messages[1:]:
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

            new_message = Message(
                thread_id=thread_id,
                role=role,
                content=str(msg.content) if msg.content else "",
                meta_data={
                    "type": msg_type,
                    **(msg.additional_kwargs if hasattr(msg, "additional_kwargs") else {}),
                },
            )
            db.add(new_message)

        # 提取最后一条助手回复
        assistant_content = result_messages[-1].content

        # 更新会话时间
        result_conv = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
        conv_update = result_conv.scalar_one_or_none()
        if conv_update:
            conv_update.update_time = utc_now()

        await db.commit()

        return ChatResponse(thread_id=thread_id, response=assistant_content, duration_ms=int(duration))

    except Exception as e:
        await db.rollback()
        logger.error(f"Regenerate error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============= 状态管理接口 =============


@router.get("/{thread_id}/state", response_model=StateResponse)
async def get_state(thread_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    获取会话的 LangGraph 状态

    Args:
        thread_id: 线程ID

    Returns:
        StateResponse: 状态响应
    """
    # 验证会话所有权
    await verify_conversation_ownership(thread_id, current_user.id, db)

    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}
    try:
        compiled_graph = get_compiled_graph()
        state = await compiled_graph.aget_state(config)

        # 处理 created_at，可能已经是字符串或 datetime 对象
        created_at_str = None
        if state.created_at:
            if isinstance(state.created_at, str):
                created_at_str = state.created_at
            elif hasattr(state.created_at, "isoformat"):
                created_at_str = state.created_at.isoformat()
            else:
                created_at_str = str(state.created_at)

        return StateResponse(
            thread_id=thread_id,
            values=state.values,
            next=state.next,
            metadata=state.metadata,
            created_at=created_at_str,
            parent_config=state.parent_config,
        )
    except Exception as e:
        logger.error(f"Get state error: {e}")
        raise HTTPException(status_code=404, detail=f"State not found: {str(e)}") from e


@router.get("/{thread_id}/checkpoints", response_model=CheckpointResponse)
async def get_checkpoints(
    thread_id: str, current_user: CurrentUser, limit: int = 10, db: AsyncSession = Depends(get_db)
):
    """
    获取会话的所有检查点

    Args:
        thread_id: 线程ID
        limit: 返回数量

    Returns:
        CheckpointResponse: 检查点响应
    """
    # 验证会话所有权
    await verify_conversation_ownership(thread_id, current_user.id, db)

    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}
    try:
        compiled_graph = get_compiled_graph()
        checkpoints = []
        async for checkpoint in compiled_graph.aget_state_history(config):
            checkpoints.append(
                {
                    "checkpoint_id": checkpoint.config["configurable"].get("checkpoint_id"),
                    "values": checkpoint.values,
                    "next": checkpoint.next,
                    "metadata": checkpoint.metadata,
                    "created_at": checkpoint.created_at.isoformat() if checkpoint.created_at else None,
                }
            )
            if len(checkpoints) >= limit:
                break

        return CheckpointResponse(thread_id=thread_id, checkpoints=checkpoints)
    except Exception as e:
        logger.error(f"Get checkpoints error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============= 导出/导入接口 =============


@router.get("/{thread_id}/export", response_model=ConversationExportResponse)
async def export_conversation(thread_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    导出会话数据

    Args:
        thread_id: 线程ID
        db: 数据库会话

    Returns:
        ConversationExportResponse: 导出数据
    """
    # 验证会话所有权
    conversation = await verify_conversation_ownership(thread_id, current_user.id, db)

    messages_result = await db.execute(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.create_time)
    )
    messages = messages_result.scalars().all()

    # 获取 LangGraph 状态
    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}
    try:
        compiled_graph = get_compiled_graph()
        state = await compiled_graph.aget_state(config)
        state_values = state.values
    except Exception:
        state_values = None

    return ConversationExportResponse(
        conversation={
            "thread_id": conversation.thread_id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "metadata": conversation.meta_data or {},
            "created_at": conversation.create_time.isoformat(),
            "updated_at": conversation.update_time.isoformat(),
        },
        messages=[
            {
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.meta_data or {},
                "created_at": msg.create_time.isoformat(),
            }
            for msg in messages
        ],
        state=state_values,
    )


@router.post("/import")
async def import_conversation(
    request: ConversationImportRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    """
    导入会话数据

    Args:
        request: 导入请求
        db: 数据库会话

    Returns:
        dict: 导入状态
    """
    data = request.data
    thread_id = str(uuid.uuid4())

    # 创建会话
    conversation = Conversation(
        thread_id=thread_id,
        user_id=current_user.id,  # 使用当前用户ID
        title=data["conversation"]["title"],
        meta_data=data["conversation"].get("metadata", {}),
    )
    db.add(conversation)

    # 导入消息
    for msg_data in data["messages"]:
        message = Message(
            thread_id=thread_id,
            role=msg_data["role"],
            content=msg_data["content"],
            meta_data=msg_data.get("metadata", {}),
        )
        db.add(message)

    await db.commit()

    # 恢复 LangGraph 状态
    if "state" in data and data["state"]:
        config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}
        try:
            compiled_graph = get_compiled_graph()
            await compiled_graph.aupdate_state(config, data["state"])
        except Exception as e:
            logger.warning(f"Could not restore state: {e}")

    return {"thread_id": thread_id, "status": "imported"}


# ============= 搜索接口 =============


@router.post("/search", response_model=SearchResponse)
async def search_conversations(request: SearchRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    搜索会话和消息

    Args:
        request: 搜索请求
        db: 数据库会话

    Returns:
        SearchResponse: 搜索结果
    """
    # 使用 SQLite LIKE 搜索
    result = await db.execute(
        select(Message)
        .join(Conversation, Message.thread_id == Conversation.thread_id)
        .where(Message.content.like(f"%{request.query}%"), Conversation.user_id == current_user.id)
        .order_by(Message.create_time.desc())
        .offset(request.skip)
        .limit(request.limit)
    )
    messages = result.scalars().all()

    results = []
    for msg in messages:
        conv_result = await db.execute(select(Conversation).where(Conversation.thread_id == msg.thread_id))
        conversation = conv_result.scalar_one_or_none()

        results.append(
            {
                "message_id": msg.id,
                "thread_id": msg.thread_id,
                "conversation_title": conversation.title if conversation else "",
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.create_time.isoformat(),
            }
        )

    return SearchResponse(query=request.query, results=results)


# ============= 统计接口 =============


@router.get("/users/stats", response_model=UserStatsResponse)
async def get_user_stats(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    获取用户统计信息

    Args:
        user_id: 用户ID
        db: 数据库会话

    Returns:
        UserStatsResponse: 用户统计
    """
    # 总会话数
    conv_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id, Conversation.is_active == 1)
    )
    total_conversations = conv_result.scalar() or 0

    # 总消息数
    msg_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation, Message.thread_id == Conversation.thread_id)
        .where(Conversation.user_id == current_user.id)
    )
    total_messages = msg_result.scalar() or 0

    # 最近会话
    recent_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_active == 1)
        .order_by(Conversation.update_time.desc())
        .limit(5)
    )
    recent_conversations = recent_result.scalars().all()

    return UserStatsResponse(
        user_id=str(current_user.id),
        total_conversations=total_conversations,
        total_messages=total_messages,
        recent_conversations=[
            {"thread_id": conv.thread_id, "title": conv.title, "updated_at": conv.update_time.isoformat()}
            for conv in recent_conversations
        ],
    )

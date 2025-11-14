"""
会话管理 API 路由

提供会话的 CRUD、状态管理、导出导入等功能
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.lifespan import get_compiled_graph
from app.models import BasePageQuery, Conversation, Message, PageResponse
from app.schemas import (
    CheckpointResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationExportResponse,
    ConversationImportRequest,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    SearchResponse,
    StateResponse,
    StateUpdateRequest,
    UserStatsResponse,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ============= 会话管理接口 =============


@router.post("", response_model=ConversationResponse)
async def create_conversation(conv: ConversationCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    创建新会话 (需要认证)

    Args:
        conv: 会话创建请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        ConversationResponse: 会话响应
    """
    conversation = Conversation(
        thread_id=str(uuid.uuid4()),
        user_id=current_user.id,  # 使用当前登录用户的ID
        title=conv.title,
        meta_data=conv.metadata or {},
        create_by=current_user.username,
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


@router.get("", response_model=PageResponse[ConversationResponse])
async def list_conversations(
    current_user: CurrentUser,
    page_num: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的会话列表 (需要认证,分页)

    Args:
        current_user: 当前用户
        page_num: 页码
        page_size: 每页数量
        db: 数据库会话

    Returns:
        PageResponse[ConversationResponse]: 分页会话列表
    """
    # 创建分页查询对象
    page_query = BasePageQuery(page_num=page_num, page_size=page_size)

    # 查询总数
    count_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id, Conversation.deleted == 0)
    )
    total = count_result.scalar() or 0

    # 查询数据
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.deleted == 0)
        .order_by(Conversation.update_time.desc())
        .offset(page_query.offset)
        .limit(page_query.limit)
    )
    conversations = result.scalars().all()

    # 构建响应
    items = []
    for conv in conversations:
        # 获取消息数量
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.thread_id == conv.thread_id, Message.deleted == 0)
        )
        message_count = count_result.scalar() or 0

        items.append(
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

    return PageResponse(page_num=page_num, page_size=page_size, total=total, items=items)


@router.get("/{thread_id}", response_model=ConversationDetailResponse)
async def get_conversation(thread_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    获取单个会话详情 (需要认证)

    Args:
        thread_id: 线程ID
        current_user: 当前用户
        db: 数据库会话

    Returns:
        ConversationDetailResponse: 会话详情
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.thread_id == thread_id, Conversation.user_id == current_user.id, Conversation.deleted == 0
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(Message).where(Message.thread_id == thread_id, Message.deleted == 0).order_by(Message.create_time)
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
    更新会话信息 (需要认证)

    Args:
        thread_id: 线程ID
        update: 更新数据
        current_user: 当前用户
        db: 数据库会话

    Returns:
        dict: 更新状态
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.thread_id == thread_id, Conversation.user_id == current_user.id, Conversation.deleted == 0
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if update.title is not None:
        conversation.title = update.title
    if update.metadata is not None:
        conversation.meta_data = update.metadata

    conversation.update_time = datetime.utcnow()
    conversation.update_by = current_user.username
    await db.commit()

    return {"status": "updated", "thread_id": thread_id}


@router.delete("/{thread_id}")
async def delete_conversation(thread_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    删除会话 (软删除,需要认证)

    Args:
        thread_id: 线程ID
        current_user: 当前用户
        db: 数据库会话

    Returns:
        dict: 删除状态
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.thread_id == thread_id, Conversation.user_id == current_user.id, Conversation.deleted == 0
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 软删除
    conversation.deleted = 1
    conversation.update_by = current_user.username
    await db.commit()

    return {"status": "deleted", "thread_id": thread_id}


# ============= 消息管理接口 =============


@router.get("/{thread_id}/messages", response_model=PageResponse[MessageResponse])
async def get_messages(
    thread_id: str,
    current_user: CurrentUser,
    page_num: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话消息历史 (需要认证,分页)

    Args:
        thread_id: 线程ID
        current_user: 当前用户
        page_num: 页码
        page_size: 每页数量
        db: 数据库会话

    Returns:
        PageResponse[MessageResponse]: 分页消息列表
    """
    # 验证会话所有权
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.thread_id == thread_id, Conversation.user_id == current_user.id, Conversation.deleted == 0
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 创建分页查询对象
    page_query = BasePageQuery(page_num=page_num, page_size=page_size)

    # 查询总数
    count_result = await db.execute(
        select(func.count(Message.id)).where(Message.thread_id == thread_id, Message.deleted == 0)
    )
    total = count_result.scalar() or 0

    # 查询数据
    result = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_id, Message.deleted == 0)
        .order_by(Message.create_time.asc())
        .offset(page_query.offset)
        .limit(page_query.limit)
    )
    messages = result.scalars().all()

    items = [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            metadata=msg.meta_data or {},
            created_at=msg.create_time,
        )
        for msg in messages
    ]

    return PageResponse(page_num=page_num, page_size=page_size, total=total, items=items)


# ============= 状态管理接口 =============


@router.get("/{thread_id}/state", response_model=StateResponse)
async def get_state(thread_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    获取会话的 LangGraph 状态 (需要认证)

    Args:
        thread_id: 线程ID
        current_user: 当前用户
        db: 数据库会话

    Returns:
        StateResponse: 状态响应
    """
    # 验证会话所有权
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.thread_id == thread_id, Conversation.user_id == current_user.id, Conversation.deleted == 0
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    config = {"configurable": {"thread_id": thread_id}}
    try:
        compiled_graph = get_compiled_graph()
        state = await compiled_graph.aget_state(config)
        return StateResponse(
            thread_id=thread_id,
            values=state.values,
            next=state.next,
            metadata=state.metadata,
            created_at=state.created_at.isoformat() if state.created_at else None,
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
    获取会话的所有检查点 (需要认证)

    Args:
        thread_id: 线程ID
        current_user: 当前用户
        limit: 返回数量
        db: 数据库会话

    Returns:
        CheckpointResponse: 检查点响应
    """
    # 验证会话所有权
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.thread_id == thread_id, Conversation.user_id == current_user.id, Conversation.deleted == 0
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    config = {"configurable": {"thread_id": thread_id}}
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


@router.post("/{thread_id}/update-state")
async def update_state(
    thread_id: str, request: StateUpdateRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    """
    更新会话状态 (需要认证)

    Args:
        thread_id: 线程ID
        request: 状态更新请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        dict: 更新状态
    """
    # 验证会话所有权
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.thread_id == thread_id, Conversation.user_id == current_user.id, Conversation.deleted == 0
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    config = {"configurable": {"thread_id": thread_id}}

    try:
        compiled_graph = get_compiled_graph()
        await compiled_graph.aupdate_state(config, request.state_update, as_node=request.as_node)
        return {"status": "updated", "thread_id": thread_id}
    except Exception as e:
        logger.error(f"Update state error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============= 导出/导入接口 =============


@router.get("/{thread_id}/export", response_model=ConversationExportResponse)
async def export_conversation(thread_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    导出会话数据 (需要认证)

    Args:
        thread_id: 线程ID
        current_user: 当前用户
        db: 数据库会话

    Returns:
        ConversationExportResponse: 导出数据
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.thread_id == thread_id, Conversation.user_id == current_user.id, Conversation.deleted == 0
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(Message).where(Message.thread_id == thread_id, Message.deleted == 0).order_by(Message.create_time)
    )
    messages = messages_result.scalars().all()

    # 获取 LangGraph 状态
    config = {"configurable": {"thread_id": thread_id}}
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
    导入会话数据 (需要认证)

    Args:
        request: 导入请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        dict: 导入状态
    """
    data = request.data
    thread_id = str(uuid.uuid4())

    # 创建会话
    conversation = Conversation(
        thread_id=thread_id,
        user_id=current_user.id,  # 使用当前登录用户的ID
        title=data["conversation"]["title"],
        meta_data=data["conversation"].get("metadata", {}),
        create_by=current_user.username,
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
        config = {"configurable": {"thread_id": thread_id}}
        try:
            compiled_graph = get_compiled_graph()
            await compiled_graph.aupdate_state(config, data["state"])
        except Exception as e:
            logger.warning(f"Could not restore state: {e}")

    return {"thread_id": thread_id, "status": "imported"}


# ============= 搜索接口 =============


@router.get("/search", response_model=SearchResponse)
async def search_conversations(
    query: str = Query(..., description="搜索关键词"),
    current_user: CurrentUser = Depends(),
    page_num: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    搜索会话和消息 (需要认证)

    Args:
        query: 搜索关键词
        current_user: 当前用户
        page_num: 页码
        page_size: 每页数量
        db: 数据库会话

    Returns:
        SearchResponse: 搜索结果
    """
    # 创建分页查询对象
    page_query = BasePageQuery(page_num=page_num, page_size=page_size)

    # 使用 SQLite LIKE 搜索
    result = await db.execute(
        select(Message)
        .join(Conversation, Message.thread_id == Conversation.thread_id)
        .where(
            Message.content.like(f"%{query}%"),
            Conversation.user_id == current_user.id,
            Message.deleted == 0,
            Conversation.deleted == 0,
        )
        .order_by(Message.create_time.desc())
        .offset(page_query.offset)
        .limit(page_query.limit)
    )
    messages = result.scalars().all()

    results = []
    for msg in messages:
        conv_result = await db.execute(
            select(Conversation).where(Conversation.thread_id == msg.thread_id, Conversation.deleted == 0)
        )
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

    return SearchResponse(query=query, results=results)


# ============= 统计接口 =============


@router.get("/users/stats", response_model=UserStatsResponse)
async def get_user_stats(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    获取当前用户统计信息 (需要认证)

    Args:
        current_user: 当前用户
        db: 数据库会话

    Returns:
        UserStatsResponse: 用户统计
    """
    # 总会话数
    conv_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id, Conversation.deleted == 0)
    )
    total_conversations = conv_result.scalar() or 0

    # 总消息数
    msg_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation, Message.thread_id == Conversation.thread_id)
        .where(Conversation.user_id == current_user.id, Message.deleted == 0, Conversation.deleted == 0)
    )
    total_messages = msg_result.scalar() or 0

    # 最近会话
    recent_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.deleted == 0)
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

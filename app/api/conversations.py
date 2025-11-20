"""
会话管理 API 路由

提供会话的 CRUD、状态管理、导出导入等功能
"""

import uuid

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat import serialize_messages
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.exceptions import raise_internal_error, raise_not_found_error
from app.core.lifespan import get_cached_graph, get_compiled_graph
from app.models import Conversation, Message
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas import (
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
        raise_not_found_error("会话")
    # 此时conversation肯定不是None
    assert conversation is not None
    return conversation


# ============= 会话管理接口 =============


@router.post("", response_model=BaseResponse[ConversationResponse])
async def create_conversation(
    conv: ConversationCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
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

    return BaseResponse(
        success=True,
        code=201,
        msg="创建会话成功",
        data=ConversationResponse(
            id=conversation.id,
            thread_id=conversation.thread_id,
            user_id=conversation.user_id,
            title=conversation.title,
            metadata=conversation.meta_data or {},
            created_at=conversation.create_time,
            updated_at=conversation.update_time,
            message_count=0,
        ),
    )


@router.get("", response_model=BaseResponse[PageResponse[ConversationResponse]])
async def list_conversations(
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户的会话列表

    Args:
        current_user: 当前用户
        page_query: 分页参数（page_num, page_size）
        db: 数据库会话

    Returns:
        PageResponse[ConversationResponse]: 分页的会话列表
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_active == 1)
        .order_by(Conversation.update_time.desc())
        .offset(page_query.offset)
        .limit(page_query.limit)
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

    # 获取总数
    total_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id, Conversation.is_active == 1)
    )
    total = total_result.scalar() or 0

    return BaseResponse(
        success=True,
        code=200,
        msg="获取会话列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=total,
            items=response_list,
        ),
    )


@router.delete("/all", summary="删除所有历史会话")
async def delete_all_conversations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    hard_delete: bool = True,
) -> BaseResponse:
    """删除当前用户的所有历史会话

    Args:
        current_user: 当前登录用户
        db: 数据库会话
        hard_delete: 是否硬删除（彻底删除），默认为硬删除

    Returns:
        BaseResponse: 删除结果
    """
    # 获取用户的所有会话
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == current_user.id, Conversation.is_active == 1)
    )
    conversations = result.scalars().all()

    if not conversations:
        return BaseResponse(
            success=True,
            code=200,
            msg="没有需要删除的会话",
            data={"deleted_count": 0},
        )

    deleted_count = 0

    if hard_delete:
        # 硬删除：删除所有会话及其相关数据
        from app.core.checkpointer import delete_thread_checkpoints

        for conversation in conversations:
            try:
                # 删除检查点
                await delete_thread_checkpoints(conversation.thread_id)
            except Exception as e:
                logger.warning(f"Failed to delete checkpoints for {conversation.thread_id}: {e}")

            # 删除会话（消息会通过 cascade 自动删除）
            await db.delete(conversation)
            deleted_count += 1
    else:
        # 软删除：将所有会话标记为不活跃
        for conversation in conversations:
            conversation.is_active = 0
            deleted_count += 1

    await db.commit()

    return BaseResponse(
        success=True,
        code=200,
        msg=f"成功删除 {deleted_count} 个会话",
        data={
            "deleted_count": deleted_count,
            "hard_delete": hard_delete,
        },
    )


@router.get("/{thread_id}", response_model=BaseResponse[ConversationDetailResponse])
async def get_conversation(
    thread_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
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

    return BaseResponse(
        success=True,
        code=200,
        msg="获取会话详情成功",
        data=ConversationDetailResponse(conversation=conv_response, messages=messages_data),
    )


@router.patch("/{thread_id}", response_model=BaseResponse[dict])
async def update_conversation(
    thread_id: str,
    update: ConversationUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
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

    return BaseResponse(
        success=True,
        code=200,
        msg="更新会话成功",
        data={"status": "updated", "thread_id": thread_id},
    )


@router.delete("/{thread_id}", response_model=BaseResponse[dict])
async def delete_conversation(
    thread_id: str,
    current_user: CurrentUser,
    hard_delete: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    删除会话（软删除或硬删除），默认硬删除

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

        # 删除会话（消息会通过 cascade 自动删除）
        await db.delete(conversation)
    else:
        # 软删除
        conversation.is_active = 0

    await db.commit()
    return BaseResponse(
        success=True,
        code=200,
        msg="删除会话成功",
        data={"status": "deleted", "thread_id": thread_id},
    )


@router.post("/{thread_id}/reset")
async def reset_conversation(
    thread_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
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
        # 删除 LangGraph 检查点（消息存储在 checkpoint 中）
        from app.core.checkpointer import delete_thread_checkpoints

        await delete_thread_checkpoints(thread_id)
        logger.info(f"✅ Deleted LangGraph checkpoints for thread: {thread_id}")

        # 更新会话时间戳
        conversation.update_time = utc_now()
        await db.commit()

        return BaseResponse(
            success=True,
            code=200,
            msg="会话已重置",
            data={
                "status": "reset",
                "thread_id": thread_id,
            },
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to reset conversation {thread_id}: {e}")
        raise_internal_error(f"重置会话失败: {str(e)}")


# ============= 消息管理接口 =============


@router.get("/{thread_id}/messages", response_model=BaseResponse[PageResponse[MessageResponse]])
async def get_messages(
    thread_id: str,
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话消息历史（从 LangGraph checkpoint 读取）

    Args:
        thread_id: 线程ID
        current_user: 当前用户
        page_query: 分页参数（page_num, page_size）
        db: 数据库会话

    Returns:
        PageResponse[MessageResponse]: 分页的消息列表
    """
    # 验证会话所有权
    conversation = await verify_conversation_ownership(thread_id, current_user.id, db)

    # 从 LangGraph checkpoint 获取消息
    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}
    try:
        compiled_graph = await get_cached_graph(user_id=current_user.id)
        state = await compiled_graph.aget_state(config)
        all_messages = state.values.get("messages", []) if state and state.values else []
    except Exception as e:
        logger.error(f"Failed to get messages from checkpoint: {e}")
        all_messages = []

    # 序列化所有消息
    serialized_messages = serialize_messages(all_messages)

    # 转换为 MessageResponse 格式（使用索引作为 id，使用会话创建时间作为基准时间）
    from datetime import timedelta

    base_time = conversation.create_time

    message_list = [
        MessageResponse(
            id=idx,
            role=msg["role"],
            content=msg["content"],
            metadata=msg.get("metadata", {}),  # 直接使用 metadata 字段
            created_at=base_time + timedelta(seconds=idx),  # 使用索引生成递增时间
        )
        for idx, msg in enumerate(serialized_messages)
    ]

    # 手动分页
    total = len(message_list)
    start_idx = page_query.offset
    end_idx = start_idx + page_query.limit
    paginated_messages = message_list[start_idx:end_idx]

    return BaseResponse(
        success=True,
        code=200,
        msg="获取消息列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=total,
            items=paginated_messages,
        ),
    )


@router.get("/{thread_id}/checkpoints", response_model=BaseResponse[CheckpointResponse])
async def get_checkpoints(
    thread_id: str,
    current_user: CurrentUser,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
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

        return BaseResponse(
            success=True,
            code=200,
            msg="获取检查点成功",
            data=CheckpointResponse(thread_id=thread_id, checkpoints=checkpoints),
        )
    except Exception as e:
        logger.error(f"Get checkpoints error: {e}")
        raise_internal_error(str(e))


# ============= 导出/导入接口 =============


@router.get("/{thread_id}/export", response_model=BaseResponse[ConversationExportResponse], include_in_schema=False)
async def export_conversation(
    thread_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    导出会话数据（从 LangGraph checkpoint 读取）

    Args:
        thread_id: 线程ID
        db: 数据库会话

    Returns:
        ConversationExportResponse: 导出数据
    """
    # 验证会话所有权
    conversation = await verify_conversation_ownership(thread_id, current_user.id, db)

    # 获取 LangGraph 状态和消息
    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}
    try:
        compiled_graph = await get_cached_graph(user_id=current_user.id)
        state = await compiled_graph.aget_state(config)
        state_values = state.values

        # 从 checkpoint 获取消息并序列化
        all_messages = state.values.get("messages", []) if state and state.values else []
        serialized_messages = serialize_messages(all_messages)
    except Exception as e:
        logger.warning(f"Failed to get state: {e}")
        state_values = None
        serialized_messages = []

    return BaseResponse(
        success=True,
        code=200,
        msg="导出会话成功",
        data=ConversationExportResponse(
            conversation={
                "thread_id": conversation.thread_id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "metadata": conversation.meta_data or {},
                "created_at": conversation.create_time.isoformat(),
                "updated_at": conversation.update_time.isoformat(),
            },
            messages=serialized_messages,
            state=state_values,
        ),
    )


@router.post("/import", include_in_schema=False)
async def import_conversation(
    request: ConversationImportRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(
        get_db,
    ),
):
    """
    导入会话数据（仅恢复到 LangGraph checkpoint）

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
    await db.commit()

    # 恢复 LangGraph 状态（消息会自动包含在状态中）
    if "state" in data and data["state"]:
        config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}
        try:
            compiled_graph = await get_cached_graph(user_id=current_user.id)
            await compiled_graph.aupdate_state(config, data["state"])
        except Exception as e:
            logger.warning(f"Could not restore state: {e}")
            raise_internal_error(f"导入会话失败: {str(e)}")

    return BaseResponse(
        success=True,
        code=200,
        msg="导入会话成功",
        data={"thread_id": thread_id, "status": "imported"},
    )


# ============= 搜索接口 =============


@router.post("/search", response_model=BaseResponse[SearchResponse])
async def search_conversations(
    request: SearchRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
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

    return BaseResponse(
        success=True,
        code=200,
        msg="搜索完成",
        data=SearchResponse(query=request.query, results=results),
    )


# ============= 统计接口 =============


@router.get("/users/stats", response_model=BaseResponse[UserStatsResponse])
async def get_user_stats(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
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

    return BaseResponse(
        success=True,
        code=200,
        msg="获取统计信息成功",
        data=UserStatsResponse(
            user_id=str(current_user.id),
            total_conversations=total_conversations,
            total_messages=total_messages,
            recent_conversations=[
                {"thread_id": conv.thread_id, "title": conv.title, "updated_at": conv.update_time.isoformat()}
                for conv in recent_conversations
            ],
        ),
    )

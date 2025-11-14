import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import aiosqlite
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, MessagesState, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# ============= 配置 =============
SQLITE_DB_PATH = "langgraph_app.db"
CHECKPOINT_DB_PATH = "checkpoints.db"

# ============= 数据库模型 =============
Base = declarative_base()


class Conversation(Base):
    """会话表"""

    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    thread_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Integer, default=1)


class Message(Base):
    """消息表"""

    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    thread_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutionLog(Base):
    """执行日志表"""

    __tablename__ = "execution_logs"

    id = Column(String, primary_key=True)
    thread_id = Column(String, index=True, nullable=False)
    node_name = Column(String)
    input_data = Column(JSON)
    output_data = Column(JSON)
    duration_ms = Column(Integer)
    status = Column(String)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============= 异步数据库初始化 =============
engine = create_async_engine(
    f"sqlite+aiosqlite:///{SQLITE_DB_PATH}", echo=False, json_serializer=json.dumps, json_deserializer=json.loads
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ============= LangGraph 初始化 =============
def create_graph():
    """创建 LangGraph"""
    workflow = StateGraph(MessagesState)

    async def chatbot(state: MessagesState):
        """异步聊天机器人节点"""
        # 这里替换为你的实际 LLM 调用
        user_message = state["messages"][-1].content

        # 模拟异步 LLM 调用
        import asyncio

        await asyncio.sleep(0.1)  # 模拟网络延迟

        response = f"Echo: {user_message}"
        return {"messages": [AIMessage(content=response)]}

    workflow.add_node("chatbot", chatbot)
    workflow.set_entry_point("chatbot")
    workflow.add_edge("chatbot", END)

    return workflow


# 全局变量用于存储 checkpointer 和 graph
checkpointer = None
compiled_graph = None


# ============= FastAPI 应用 =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global checkpointer, compiled_graph

    # 启动时初始化
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化 AsyncSqliteSaver
    checkpointer = AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)

    # 编译图
    compiled_graph = create_graph().compile(checkpointer=checkpointer)

    print(f"✅ Database initialized: {SQLITE_DB_PATH}")
    print(f"✅ Async Checkpointer initialized: {CHECKPOINT_DB_PATH}")

    yield

    # 关闭时清理
    await checkpointer.conn.close()
    await engine.dispose()
    print("👋 Application shutdown")


app = FastAPI(title="LangGraph Async SQLite API", version="1.0.0", lifespan=lifespan)


# ============= Pydantic 模型 =============
class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    user_id: str
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class ConversationCreate(BaseModel):
    user_id: str
    title: str | None = "New Conversation"
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    title: str | None = None
    metadata: dict[str, Any] | None = None


class ConversationResponse(BaseModel):
    id: str
    thread_id: str
    user_id: str
    title: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime


# ============= 依赖注入 =============
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ============= 辅助函数 =============
async def log_execution_async(
    thread_id: str,
    node_name: str,
    input_data: dict,
    output_data: Any,
    duration: float,
    status: str,
    error_message: str = None,
):
    """异步记录执行日志"""
    async with AsyncSessionLocal() as session:
        try:
            log = ExecutionLog(
                id=str(uuid.uuid4()),
                thread_id=thread_id,
                node_name=node_name,
                input_data=input_data,
                output_data=output_data if isinstance(output_data, dict) else {},
                duration_ms=int(duration),
                status=status,
                error_message=error_message,
            )
            session.add(log)
            await session.commit()
        except Exception as e:
            print(f"Error logging execution: {e}")


# ============= 核心对话接口 =============


@app.post("/api/v1/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """异步对话接口"""
    # 获取或创建会话
    thread_id = request.thread_id
    if not thread_id:
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            id=str(uuid.uuid4()),
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
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

    config = {"configurable": {"thread_id": thread_id}}

    try:
        # 保存用户消息
        user_message = Message(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            role="user",
            content=request.message,
            meta_data=request.metadata or {},
        )
        db.add(user_message)
        await db.commit()

        # 执行图（异步）
        start_time = datetime.utcnow()
        result = await compiled_graph.ainvoke({"messages": [HumanMessage(content=request.message)]}, config)
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        # 提取助手回复
        assistant_content = result["messages"][-1].content

        # 保存助手回复
        assistant_message = Message(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            role="assistant",
            content=assistant_content,
            metadata={"duration_ms": duration},
        )
        db.add(assistant_message)

        # 更新会话时间
        result_conv = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
        conversation = result_conv.scalar_one_or_none()
        if conversation:
            conversation.updated_at = datetime.utcnow()

        await db.commit()

        # 后台记录执行日志
        background_tasks.add_task(
            log_execution_async,
            thread_id,
            "chat",
            {"message": request.message},
            {"response": assistant_content},
            duration,
            "success",
        )

        return {"thread_id": thread_id, "response": assistant_content, "duration_ms": int(duration)}

    except Exception as e:
        background_tasks.add_task(
            log_execution_async, thread_id, "chat", {"message": request.message}, None, 0, "error", str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """异步流式对话接口"""
    thread_id = request.thread_id or str(uuid.uuid4())

    if not request.thread_id:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            user_id=request.user_id,
            title=request.message[:50] if len(request.message) > 50 else request.message,
            meta_data=request.metadata or {},
        )
        db.add(conversation)
        await db.commit()

    # 保存用户消息
    user_message = Message(
        id=str(uuid.uuid4()),
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
                        id=str(uuid.uuid4()), thread_id=thread_id, role="assistant", content=full_response, metadata={}
                    )
                    new_session.add(assistant_message)

                    # 更新会话时间
                    result = await new_session.execute(select(Conversation).where(Conversation.thread_id == thread_id))
                    conversation = result.scalar_one_or_none()
                    if conversation:
                        conversation.updated_at = datetime.utcnow()

                    await new_session.commit()

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============= 会话管理接口 =============


@app.post("/api/v1/conversations", response_model=ConversationResponse)
async def create_conversation(conv: ConversationCreate, db: AsyncSession = Depends(get_db)):
    """创建新会话"""
    conversation = Conversation(
        id=str(uuid.uuid4()),
        thread_id=str(uuid.uuid4()),
        user_id=conv.user_id,
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
        metadata=conversation.meta_data,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0,
    )


@app.get("/api/v1/conversations", response_model=list[ConversationResponse])
async def list_conversations(user_id: str, skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """获取用户的会话列表"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.is_active == 1)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()

    response_list = []
    for conv in conversations:
        # 获取消息数量
        count_result = await db.execute(select(Message).where(Message.thread_id == conv.thread_id))
        message_count = len(count_result.scalars().all())

        response_list.append(
            ConversationResponse(
                id=conv.id,
                thread_id=conv.thread_id,
                user_id=conv.user_id,
                title=conv.title,
                metadata=conv.meta_data or {},
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=message_count,
            )
        )

    return response_list


@app.get("/api/v1/conversations/{thread_id}")
async def get_conversation(thread_id: str, db: AsyncSession = Depends(get_db)):
    """获取单个会话详情"""
    result = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()

    return {
        "conversation": {
            "id": conversation.id,
            "thread_id": conversation.thread_id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "metadata": conversation.meta_data,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        },
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.meta_data,
                "created_at": msg.created_at,
            }
            for msg in messages
        ],
    }


@app.patch("/api/v1/conversations/{thread_id}")
async def update_conversation(thread_id: str, update: ConversationUpdate, db: AsyncSession = Depends(get_db)):
    """更新会话信息"""
    result = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if update.title is not None:
        conversation.title = update.title
    if update.metadata is not None:
        conversation.meta_data = update.metadata

    conversation.updated_at = datetime.utcnow()
    await db.commit()

    return {"status": "updated", "thread_id": thread_id}


@app.delete("/api/v1/conversations/{thread_id}")
async def delete_conversation(thread_id: str, hard_delete: bool = False, db: AsyncSession = Depends(get_db)):
    """删除会话（软删除或硬删除）"""
    result = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if hard_delete:
        # 硬删除：删除所有相关数据
        await db.execute(select(Message).where(Message.thread_id == thread_id))
        await db.execute(select(ExecutionLog).where(ExecutionLog.thread_id == thread_id))
        await db.delete(conversation)
    else:
        # 软删除
        conversation.is_active = 0

    await db.commit()
    return {"status": "deleted", "thread_id": thread_id}


# ============= 消息管理接口 =============


@app.get("/api/v1/conversations/{thread_id}/messages", response_model=list[MessageResponse])
async def get_messages(thread_id: str, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """获取会话消息历史"""
    result = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=msg.id, role=msg.role, content=msg.content, metadata=msg.meta_data or {}, created_at=msg.created_at
        )
        for msg in reversed(list(messages))
    ]


@app.delete("/api/v1/messages/{message_id}")
async def delete_message(message_id: str, db: AsyncSession = Depends(get_db)):
    """删除单条消息"""
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    await db.delete(message)
    await db.commit()
    return {"status": "deleted", "message_id": message_id}


# ============= 状态管理接口 =============


@app.get("/api/v1/conversations/{thread_id}/state")
async def get_state(thread_id: str):
    """获取会话的 LangGraph 状态"""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = await compiled_graph.aget_state(config)
        return {
            "thread_id": thread_id,
            "values": state.values,
            "next": state.next,
            "metadata": state.metadata,
            "created_at": state.created_at.isoformat() if state.created_at else None,
            "parent_config": state.parent_config,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"State not found: {str(e)}")


@app.get("/api/v1/conversations/{thread_id}/checkpoints")
async def get_checkpoints(thread_id: str, limit: int = 10):
    """获取会话的所有检查点"""
    config = {"configurable": {"thread_id": thread_id}}
    try:
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

        return {"thread_id": thread_id, "checkpoints": checkpoints}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/conversations/{thread_id}/update-state")
async def update_state(thread_id: str, state_update: dict[str, Any], as_node: str | None = None):
    """更新会话状态"""
    config = {"configurable": {"thread_id": thread_id}}

    try:
        await compiled_graph.aupdate_state(config, state_update, as_node=as_node)
        return {"status": "updated", "thread_id": thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 执行日志接口 =============


@app.get("/api/v1/conversations/{thread_id}/logs")
async def get_execution_logs(thread_id: str, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """获取执行日志"""
    result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.thread_id == thread_id)
        .order_by(ExecutionLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()

    return {
        "thread_id": thread_id,
        "logs": [
            {
                "id": log.id,
                "node_name": log.node_name,
                "duration_ms": log.duration_ms,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }


# ============= 搜索接口 =============


@app.get("/api/v1/search")
async def search_conversations(
    user_id: str, query: str, skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    """搜索会话和消息"""
    # 使用 SQLite LIKE 搜索
    result = await db.execute(
        select(Message)
        .join(Conversation, Message.thread_id == Conversation.thread_id)
        .where(Message.content.like(f"%{query}%"), Conversation.user_id == user_id)
        .order_by(Message.created_at.desc())
        .offset(skip)
        .limit(limit)
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
                "created_at": msg.created_at,
            }
        )

    return {"query": query, "results": results}


# ============= 导出/导入接口 =============


@app.get("/api/v1/conversations/{thread_id}/export")
async def export_conversation(thread_id: str, db: AsyncSession = Depends(get_db)):
    """导出会话数据"""
    result = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()

    # 获取 LangGraph 状态
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = await compiled_graph.aget_state(config)
        state_values = state.values
    except:
        state_values = {}

    return {
        "conversation": {
            "thread_id": conversation.thread_id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "metadata": conversation.meta_data,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        },
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.meta_data,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
        "state": state_values,
    }


@app.post("/api/v1/conversations/import")
async def import_conversation(data: dict[str, Any], user_id: str, db: AsyncSession = Depends(get_db)):
    """导入会话数据"""
    thread_id = str(uuid.uuid4())

    # 创建会话
    conversation = Conversation(
        id=str(uuid.uuid4()),
        thread_id=thread_id,
        user_id=user_id,
        title=data["conversation"]["title"],
        meta_data=data["conversation"].get("metadata", {}),
    )
    db.add(conversation)

    # 导入消息
    for msg_data in data["messages"]:
        message = Message(
            id=str(uuid.uuid4()),
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
            await compiled_graph.aupdate_state(config, data["state"])
        except Exception as e:
            print(f"Warning: Could not restore state: {e}")

    return {"thread_id": thread_id, "status": "imported"}


# ============= 统计接口 =============


@app.get("/api/v1/users/{user_id}/stats")
async def get_user_stats(user_id: str, db: AsyncSession = Depends(get_db)):
    """获取用户统计信息"""
    # 总会话数
    conv_result = await db.execute(
        select(Conversation).where(Conversation.user_id == user_id, Conversation.is_active == 1)
    )
    total_conversations = len(conv_result.scalars().all())

    # 总消息数
    msg_result = await db.execute(
        select(Message)
        .join(Conversation, Message.thread_id == Conversation.thread_id)
        .where(Conversation.user_id == user_id)
    )
    total_messages = len(msg_result.scalars().all())

    # 最近会话
    recent_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.is_active == 1)
        .order_by(Conversation.updated_at.desc())
        .limit(5)
    )
    recent_conversations = recent_result.scalars().all()

    return {
        "user_id": user_id,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "recent_conversations": [
            {"thread_id": conv.thread_id, "title": conv.title, "updated_at": conv.updated_at}
            for conv in recent_conversations
        ],
    }


# ============= 数据库维护接口 =============


@app.post("/api/v1/admin/vacuum")
async def vacuum_database():
    """优化 SQLite 数据库"""
    try:
        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            await db.execute("VACUUM")
            await db.commit()
        return {"status": "success", "message": "Database vacuumed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/admin/db-size")
async def get_database_size():
    """获取数据库大小"""
    import os

    try:
        main_db_size = os.path.getsize(SQLITE_DB_PATH) / (1024 * 1024)
        checkpoint_db_size = os.path.getsize(CHECKPOINT_DB_PATH) / (1024 * 1024)

        return {
            "main_database": {"path": SQLITE_DB_PATH, "size_mb": round(main_db_size, 2)},
            "checkpoint_database": {"path": CHECKPOINT_DB_PATH, "size_mb": round(checkpoint_db_size, 2)},
            "total_size_mb": round(main_db_size + checkpoint_db_size, 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 健康检查 =============


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """健康检查"""
    try:
        # 检查数据库连接
        await db.execute(select(1))

        # 检查 checkpointer
        async with aiosqlite.connect(CHECKPOINT_DB_PATH) as conn:
            await conn.execute("SELECT 1")

        return {"status": "healthy", "database": "connected", "checkpointer": "connected", "langgraph": "ready"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/")
async def root():
    """根路径"""
    return {"message": "LangGraph Async SQLite API", "version": "1.0.0", "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

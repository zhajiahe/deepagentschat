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

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import CurrentUser
from app.core.exceptions import (
    raise_client_closed_error,
    raise_internal_error,
    raise_not_found_error,
)
from app.core.lifespan import get_cached_graph
from app.models import Conversation, UserSettings
from app.models.base import BaseResponse
from app.schemas import ChatRequest, ChatResponse
from app.tools import UserContext
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


def serialize_messages(messages: list[BaseMessage]) -> list[dict]:
    """将 LangChain 消息列表序列化为字典格式，自动关联工具调用和输出

    Args:
        messages: LangChain 消息对象列表

    Returns:
        list[dict]: 序列化后的消息字典列表
    """
    # 第一步：收集所有工具调用的输出
    tool_outputs: dict[str, str] = {}
    for msg in messages:
        # ToolMessage 包含工具调用的输出
        if type(msg).__name__ == "ToolMessage" and hasattr(msg, "tool_call_id") and msg.tool_call_id:
            tool_outputs[msg.tool_call_id] = str(msg.content) if msg.content else ""

    # 第二步：序列化所有消息
    serialized: list[dict] = []
    for index, msg in enumerate(messages):
        metadata: dict = {
            "_order_index": index,  # 添加顺序索引，确保前端能正确排序
        }

        # 处理 AIMessage 的 tool_calls
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_calls_list = []
            for tool_call in msg.tool_calls:
                tool_call_dict = {
                    "id": tool_call.get("id", ""),
                    "name": tool_call.get("name", ""),
                    "input": tool_call.get("args", {}),  # 前端期望 input 字段
                    "arguments": tool_call.get("args", {}),  # 同时保留 arguments 以兼容
                }
                # 如果有工具输出，添加到 tool_call 中
                tool_call_id = tool_call.get("id")
                if tool_call_id and tool_call_id in tool_outputs:
                    tool_call_dict["output"] = tool_outputs[tool_call_id]
                tool_calls_list.append(tool_call_dict)

            metadata["tool_calls"] = tool_calls_list

        # 处理 ToolMessage 的 name 和 tool_call_id
        if hasattr(msg, "name") and msg.name:
            metadata["tool_name"] = msg.name
        if hasattr(msg, "tool_call_id") and msg.tool_call_id:
            metadata["tool_call_id"] = msg.tool_call_id

        # 添加额外的 kwargs（如果有）
        if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
            metadata.update(msg.additional_kwargs)

        msg_dict = {
            "role": get_role(msg),
            "content": str(msg.content) if msg.content else "",
            "type": type(msg).__name__,
            "metadata": metadata,
        }

        serialized.append(msg_dict)

    return serialized


def serialize_message(msg: BaseMessage) -> dict:
    """将单个 LangChain BaseMessage 序列化为字典格式（向后兼容）

    Args:
        msg: LangChain 消息对象

    Returns:
        dict: 序列化后的消息字典
    """
    return serialize_messages([msg])[0]


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


async def get_user_config(
    user_id: uuid.UUID, thread_id: str, db: AsyncSession
) -> tuple[dict, dict, dict[str, str | int | None]]:
    """获取用户配置

    Args:
        user_id: 用户ID
        thread_id: 会话线程ID
        db: 数据库会话

    Returns:
        tuple[dict, dict, dict]: (config, context, llm_params)
            - config: LangGraph 配置（包含 thread_id、user_id、recursion_limit 等）
            - context: LangGraph 上下文
            - llm_params: LLM 模型参数（llm_model, api_key, base_url, max_tokens）
    """
    # 使用全局配置作为默认值
    config: dict = {
        "configurable": {"thread_id": thread_id, "user_id": str(user_id)},
        "recursion_limit": settings.LANGGRAPH_RECURSION_LIMIT,  # 添加递归限制
    }
    context: dict = {}
    llm_params: dict[str, str | int | None] = {
        "llm_model": None,
        "api_key": None,
        "base_url": None,
        "max_tokens": 4096,
    }

    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = result.scalar_one_or_none()

    if user_settings:
        # LangGraph 配置和上下文
        config["configurable"].update(user_settings.config or {})
        context = user_settings.context or {}

        # 允许用户自定义递归限制（如果在 config 中设置）
        if user_settings.config and "recursion_limit" in user_settings.config:
            config["recursion_limit"] = user_settings.config["recursion_limit"]

        # LLM 模型参数（用于动态创建图）
        if user_settings.llm_model:
            llm_params["llm_model"] = user_settings.llm_model
        if user_settings.max_tokens:
            llm_params["max_tokens"] = user_settings.max_tokens

        # 从用户设置中读取 API 密钥和基础 URL（如果有）
        user_api_key = user_settings.settings.get("api_key") if user_settings.settings else None
        user_base_url = user_settings.settings.get("base_url") if user_settings.settings else None

        if user_api_key:
            llm_params["api_key"] = user_api_key
        if user_base_url:
            llm_params["base_url"] = user_base_url

    # 使用全局配置作为默认值
    if not llm_params["llm_model"]:
        llm_params["llm_model"] = settings.DEFAULT_LLM_MODEL
    if not llm_params["api_key"]:
        llm_params["api_key"] = settings.OPENAI_API_KEY
    if not llm_params["base_url"]:
        llm_params["base_url"] = settings.OPENAI_API_BASE

    return config, context, llm_params


async def update_conversation_time(thread_id: str, db: AsyncSession) -> None:
    """更新会话时间

    Args:
        thread_id: 会话线程ID
        db: 数据库会话
    """
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

    # 获取用户配置（包括 LLM 参数）
    config, context, llm_params = await get_user_config(current_user.id, thread_id, db)

    try:
        # 执行图（异步）- 使用任务包装以便支持取消
        start_time = utc_now()

        # 根据用户配置获取对应的图实例（带缓存）
        llm_model = llm_params["llm_model"]
        api_key = llm_params["api_key"]
        base_url = llm_params["base_url"]
        max_tokens = llm_params["max_tokens"]

        compiled_graph = await get_cached_graph(
            llm_model=llm_model if isinstance(llm_model, str) else None,
            api_key=api_key if isinstance(api_key, str) else None,
            base_url=base_url if isinstance(base_url, str) else None,
            max_tokens=max_tokens if isinstance(max_tokens, int) else 4096,
            user_id=current_user.id,  # 使用 UUID，不转换为 int
        )

        # 创建任务并注册
        invoke_task = asyncio.create_task(
            compiled_graph.ainvoke(
                {"messages": [HumanMessage(content=request.message)]},
                config=config,
                context=UserContext(user_id=str(current_user.id)),  # 传递用户上下文
            )
        )
        await task_manager.register_task(thread_id, invoke_task)

        try:
            await invoke_task
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

        # 更新会话时间
        await update_conversation_time(thread_id, db)

        # 从 checkpoint 获取完整的消息历史
        state = await compiled_graph.aget_state(config)
        all_messages = state.values.get("messages", []) if state and state.values else []

        # 找到最后一个用户消息的索引，提取本轮对话的所有消息
        last_human_index = -1
        for i in range(len(all_messages) - 1, -1, -1):
            if get_role(all_messages[i]) == "user":
                last_human_index = i
                break

        # 序列化本轮对话的消息（从最后一个用户消息开始）
        current_turn_messages = all_messages[last_human_index:] if last_human_index >= 0 else all_messages
        serialized_messages = serialize_messages(current_turn_messages)

        # 提取最后一条助手回复用于响应
        assistant_content = (
            all_messages[-1].content if all_messages and get_role(all_messages[-1]) == "assistant" else ""
        )

        return BaseResponse(
            success=True,
            code=200,
            msg="对话成功",
            data=ChatResponse(
                thread_id=thread_id,
                response=str(assistant_content) if assistant_content else "",
                duration_ms=int(duration),
                messages=serialized_messages,
            ),
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

    # 获取用户配置（包括 LLM 参数）
    config, context, llm_params = await get_user_config(current_user.id, thread_id, db)

    async def event_generator():
        stopped = False
        # 注册任务（使用当前协程作为任务标识）
        current_task = asyncio.current_task()
        if current_task:
            await task_manager.register_task(thread_id, current_task)

        try:
            # 根据用户配置获取对应的图实例（带缓存）
            llm_model = llm_params["llm_model"]
            api_key = llm_params["api_key"]
            base_url = llm_params["base_url"]
            max_tokens = llm_params["max_tokens"]

            compiled_graph = await get_cached_graph(
                llm_model=llm_model if isinstance(llm_model, str) else None,
                api_key=api_key if isinstance(api_key, str) else None,
                base_url=base_url if isinstance(base_url, str) else None,
                max_tokens=max_tokens if isinstance(max_tokens, int) else 4096,
                user_id=current_user.id,  # 使用 UUID，不转换为 int
            )

            # 使用 astream 获取逐 token 流式输出 (同时监听 messages 和 updates 以优化延迟)
            # 用于累积工具调用的参数和消息内容
            tool_call_chunks: dict[str, dict] = {}  # {tool_call_id: {name, args_accumulated}}
            current_checkpoint_ns: str | None = None  # 当前消息的 checkpoint namespace

            async for mode, payload in compiled_graph.astream(
                {"messages": [HumanMessage(content=request.message)]},
                config=config,
                context=UserContext(user_id=str(current_user.id)),  # 传递用户上下文
                stream_mode=["messages", "updates"],
            ):
                # 检查是否被停止
                if await task_manager.is_stopped(thread_id):
                    stopped = True
                    logger.info(f"Stream stopped by user for thread_id: {thread_id}")
                    yield f"data: {json.dumps({'stopped': True, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"
                    break

                if mode == "updates":
                    # 监听 updates 事件，当 model 节点完成时立即发送 tool_input
                    # payload 是一个字典 {node_name: values}
                    if isinstance(payload, dict):
                        # 检查是否有 model 节点的更新
                        # 注意：根据 LangGraph 版本，key 可能是 "model" 或其他配置的节点名
                        # 这里假设 LLM 节点名为 "model" (agent pattern 常用名)
                        is_model_update = "model" in payload or any(k.endswith(":model") for k in payload.keys())

                        if is_model_update and current_checkpoint_ns is not None:
                            # Model 节点执行完成，立即发送累积的工具调用参数
                            for tool_call_id, tool_data in tool_call_chunks.items():
                                try:
                                    tool_input = json.loads(tool_data["args"]) if tool_data["args"] else {}
                                except json.JSONDecodeError:
                                    tool_input = {"raw": tool_data["args"]}

                                # 只有当还未发送过（或者为了保险起见重复发送，前端应去重）时才发送
                                # 这里我们清空 accumulated args 或者标记已发送
                                # 简单起见，我们发送并清空 list (但 message_end 还需要吗？)
                                yield f"data: {json.dumps({'type': 'tool_input', 'tool_name': tool_data['name'], 'tool_call_id': tool_call_id, 'tool_input': tool_input, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                            # 清空 accumulators 以免重复发送
                            tool_call_chunks.clear()
                    continue

                if mode == "messages":
                    token, metadata = payload

                    # token 是一个对象，包含 content_blocks 属性
                    # content_blocks 格式: [{'type': 'text', 'text': '...'}, {'type': 'tool_call_chunk', ...}, ...]
                    if hasattr(token, "content_blocks"):
                        node_name = metadata.get("langgraph_node", "")
                        checkpoint_ns = metadata.get("langgraph_checkpoint_ns", "")

                        # 检测新消息：checkpoint_ns 改变且是 model 节点且有内容
                        if (
                            checkpoint_ns
                            and checkpoint_ns != current_checkpoint_ns
                            and node_name == "model"
                            and token.content_blocks
                        ):
                            # 新消息开始
                            if current_checkpoint_ns is not None:
                                # 在发送 message_end 之前，发送工具调用的完整参数 (如果 updates 没触发)
                                for tool_call_id, tool_data in tool_call_chunks.items():
                                    try:
                                        # 尝试解析 JSON 参数
                                        tool_input = json.loads(tool_data["args"]) if tool_data["args"] else {}
                                    except json.JSONDecodeError:
                                        tool_input = {"raw": tool_data["args"]}

                                    yield f"data: {json.dumps({'type': 'tool_input', 'tool_name': tool_data['name'], 'tool_call_id': tool_call_id, 'tool_input': tool_input, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"
                                # 发送消息结束事件
                                yield f"data: {json.dumps({'type': 'message_end', 'message_id': current_checkpoint_ns, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                                # 清空 chunks
                                tool_call_chunks.clear()

                            # 发送消息开始事件
                            current_checkpoint_ns = checkpoint_ns
                            yield f"data: {json.dumps({'type': 'message_start', 'message_id': checkpoint_ns, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                        for block in token.content_blocks:
                            if not isinstance(block, dict):
                                continue

                            block_type = block.get("type")

                            # 处理文本块
                            if block_type == "text" and block.get("text"):
                                # 添加 node_name 以便前端区分是 model 节点还是 tools 节点的内容
                                yield f"data: {json.dumps({'type': 'content', 'content': block['text'], 'node': node_name, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                            # 处理工具调用块
                            elif block_type == "tool_call_chunk":
                                tool_call_id = block.get("id", "")
                                tool_name = block.get("name")
                                tool_args = block.get("args") or ""  # 确保不是 None

                                # 如果是新的工具调用（有 id 和 name）
                                if tool_call_id and tool_name:
                                    if tool_call_id not in tool_call_chunks:
                                        # 发送工具调用开始事件
                                        tool_call_chunks[tool_call_id] = {
                                            "name": tool_name,
                                            "args": tool_args,
                                        }
                                        yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': tool_name, 'tool_call_id': tool_call_id, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"
                                    else:
                                        # 累积参数
                                        tool_call_chunks[tool_call_id]["args"] += tool_args
                                # 如果只有参数（继续累积）
                                elif tool_args and tool_call_chunks:
                                    # 找到最后一个工具调用并累积参数
                                    last_tool_id = list(tool_call_chunks.keys())[-1]
                                    tool_call_chunks[last_tool_id]["args"] += tool_args

                        # 注意：tool_input 事件已经在检测到新消息或 updates 时发送

            # 如果被停止，不更新会话时间
            if stopped:
                await task_manager.unregister_task(thread_id)
                return

            # 更新会话时间
            try:
                async with AsyncSessionLocal() as new_session:
                    await update_conversation_time(thread_id, new_session)
            except Exception as e:
                logger.error(f"Failed to update conversation time: {e}")

            # 获取完整的消息历史（包括工具调用和输出）
            try:
                state = await compiled_graph.aget_state(config)
                all_messages = state.values.get("messages", []) if state and state.values else []

                # 找到最后一个用户消息的索引，提取本轮对话的所有消息
                last_human_index = -1
                for i in range(len(all_messages) - 1, -1, -1):
                    if get_role(all_messages[i]) == "user":
                        last_human_index = i
                        break

                # 提取本轮对话的消息
                current_turn_messages = all_messages[last_human_index:] if last_human_index >= 0 else all_messages

                # 发送工具输出事件（如果有工具调用）
                for msg in current_turn_messages:
                    if get_role(msg) == "tool" and hasattr(msg, "tool_call_id"):
                        tool_call_id = msg.tool_call_id
                        tool_name = msg.name if hasattr(msg, "name") else ""
                        tool_output = str(msg.content) if msg.content else ""
                        yield f"data: {json.dumps({'type': 'tool_end', 'tool_name': tool_name, 'tool_call_id': tool_call_id, 'tool_output': tool_output, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                # 序列化本轮对话的消息
                serialized_messages = serialize_messages(current_turn_messages)

                # 在 done 事件中包含完整的消息列表
                yield f"data: {json.dumps({'done': True, 'messages': serialized_messages}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"Failed to get messages: {e}")
                yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for thread_id: {thread_id}")
            yield f"data: {json.dumps({'stopped': True, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            # 区分错误类型
            error_msg = str(e)
            error_code = "internal_error"

            if "401" in error_msg or "Unauthorized" in error_msg:
                error_code = "auth_error"
            elif "429" in error_msg or "Rate limit" in error_msg:
                error_code = "rate_limit_error"
            elif "400" in error_msg:
                error_code = "invalid_request"

            yield f"data: {json.dumps({'error': error_msg, 'code': error_code}, ensure_ascii=False)}\n\n"
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

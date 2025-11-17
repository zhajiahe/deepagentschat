"""
应用生命周期管理

管理应用启动和关闭时的资源初始化和清理
"""

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from fastapi import FastAPI
from loguru import logger

from app.core.checkpointer import close_checkpointer, get_checkpointer, init_checkpointer
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.graph import create_graph

# 全局变量用于存储默认编译后的图
compiled_graph: Any | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器

    启动时:
    - 初始化数据库连接
    - 创建数据库表（开发环境）
    - 初始化 LangGraph checkpointer
    - 编译 LangGraph 图

    关闭时:
    - 关闭数据库连接
    - 关闭 checkpointer 连接
    - 清理资源
    """
    global compiled_graph

    # 启动时
    logger.info("🚀 应用启动中...")

    try:
        # 初始化数据库
        await init_db()
        logger.info("✅ 数据库初始化成功")

        # 初始化 LangGraph checkpointer（使用配置中的路径）
        checkpointer = await init_checkpointer(settings.CHECKPOINT_DB_PATH)

        # 创建 Agent 图（传入 checkpointer 以支持状态持久化）
        compiled_graph = create_graph(checkpointer=checkpointer)
        logger.info("✅ LangGraph 图编译成功")

    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        raise

    logger.info("✅ 应用启动完成")

    yield

    # 关闭时
    logger.info("🛑 应用关闭中...")

    try:
        await close_db()
        logger.info("✅ 数据库连接已关闭")

        await close_checkpointer()
        logger.info("✅ Checkpointer 连接已关闭")

    except Exception as e:
        logger.error(f"❌ 关闭失败: {e}")

    logger.info("✅ 应用已关闭")


def get_compiled_graph() -> Any:
    """
    获取默认编译后的 LangGraph 图（使用默认配置）

    Returns:
        CompiledGraph: 编译后的图对象

    Raises:
        RuntimeError: 如果图未初始化
    """
    if compiled_graph is None:
        raise RuntimeError("Graph not initialized. Application may not have started properly.")
    return compiled_graph


@lru_cache(maxsize=32)
def get_cached_graph(
    llm_model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    max_tokens: int = 4096,
) -> Any:
    """
    获取缓存的 LangGraph 图（根据用户配置）

    使用 LRU 缓存策略，最多缓存 32 个不同配置的图实例。
    这样可以为不同用户的不同配置提供高效的图实例复用。

    Args:
        llm_model: LLM 模型名称
        api_key: API 密钥
        base_url: API 基础 URL
        max_tokens: 最大 token 数

    Returns:
        CompiledGraph: 编译后的图对象

    Note:
        - 相同配置的请求会复用同一个图实例
        - 超过缓存大小时，最少使用的图实例会被清除
        - 所有图实例共享同一个 checkpointer（状态持久化）
    """
    checkpointer = get_checkpointer()
    graph = create_graph(
        checkpointer=checkpointer,
        llm_model=llm_model,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
    )
    logger.debug(
        f"Created new graph instance with config: model={llm_model}, max_tokens={max_tokens}, cache_info={get_cached_graph.cache_info()}"
    )
    return graph


def clear_graph_cache():
    """
    清除图缓存

    在需要强制重新创建所有图实例时调用（例如配置热重载）
    """
    get_cached_graph.cache_clear()
    logger.info("Graph cache cleared")

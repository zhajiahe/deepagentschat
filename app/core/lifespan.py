"""
应用生命周期管理

管理应用启动和关闭时的资源初始化和清理
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from loguru import logger

from app.core.checkpointer import close_checkpointer, init_checkpointer
from app.core.database import close_db, init_db
from app.core.graph import create_graph

# 全局变量用于存储编译后的图
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

        # 初始化 LangGraph checkpointer
        checkpointer = await init_checkpointer()

        # 编译 LangGraph 图
        compiled_graph = create_graph().compile(checkpointer=checkpointer)
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
    获取编译后的 LangGraph 图

    Returns:
        CompiledGraph: 编译后的图对象

    Raises:
        RuntimeError: 如果图未初始化
    """
    if compiled_graph is None:
        raise RuntimeError("Graph not initialized. Application may not have started properly.")
    return compiled_graph

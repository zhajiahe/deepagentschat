"""
LangGraph 检查点管理

管理对话状态的持久化
"""

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from loguru import logger

# 全局 checkpointer 实例
checkpointer: AsyncSqliteSaver | None = None


async def init_checkpointer(db_path: str = "checkpoints.db") -> AsyncSqliteSaver:
    """
    初始化异步 SQLite 检查点保存器

    Args:
        db_path: SQLite 数据库路径

    Returns:
        AsyncSqliteSaver: 检查点保存器实例
    """
    global checkpointer

    try:
        # AsyncSqliteSaver.from_conn_string returns a context manager
        # We need to enter it to get the actual saver
        checkpointer = await AsyncSqliteSaver.from_conn_string(db_path).__aenter__()
        logger.info(f"✅ Checkpointer initialized: {db_path}")
        return checkpointer
    except Exception as e:
        logger.error(f"❌ Failed to initialize checkpointer: {e}")
        raise


async def close_checkpointer():
    """关闭检查点保存器连接"""
    global checkpointer

    if checkpointer:
        try:
            # Call __aexit__ to properly close the context manager
            await checkpointer.__aexit__(None, None, None)
            logger.info("✅ Checkpointer connection closed")
        except Exception as e:
            logger.error(f"❌ Failed to close checkpointer: {e}")


def get_checkpointer() -> AsyncSqliteSaver:
    """
    获取全局检查点保存器实例

    Returns:
        AsyncSqliteSaver: 检查点保存器实例

    Raises:
        RuntimeError: 如果检查点保存器未初始化
    """
    if checkpointer is None:
        raise RuntimeError("Checkpointer not initialized. Call init_checkpointer() first.")
    return checkpointer

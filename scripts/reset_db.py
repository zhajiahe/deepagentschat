"""
重置数据库脚本

删除所有表并重新创建
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.core.database import engine
from app.models.base import Base


async def reset_database():
    """重置数据库"""
    logger.warning("⚠️  警告：此操作将删除所有数据库表和数据！")
    confirm = input("确认要继续吗？(yes/no): ").strip().lower()

    if confirm != "yes":
        logger.info("❌ 操作已取消")
        return

    try:
        logger.info("🗑️  正在删除所有表...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("✅ 所有表已删除")

        logger.info("🔨 正在重新创建表...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ 所有表已重新创建")

        logger.info("✅ 数据库重置成功！")

    except Exception as e:
        logger.error(f"❌ 数据库重置失败: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """主函数"""
    try:
        await reset_database()
    except KeyboardInterrupt:
        logger.info("\n⚠️  操作已取消")
    except Exception as e:
        logger.error(f"❌ 发生错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

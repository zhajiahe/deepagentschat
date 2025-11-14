"""
初始化数据库脚本

创建所有数据库表
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.core.database import init_db


async def main():
    """主函数"""
    logger.info("🗄️  开始初始化数据库...")

    try:
        await init_db()
        logger.info("✅ 数据库初始化成功！")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

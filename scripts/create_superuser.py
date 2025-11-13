"""
创建超级管理员脚本

交互式创建超级管理员用户
"""

import asyncio

from loguru import logger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User


async def create_superuser():
    """创建超级管理员"""
    logger.info("👤 创建超级管理员")

    # 获取用户输入
    username = input("请输入用户名: ").strip()
    if not username:
        logger.error("❌ 用户名不能为空")
        return

    email = input("请输入邮箱: ").strip()
    if not email:
        logger.error("❌ 邮箱不能为空")
        return

    nickname = input("请输入昵称: ").strip()
    if not nickname:
        nickname = username

    password = input("请输入密码: ").strip()
    if not password:
        logger.error("❌ 密码不能为空")
        return

    # 确认密码
    password_confirm = input("请再次输入密码: ").strip()
    if password != password_confirm:
        logger.error("❌ 两次密码不一致")
        return

    # 创建用户
    async with AsyncSessionLocal() as db:
        try:
            # 检查用户名是否已存在
            result = await db.execute(select(User).where(User.username == username, User.deleted == 0))
            if result.scalar_one_or_none():
                logger.error(f"❌ 用户名 '{username}' 已存在")
                return

            # 检查邮箱是否已存在
            result = await db.execute(select(User).where(User.email == email, User.deleted == 0))
            if result.scalar_one_or_none():
                logger.error(f"❌ 邮箱 '{email}' 已存在")
                return

            # 创建超级管理员
            superuser = User(
                username=username,
                email=email,
                nickname=nickname,
                hashed_password=get_password_hash(password),
                is_active=True,
                is_superuser=True,
            )

            db.add(superuser)
            await db.commit()
            await db.refresh(superuser)

            logger.info("✅ 超级管理员创建成功！")
            logger.info(f"   用户名: {superuser.username}")
            logger.info(f"   邮箱: {superuser.email}")
            logger.info(f"   昵称: {superuser.nickname}")
            logger.info(f"   ID: {superuser.id}")

        except Exception as e:
            logger.error(f"❌ 创建超级管理员失败: {e}")
            await db.rollback()
            raise


async def main():
    """主函数"""
    try:
        await create_superuser()
    except KeyboardInterrupt:
        logger.info("\n⚠️  操作已取消")
    except Exception as e:
        logger.error(f"❌ 发生错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

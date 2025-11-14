"""
pytest 全局配置文件
定义全局 fixtures 和配置
"""

import os
import uuid
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.base import Base

try:
    from app.main import app
except (ImportError, AttributeError):
    from fastapi import FastAPI

    app = FastAPI()

# ============ 数据库配置 ============

# 使用内存数据库进行测试 (使用 aiosqlite 支持异步)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # 使用静态连接池，确保所有测试使用同一个内存数据库
    echo=False,  # 关闭SQL日志以提高测试速度
)

# ============ Pytest 配置 ============

# 配置 pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """pytest 启动时的配置"""
    # 设置测试环境变量
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL

    # 禁用loguru日志以提高测试速度
    from loguru import logger

    logger.disable("")


# ============ 数据库 Fixtures ============


@pytest.fixture(scope="session")
def event_loop():
    """创建一个事件循环用于整个测试会话"""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def db_engine():
    """
    创建测试数据库引擎（整个测试会话共享）
    """
    return engine


@pytest.fixture(scope="session", autouse=True)
async def setup_db(db_engine):
    """
    在测试会话开始时创建数据库表，结束时清理
    """
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_engine.dispose()


@pytest.fixture(scope="class")
async def db(db_engine):
    """
    创建数据库会话（类级别共享，每个测试后清理数据）
    性能优化：使用TRUNCATE代替重建表
    """
    AsyncSessionLocal = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionLocal() as session:
        yield session

        # 测试后清理数据（保留表结构）
        try:
            from sqlalchemy import text

            await session.execute(text("DELETE FROM users"))
            await session.commit()
        except Exception:
            await session.rollback()


@pytest.fixture(scope="class", autouse=True)
async def override_get_db(db: AsyncSession):
    """
    覆盖应用的数据库依赖（类级别自动应用）
    """

    async def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


# ============ 客户端 Fixtures ============


@pytest.fixture(scope="class")
def client(override_get_db) -> Generator[TestClient, None, None]:
    """
    同步测试客户端（类级别共享）
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="class")
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """
    异步测试客户端（类级别共享）
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============ 认证 Fixtures ============

# 缓存superuser token以加速测试
# 注意：由于 user_id 改为 UUID，需要清除旧 token 缓存
_cached_superuser_token: str | None = None
_cached_hashed_password: str | None = None
_cached_user_id: uuid.UUID | None = None


@pytest.fixture(scope="session")
def cached_admin_password_hash():
    """缓存管理员密码哈希以加速测试"""
    from app.core.security import get_password_hash

    global _cached_hashed_password
    if _cached_hashed_password is None:
        _cached_hashed_password = get_password_hash("admin123")
    return _cached_hashed_password


@pytest.fixture(scope="class")
async def superuser_token(client: TestClient, db: AsyncSession, cached_admin_password_hash: str) -> str:
    """
    创建超级管理员并返回其访问令牌（类级别共享，使用缓存的密码哈希）
    """
    from sqlalchemy import select

    from app.models.user import User

    global _cached_user_id

    # 检查是否已存在admin用户
    result = await db.execute(select(User).where(User.username == "admin", User.deleted == 0))
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        # 创建超级管理员用户（使用缓存的密码哈希）
        superuser = User(
            username="admin",
            email="admin@example.com",
            nickname="Admin",
            hashed_password=cached_admin_password_hash,
            is_active=True,
            is_superuser=True,
        )
        db.add(superuser)
        await db.commit()
        await db.refresh(superuser)
        _cached_user_id = superuser.id
    else:
        _cached_user_id = existing_user.id

    # 登录获取token（每次重新生成，因为 user_id 是 UUID）
    response = client.post("/api/v1/auth/login?username=admin&password=admin123")
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.text}")
    token: str = response.json()["data"]["access_token"]
    return token


@pytest.fixture(scope="class")
def auth_headers(superuser_token: str) -> dict[str, str]:
    """
    返回包含认证token的headers（类级别共享）
    """
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest.fixture(scope="class")
async def current_user_id(superuser_token: str, db: AsyncSession):
    """
    获取当前用户的 UUID（类级别共享）
    """
    from fastapi import HTTPException, status

    from app.core.security import verify_access_token

    try:
        user_id = verify_access_token(
            superuser_token, HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        )
        return user_id
    except Exception:
        # 如果无法解析token，从数据库获取
        from sqlalchemy import select

        from app.models.user import User

        result = await db.execute(select(User).where(User.username == "admin", User.deleted == 0))
        user = result.scalar_one_or_none()
        if user:
            return user.id
        raise

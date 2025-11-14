"""
配置管理模块

使用 Pydantic Settings 管理应用配置
"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # JWT 配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"  # 生产环境必须更改
    REFRESH_SECRET_KEY: str = "your-refresh-secret-key-here-change-in-production"  # 生产环境必须更改
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 访问令牌过期时间（分钟）
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 刷新令牌过期时间（天）

    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./langgraph_app.db"

    # LangGraph Checkpointer 配置
    # 使用与主数据库相同的文件
    CHECKPOINT_DB_PATH: str = "./langgraph_app.db"

    # 应用配置
    APP_NAME: str = "FastAPI Template"
    DEBUG: bool = True

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # 忽略未定义的额外环境变量
    )  # type: ignore[typeddict-unknown-key]


# 创建全局配置实例
settings = Settings()

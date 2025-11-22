"""
配置管理模块

使用 Pydantic Settings 管理应用配置
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # LLM 配置
    OPENAI_API_KEY: str | None = None  # OpenAI API 密钥
    OPENAI_API_BASE: str | None = None  # OpenAI API 基础 URL
    DEFAULT_LLM_MODEL: str = "qwen-plus"  # 默认 LLM 模型

    # LangGraph 配置
    LANGGRAPH_RECURSION_LIMIT: int = 1000  # 递归限制
    LANGGRAPH_MAX_ITERATIONS: int = 100  # 最大迭代次数

    # 应用配置
    APP_NAME: str = "FastAPI Template"
    DEBUG: bool = True

    # Docker 工具配置
    USE_DOCKER_TOOLS: bool = True
    DOCKER_IMAGE: str = "deepagentschat-tools:latest"
    DOCKER_CPU_LIMIT: float = 1.0
    DOCKER_MEMORY_LIMIT: str = "512m"
    DOCKER_NETWORK_MODE: str = "none"
    DOCKER_TIMEOUT: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # 忽略未定义的额外环境变量
    )


# 创建全局配置实例
settings = Settings()

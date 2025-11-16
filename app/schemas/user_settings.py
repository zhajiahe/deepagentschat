"""
用户设置 Schema

用于用户设置相关的数据验证和序列化
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import EnhancedBaseModel, validate_max_tokens


class UserSettingsResponse(BaseModel):
    """用户设置响应"""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID = Field(..., description="用户ID(UUID)")
    llm_model: str | None = Field(None, description="默认模型")
    max_tokens: int | None = Field(None, description="默认最大token数", ge=1)
    settings: dict = Field(default_factory=dict, description="其他设置(JSON格式)")
    config: dict = Field(default_factory=dict, description="langgraph 配置(JSON格式)")
    context: dict = Field(default_factory=dict, description="langgraph context(JSON格式)")


class UserSettingsUpdate(EnhancedBaseModel):
    """用户设置更新请求"""

    llm_model: str | None = Field(None, min_length=1, max_length=100, description="默认模型")
    max_tokens: int | None = Field(None, ge=1, le=32768, description="默认最大token数")
    settings: dict | None = Field(None, description="其他设置(JSON格式)")
    config: dict | None = Field(None, description="langgraph 配置(JSON格式)")
    context: dict | None = Field(None, description="langgraph context(JSON格式)")

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens_field(cls, v: int) -> int:
        return validate_max_tokens(v)

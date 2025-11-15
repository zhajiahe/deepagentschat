"""
用户设置 Schema

用于用户设置相关的数据验证和序列化
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import EnhancedBaseModel, validate_max_tokens, validate_temperature


class UserSettingsResponse(BaseModel):
    """用户设置响应"""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID = Field(..., description="用户ID(UUID)")
    default_model: str | None = Field(None, description="默认模型")
    default_temperature: float | None = Field(None, description="默认温度", ge=0.0, le=2.0)
    default_max_tokens: int | None = Field(None, description="默认最大token数", ge=1)
    theme: str = Field(default="light", description="主题(light/dark)")
    language: str = Field(default="zh-CN", description="语言")
    settings: dict = Field(default_factory=dict, description="其他设置")


class UserSettingsUpdate(EnhancedBaseModel):
    """用户设置更新请求"""

    default_model: str | None = Field(None, min_length=1, max_length=100, description="默认模型")
    default_temperature: float | None = Field(None, ge=0.0, le=2.0, description="默认温度")
    default_max_tokens: int | None = Field(None, ge=1, le=32768, description="默认最大token数")
    theme: str | None = Field(None, pattern="^(light|dark)$", description="主题(light/dark)")
    language: str | None = Field(None, min_length=2, max_length=10, description="语言")
    settings: dict | None = Field(None, description="其他设置")

    @field_validator("default_temperature")
    @classmethod
    def validate_temperature_field(cls, v: float) -> float:
        return validate_temperature(v)

    @field_validator("default_max_tokens")
    @classmethod
    def validate_max_tokens_field(cls, v: int) -> int:
        return validate_max_tokens(v)

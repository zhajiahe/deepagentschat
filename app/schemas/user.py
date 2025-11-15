"""
用户相关的 Pydantic Schema

用于 API 请求和响应的数据验证和序列化
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.validators import (
    EnhancedBaseModel,
    validate_email_domain,
    validate_nickname,
    validate_password_strength,
    validate_username,
)


class UserBase(EnhancedBaseModel):
    """用户基础字段"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    nickname: str = Field(..., min_length=2, max_length=50, description="昵称")

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: EmailStr) -> EmailStr:
        return validate_email_domain(str(v))

    @field_validator("nickname")
    @classmethod
    def validate_nickname_field(cls, v: str) -> str:
        return validate_nickname(v)


class UserCreate(UserBase):
    """创建用户请求"""

    password: str = Field(..., min_length=8, max_length=128, description="密码")
    is_active: bool = Field(default=True, description="是否激活")
    is_superuser: bool = Field(default=False, description="是否超级管理员")

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(EnhancedBaseModel):
    """更新用户请求"""

    email: EmailStr | None = Field(default=None, description="邮箱")
    nickname: str | None = Field(default=None, min_length=2, max_length=50, description="昵称")
    is_active: bool | None = Field(default=None, description="是否激活")
    is_superuser: bool | None = Field(default=None, description="是否超级管理员")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: EmailStr) -> EmailStr:
        return validate_email_domain(str(v))

    @field_validator("nickname")
    @classmethod
    def validate_nickname_field(cls, v: str) -> str:
        return validate_nickname(v)


class UserResponse(UserBase):
    """用户响应"""

    id: uuid.UUID = Field(..., description="用户ID(UUID)")
    is_active: bool = Field(..., description="是否激活")
    is_superuser: bool = Field(..., description="是否超级管理员")
    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    model_config = {"from_attributes": True}


class UserListQuery(BaseModel):
    """用户列表查询参数"""

    keyword: str | None = Field(default=None, description="搜索关键词（用户名、邮箱、昵称）")
    is_active: bool | None = Field(default=None, description="是否激活")
    is_superuser: bool | None = Field(default=None, description="是否超级管理员")


class PasswordChange(EnhancedBaseModel):
    """修改密码请求"""

    old_password: str = Field(..., min_length=1, description="旧密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        return validate_password_strength(v)

"""
对话相关的 Pydantic Schema

用于 LangGraph 对话系统的请求和响应数据验证
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求"""

    message: str = Field(..., description="用户消息")
    thread_id: str | None = Field(None, description="会话线程ID，不提供则创建新会话")
    user_id: int = Field(..., description="用户ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class ChatResponse(BaseModel):
    """对话响应"""

    thread_id: str = Field(..., description="会话线程ID")
    response: str = Field(..., description="助手回复")
    duration_ms: int = Field(..., description="执行时长(毫秒)")


class MessageResponse(BaseModel):
    """消息响应"""

    id: int = Field(..., description="消息ID")
    role: str = Field(..., description="角色(user/assistant/system)")
    content: str = Field(..., description="消息内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True

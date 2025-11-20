"""
对话相关的 Pydantic Schema

用于 LangGraph 对话系统的请求和响应数据验证
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """对话请求"""

    message: str = Field(..., description="用户消息")
    thread_id: str | None = Field(None, description="会话线程ID，不提供则创建新会话")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")
    # user_id 从认证中获取，不再需要在请求中提供


class ChatResponse(BaseModel):
    """对话响应"""

    thread_id: str = Field(..., description="会话线程ID")
    response: str = Field(..., description="助手回复")
    duration_ms: int = Field(..., description="执行时长(毫秒)")
    messages: list[dict[str, Any]] = Field(default_factory=list, description="本轮对话的所有消息（包括工具调用）")


class MessageResponse(BaseModel):
    """消息响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="消息ID")
    role: str = Field(..., description="角色(user/assistant/system)")
    content: str = Field(..., description="消息内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(..., description="创建时间")

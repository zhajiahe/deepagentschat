"""
会话相关的 Pydantic Schema

用于会话管理的请求和响应数据验证
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """创建会话请求"""

    user_id: int = Field(..., description="用户ID")
    title: str = Field(default="New Conversation", description="会话标题")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class ConversationUpdate(BaseModel):
    """更新会话请求"""

    title: str | None = Field(None, description="会话标题")
    metadata: dict[str, Any] | None = Field(None, description="元数据")


class ConversationResponse(BaseModel):
    """会话响应"""

    id: int = Field(..., description="会话ID")
    thread_id: str = Field(..., description="线程ID")
    user_id: int = Field(..., description="用户ID")
    title: str = Field(..., description="会话标题")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    message_count: int = Field(default=0, description="消息数量")

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """会话详情响应"""

    conversation: ConversationResponse
    messages: list[dict[str, Any]] = Field(default_factory=list, description="消息列表")


class ConversationExportResponse(BaseModel):
    """会话导出响应"""

    conversation: dict[str, Any]
    messages: list[dict[str, Any]]
    state: dict[str, Any] | None = None


class ConversationImportRequest(BaseModel):
    """会话导入请求"""

    user_id: int = Field(..., description="用户ID")
    data: dict[str, Any] = Field(..., description="导入数据")


class StateResponse(BaseModel):
    """状态响应"""

    thread_id: str
    values: dict[str, Any]
    next: list[str] | None = None
    metadata: dict[str, Any] | None = None
    created_at: str | None = None
    parent_config: dict[str, Any] | None = None


class CheckpointResponse(BaseModel):
    """检查点响应"""

    thread_id: str
    checkpoints: list[dict[str, Any]]


class StateUpdateRequest(BaseModel):
    """状态更新请求"""

    state_update: dict[str, Any] = Field(..., description="状态更新数据")
    as_node: str | None = Field(None, description="作为哪个节点更新")


class SearchRequest(BaseModel):
    """搜索请求"""

    user_id: int = Field(..., description="用户ID")
    query: str = Field(..., description="搜索关键词")
    skip: int = Field(default=0, ge=0, description="跳过数量")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量")


class SearchResponse(BaseModel):
    """搜索响应"""

    query: str
    results: list[dict[str, Any]]


class UserStatsResponse(BaseModel):
    """用户统计响应"""

    user_id: str
    total_conversations: int
    total_messages: int
    recent_conversations: list[dict[str, Any]]

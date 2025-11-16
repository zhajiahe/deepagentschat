"""
会话模型

用于 LangGraph 对话系统的会话管理
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, UUID, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin

if TYPE_CHECKING:
    from app.models.message import Message


class Conversation(Base, BaseTableMixin):
    """会话表 - 存储对话会话信息

    继承自 BaseTableMixin,包含以下字段:
    - id: 主键ID
    - create_by: 创建人
    - update_by: 更新人
    - create_time: 创建时间
    - update_time: 更新时间
    - deleted: 逻辑删除标记
    """

    __tablename__ = "conversations"

    thread_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False, comment="线程ID")
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="用户ID(UUID)",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="会话标题")
    meta_data: Mapped[dict] = mapped_column(JSON, nullable=True, default={}, comment="元数据")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="是否激活(0:否 1:是)")

    # 关系定义：一个会话可以有多条消息，删除会话时级联删除消息
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, thread_id={self.thread_id}, title={self.title})>"

"""
消息模型

用于 LangGraph 对话系统的消息存储
"""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseTableMixin


class Message(Base, BaseTableMixin):
    """消息表 - 存储对话消息

    继承自 BaseTableMixin,包含以下字段:
    - id: 主键ID
    - create_by: 创建人
    - update_by: 更新人
    - create_time: 创建时间
    - update_time: 更新时间
    - deleted: 逻辑删除标记
    """

    __tablename__ = "messages"

    thread_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False, comment="线程ID")
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="角色(user/assistant/system)")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    meta_data: Mapped[dict] = mapped_column(JSON, nullable=True, default={}, comment="元数据")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, thread_id={self.thread_id}, role={self.role})>"

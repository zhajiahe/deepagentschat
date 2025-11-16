"""
用户设置模型

用于存储用户的个性化配置
"""

import uuid

from sqlalchemy import JSON, UUID, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseTableMixin


class UserSettings(Base, BaseTableMixin):
    """用户设置表 - 存储用户的个性化配置

    继承自 BaseTableMixin,包含以下字段:
    - id: 主键ID
    - create_by: 创建人
    - update_by: 更新人
    - create_time: 创建时间
    - update_time: 更新时间
    - deleted: 逻辑删除标记
    """

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
        comment="用户ID(UUID)",
    )
    # LLM 相关设置
    llm_model: Mapped[str] = mapped_column(String(100), nullable=True, default=None, comment="默认模型")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=True, default=None, comment="默认最大token数")
    # 其他设置
    settings: Mapped[dict] = mapped_column(JSON, nullable=True, default={}, comment="其他设置(JSON格式)")
    config: Mapped[dict] = mapped_column(JSON, nullable=True, default={}, comment="langgraph 配置(JSON格式)")
    context: Mapped[dict] = mapped_column(JSON, nullable=True, default={}, comment="langgraph context(JSON格式)")

    def __repr__(self) -> str:
        return f"<UserSettings(id={self.id}, user_id={self.user_id})>"

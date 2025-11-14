import uuid

from sqlalchemy import UUID, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseTableMixin


class User(Base, BaseTableMixin):
    """用户表模型"""

    __tablename__ = "users"

    # 覆盖 BaseTableMixin 的 id 字段，使用 UUID
    id: Mapped[uuid.UUID] = mapped_column(  # type: ignore[assignment]
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="用户ID(UUID)"
    )

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, comment="昵称")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, comment="加密密码")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否激活")
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否超级管理员")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

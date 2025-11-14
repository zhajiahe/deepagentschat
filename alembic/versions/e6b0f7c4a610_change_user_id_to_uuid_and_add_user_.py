"""change_user_id_to_uuid_and_add_user_settings

Revision ID: e6b0f7c4a610
Revises: 145548601196
Create Date: 2025-11-14 15:51:39.977181

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6b0f7c4a610"
down_revision: str | Sequence[str] | None = "145548601196"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite 不支持直接修改列类型，需要重建表
    # 注意：这是一个破坏性迁移，会删除所有现有数据

    # 删除旧表（如果存在）
    op.drop_table("execution_logs", if_exists=True)
    op.drop_table("writes", if_exists=True)
    op.drop_table("checkpoints", if_exists=True)

    # 删除外键约束
    op.drop_table("user_settings", if_exists=True)
    op.drop_table("conversations", if_exists=True)

    # 重建 users 表（使用 UUID）
    op.drop_table("users", if_exists=True)
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False, comment="用户ID(UUID)"),
        sa.Column("username", sa.String(length=50), nullable=False, comment="用户名"),
        sa.Column("email", sa.String(length=100), nullable=False, comment="邮箱"),
        sa.Column("nickname", sa.String(length=50), nullable=False, comment="昵称"),
        sa.Column("hashed_password", sa.String(length=255), nullable=False, comment="加密密码"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否激活"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, comment="是否超级管理员"),
        sa.Column("create_by", sa.String(length=50), nullable=True, comment="创建人"),
        sa.Column("update_by", sa.String(length=50), nullable=True, comment="更新人"),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("deleted", sa.Integer(), nullable=False, comment="逻辑删除(0:未删除 1:已删除)"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    # 重建 conversations 表（使用 UUID user_id）
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("thread_id", sa.String(length=100), nullable=False, comment="线程ID"),
        sa.Column("user_id", sa.UUID(), nullable=False, comment="用户ID(UUID)"),
        sa.Column("title", sa.String(length=200), nullable=False, comment="会话标题"),
        sa.Column("meta_data", sa.JSON(), nullable=True, comment="元数据"),
        sa.Column("is_active", sa.Integer(), nullable=False, comment="是否激活(0:否 1:是)"),
        sa.Column("create_by", sa.String(length=50), nullable=True, comment="创建人"),
        sa.Column("update_by", sa.String(length=50), nullable=True, comment="更新人"),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("deleted", sa.Integer(), nullable=False, comment="逻辑删除(0:未删除 1:已删除)"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index(op.f("ix_conversations_thread_id"), "conversations", ["thread_id"], unique=False)
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

    # 创建 user_settings 表
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("user_id", sa.UUID(), nullable=False, comment="用户ID(UUID)"),
        sa.Column("default_model", sa.String(length=100), nullable=True, comment="默认模型"),
        sa.Column("default_temperature", sa.Float(), nullable=True, comment="默认温度"),
        sa.Column("default_max_tokens", sa.Integer(), nullable=True, comment="默认最大token数"),
        sa.Column("theme", sa.String(length=20), nullable=True, comment="主题(light/dark)"),
        sa.Column("language", sa.String(length=10), nullable=True, comment="语言"),
        sa.Column("settings", sa.JSON(), nullable=True, comment="其他设置(JSON格式)"),
        sa.Column("create_by", sa.String(length=50), nullable=True, comment="创建人"),
        sa.Column("update_by", sa.String(length=50), nullable=True, comment="更新人"),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("deleted", sa.Integer(), nullable=False, comment="逻辑删除(0:未删除 1:已删除)"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_settings_user_id"), "user_settings", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 删除新表
    op.drop_table("user_settings")
    op.drop_table("conversations")
    op.drop_table("users")

    # 重建旧表（使用 INTEGER user_id）
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("username", sa.String(length=50), nullable=False, comment="用户名"),
        sa.Column("email", sa.String(length=100), nullable=False, comment="邮箱"),
        sa.Column("nickname", sa.String(length=50), nullable=False, comment="昵称"),
        sa.Column("hashed_password", sa.String(length=255), nullable=False, comment="加密密码"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否激活"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, comment="是否超级管理员"),
        sa.Column("create_by", sa.String(length=50), nullable=True, comment="创建人"),
        sa.Column("update_by", sa.String(length=50), nullable=True, comment="更新人"),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("deleted", sa.Integer(), nullable=False, comment="逻辑删除(0:未删除 1:已删除)"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("thread_id", sa.String(length=100), nullable=False, comment="线程ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("title", sa.String(length=200), nullable=False, comment="会话标题"),
        sa.Column("meta_data", sa.JSON(), nullable=True, comment="元数据"),
        sa.Column("is_active", sa.Integer(), nullable=False, comment="是否激活(0:否 1:是)"),
        sa.Column("create_by", sa.String(length=50), nullable=True, comment="创建人"),
        sa.Column("update_by", sa.String(length=50), nullable=True, comment="更新人"),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("deleted", sa.Integer(), nullable=False, comment="逻辑删除(0:未删除 1:已删除)"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index(op.f("ix_conversations_thread_id"), "conversations", ["thread_id"], unique=False)
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

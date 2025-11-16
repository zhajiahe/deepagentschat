"""♻️ refactor: 更新用户设置表结构

Revision ID: cbd3678f829b
Revises: d0206113cbfd
Create Date: 2025-11-17 07:35:53.144364

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cbd3678f829b"
down_revision: str | Sequence[str] | None = "d0206113cbfd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 更新 user_settings 表结构
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        # 添加新列
        batch_op.add_column(sa.Column("llm_model", sa.String(length=100), nullable=True, comment="默认模型"))
        batch_op.add_column(sa.Column("max_tokens", sa.Integer(), nullable=True, comment="默认最大token数"))
        batch_op.add_column(sa.Column("config", sa.JSON(), nullable=True, comment="langgraph 配置(JSON格式)"))
        batch_op.add_column(sa.Column("context", sa.JSON(), nullable=True, comment="langgraph context(JSON格式)"))

        # 删除旧列
        batch_op.drop_column("theme")
        batch_op.drop_column("language")
        batch_op.drop_column("default_model")
        batch_op.drop_column("default_temperature")
        batch_op.drop_column("default_max_tokens")


def downgrade() -> None:
    """Downgrade schema."""
    # 恢复 user_settings 表结构
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        # 恢复旧列
        batch_op.add_column(sa.Column("default_max_tokens", sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column("default_temperature", sa.FLOAT(), nullable=True))
        batch_op.add_column(sa.Column("default_model", sa.VARCHAR(length=100), nullable=True))
        batch_op.add_column(sa.Column("language", sa.VARCHAR(length=10), nullable=True))
        batch_op.add_column(sa.Column("theme", sa.VARCHAR(length=20), nullable=True))

        # 删除新列
        batch_op.drop_column("context")
        batch_op.drop_column("config")
        batch_op.drop_column("max_tokens")
        batch_op.drop_column("llm_model")

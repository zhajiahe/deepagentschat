"""remove_execution_logs_table

Revision ID: 085fc16b389b
Revises: 145548601196
Create Date: 2025-11-14 12:03:27.800779

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "085fc16b389b"
down_revision: str | Sequence[str] | None = "145548601196"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop execution_logs table
    op.drop_index(op.f("ix_execution_logs_thread_id"), table_name="execution_logs")
    op.drop_table("execution_logs")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate execution_logs table
    op.create_table(
        "execution_logs",
        sa.Column("thread_id", sa.String(length=100), nullable=False, comment="线程ID"),
        sa.Column("node_name", sa.String(length=100), nullable=True, comment="节点名称"),
        sa.Column("input_data", sa.JSON(), nullable=True, comment="输入数据"),
        sa.Column("output_data", sa.JSON(), nullable=True, comment="输出数据"),
        sa.Column("duration_ms", sa.Integer(), nullable=True, comment="执行时长(毫秒)"),
        sa.Column("status", sa.String(length=20), nullable=True, comment="状态(success/error)"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
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
    )
    op.create_index(op.f("ix_execution_logs_thread_id"), "execution_logs", ["thread_id"], unique=False)

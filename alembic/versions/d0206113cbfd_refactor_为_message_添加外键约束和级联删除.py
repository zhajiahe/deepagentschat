"""♻️ refactor: 为 Message 添加外键约束和级联删除

Revision ID: d0206113cbfd
Revises: e6b0f7c4a610
Create Date: 2025-11-17 07:26:13.382872

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0206113cbfd"
down_revision: str | Sequence[str] | None = "e6b0f7c4a610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 为 messages 表添加外键约束，指向 conversations 表
    # 当删除 conversation 时，相关的 messages 会自动级联删除
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_messages_thread_id", "conversations", ["thread_id"], ["thread_id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 messages 表的外键约束
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_constraint("fk_messages_thread_id", type_="foreignkey")

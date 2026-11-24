"""trgm indexes for story search

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-22

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # нечёткий поиск по подстроке в заголовке, имени и описании
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stories_title_trgm ON stories USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stories_woman_name_trgm ON stories USING gin (woman_name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stories_short_desc_trgm ON stories USING gin (short_description gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stories_short_desc_trgm")
    op.execute("DROP INDEX IF EXISTS ix_stories_woman_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_stories_title_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")

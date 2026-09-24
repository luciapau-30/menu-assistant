"""Persist extracted items, reviewed reports, profile snapshots, and errors."""
from alembic import op
import sqlalchemy as sa

revision = "a832d610ea01"
down_revision = "fc8e5b064811"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("analyses", sa.Column("extraction", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("reports", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("profile_snapshot", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("error_message", sa.String(), nullable=True))


def downgrade():
    for column in ("error_message", "profile_snapshot", "reports", "extraction"):
        op.drop_column("analyses", column)

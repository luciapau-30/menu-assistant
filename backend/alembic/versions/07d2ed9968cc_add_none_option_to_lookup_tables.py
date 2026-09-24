"""add none option to lookup tables

Revision ID: 07d2ed9968cc
Revises: 1c38887bedf9
Create Date: 2026-07-20 13:19:42.583581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07d2ed9968cc'
down_revision: Union[str, Sequence[str], None] = '1c38887bedf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LOOKUP_TABLES = [
    "allergens",
    "medical_restrictions",
    "dietary_styles",
    "nutrition_goals",
]


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in LOOKUP_TABLES:
        table = sa.table(table_name, sa.column("name", sa.String))
        op.bulk_insert(table, [{"name": "None"}])


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in LOOKUP_TABLES:
        op.execute(f"DELETE FROM {table_name} WHERE name = 'None'")

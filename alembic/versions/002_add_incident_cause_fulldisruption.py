"""Add cause and fulldisruption to incidents

Revision ID: 002
Revises: 001
Create Date: 2025-02-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cause of traffic disruption (e.g. vehicle breakdown, accident) - nullable
    op.execute("""
        ALTER TABLE incidentstablenew
        ADD COLUMN IF NOT EXISTS cause VARCHAR NULL;
    """)
    # Full or half road closure - nullable, default false for road closure incidents
    op.execute("""
        ALTER TABLE incidentstablenew
        ADD COLUMN IF NOT EXISTS fulldisruption BOOLEAN NULL DEFAULT false;
    """)


def downgrade() -> None:
    op.execute('ALTER TABLE incidentstablenew DROP COLUMN IF EXISTS cause')
    op.execute('ALTER TABLE incidentstablenew DROP COLUMN IF EXISTS fulldisruption')

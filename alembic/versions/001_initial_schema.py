"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-10-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: Most tables already exist from app/qu.sql
    # This migration adds the upvotes column and activitylogs table
    
    # Add upvotes column to incidentstablenew if not exists
    try:
        op.execute('ALTER TABLE incidentstablenew ADD COLUMN IF NOT EXISTS upvotes INTEGER NOT NULL DEFAULT 0')
    except Exception:
        pass

    # Add startdate and enddate columns to incidentstablenew if not exists
    try:
        op.execute("""
        ALTER TABLE incidentstablenew 
        ADD COLUMN IF NOT EXISTS startdate TIMESTAMP NULL;
    """)
    except Exception:
        pass

    try:
        op.execute("""
        ALTER TABLE incidentstablenew 
        ADD COLUMN IF NOT EXISTS enddate TIMESTAMP NULL;
    """)
    except Exception:
        pass
    
    # Create activitylogs table
    op.create_table(
        'activitylogs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('action_type', sa.String()),
        sa.Column('module', sa.String()),
        sa.Column('userid', sa.String()),
        sa.Column('email', sa.String()),
        sa.Column('method', sa.String()),
        sa.Column('path', sa.String()),
        sa.Column('ip', sa.String()),
        sa.Column('user_agent', sa.String()),
        sa.Column('status_code', sa.Integer()),
        sa.Column('request_body_json', sa.Text()),
        sa.Column('response_body_json', sa.Text()),
        sa.Column('datecreated', sa.DateTime(), nullable=False),
    )
    
    # Create indexes
    op.create_index('idx_activitylogs_created', 'activitylogs', ['datecreated'], unique=False)
    op.create_index('idx_activitylogs_user', 'activitylogs', ['userid'], unique=False)
    op.create_index('idx_activitylogs_module', 'activitylogs', ['module'], unique=False)
    op.create_index('idx_activitylogs_action', 'activitylogs', ['action_type'], unique=False)
    op.create_index('idx_incidents_status_date', 'incidentstablenew', ['status', 'datecreated'], unique=False)
    op.create_index('idx_incidents_category_date', 'incidentstablenew', ['incidentcategoryid', 'datecreated'], unique=False)
    op.create_index('idx_incidents_upvotes', 'incidentstablenew', ['upvotes'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_incidents_upvotes', table_name='incidentstablenew')
    op.drop_index('idx_incidents_category_date', table_name='incidentstablenew')
    op.drop_index('idx_incidents_status_date', table_name='incidentstablenew')
    op.drop_index('idx_activitylogs_action', table_name='activitylogs')
    op.drop_index('idx_activitylogs_module', table_name='activitylogs')
    op.drop_index('idx_activitylogs_user', table_name='activitylogs')
    op.drop_index('idx_activitylogs_created', table_name='activitylogs')
    op.drop_table('activitylogs')
    op.execute('ALTER TABLE incidentstablenew DROP COLUMN IF EXISTS upvotes')
    op.execute('ALTER TABLE incidentstablenew DROP COLUMN IF EXISTS startdate')
    op.execute('ALTER TABLE incidentstablenew DROP COLUMN IF EXISTS enddate')


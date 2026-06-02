"""Increase session_name VARCHAR length from 50 to 200

Revision ID: 002_increase_session_name_length
Revises: 001_add_delivery_sessions
Create Date: 2026-02-01 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_increase_session_name_length'
down_revision = '001_add_delivery_sessions'
branch_labels = None
depends_on = None


def upgrade():
    """Aumentar session_name de VARCHAR(50) para VARCHAR(200)"""
    # PostgreSQL syntax para alterar coluna
    op.alter_column('sessions', 'session_name',
                   existing_type=sa.String(50),
                   type_=sa.String(200),
                   existing_nullable=False)
    print("✅ Campo session_name aumentado de 50 para 200 caracteres")


def downgrade():
    """Reverter session_name de VARCHAR(200) para VARCHAR(50)"""
    op.alter_column('sessions', 'session_name',
                   existing_type=sa.String(200),
                   type_=sa.String(50),
                   existing_nullable=False)
    print("⏮️ Campo session_name reduzido de 200 para 50 caracteres")

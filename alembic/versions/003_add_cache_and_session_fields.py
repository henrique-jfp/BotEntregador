"""Add provider and created_at to geocoding_cache and current_step to sessions

Revision ID: 003_add_cache_and_session_fields
Revises: 002_increase_session_name_length
Create Date: 2026-06-05 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_cache_and_session_fields'
down_revision = '002_increase_session_name_length'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Atualiza geocoding_cache
    op.add_column('geocoding_cache', sa.Column('provider', sa.String(50), nullable=True))
    op.add_column('geocoding_cache', sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True))
    # Adiciona índice se não existir (opcional mas recomendado)
    # op.create_index('idx_geocoding_cache_address', 'geocoding_cache', ['address'])
    
    # 2. Atualiza sessions
    op.add_column('sessions', sa.Column('current_step', sa.String(50), server_default='idle', nullable=True))
    
    print("✅ Colunas provider, created_at adicionadas a geocoding_cache")
    print("✅ Coluna current_step adicionada a sessions")


def downgrade():
    # 1. Reverte geocoding_cache
    op.drop_column('geocoding_cache', 'created_at')
    op.drop_column('geocoding_cache', 'provider')
    
    # 2. Reverte sessions
    op.drop_column('sessions', 'current_step')
    
    print("⏮️ Colunas removidas com sucesso")

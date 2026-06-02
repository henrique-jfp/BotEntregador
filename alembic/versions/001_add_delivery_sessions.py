"""Initial migration: Add delivery sessions schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '001_add_delivery_sessions'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create new session management tables"""
    
    # ==================== CREATE ENUMS ====================
    
    # SessionStatus enum
    session_status = postgresql.ENUM(
        'open', 'active', 'completed', 'paused', 'archived',
        name='sessionstatus', create_type=True
    )
    session_status.create(op.get_bind(), checkfirst=True)
    
    # DeliveryStatus enum
    delivery_status = postgresql.ENUM(
        'pending', 'picked_up', 'delivered', 'failed',
        name='deliverystatus', create_type=True
    )
    delivery_status.create(op.get_bind(), checkfirst=True)
    
    # ==================== CREATE TABLES ====================
    
    # SessionAudit (dependency for others)
    op.create_table(
        'session_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_session_audit_session_id', 'session_id'),
        sa.Index('ix_session_audit_created_at', 'created_at'),
        sa.Index('ix_session_audit_action', 'action')
    )
    
    # DeliverySession (main table)
    op.create_table(
        'delivery_sessions',
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', session_status, nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.Column('session_type', sa.String(20), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('total_packages', sa.Integer(), default=0),
        sa.Column('total_deliverers', sa.Integer(), default=0),
        sa.Column('total_cost', sa.Float(), default=0.0),
        sa.Column('total_revenue', sa.Float(), default=0.0),
        sa.Column('total_profit', sa.Float(), default=0.0),
        sa.Column('is_readonly', sa.Boolean(), default=False),
        sa.Column('was_reused', sa.Boolean(), default=False),
        sa.Column('reuse_count', sa.Integer(), default=0),
        sa.Column('financial_snapshot', sa.JSON(), nullable=True),
        sa.Column('route_optimization_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('session_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('ix_delivery_sessions_user_id', 'user_id'),
        sa.Index('ix_delivery_sessions_status', 'status'),
        sa.Index('ix_delivery_sessions_created_at', 'created_at'),
        sa.Index('ix_delivery_sessions_started_at', 'started_at')
    )
    
    # SessionAddress
    op.create_table(
        'session_addresses',
        sa.Column('address_id', sa.String(36), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('package_count', sa.Integer(), default=1),
        sa.Column('geocoding_cache', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('address_id'),
        sa.ForeignKeyConstraint(['session_id'], ['delivery_sessions.session_id'], ondelete='CASCADE'),
        sa.Index('ix_session_addresses_session_id', 'session_id'),
        sa.Index('ix_session_addresses_address', 'address')
    )
    
    # SessionPackage
    op.create_table(
        'session_packages',
        sa.Column('package_id', sa.String(36), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('barcode', sa.String(100), nullable=False),
        sa.Column('address_id', sa.String(36), nullable=False),
        sa.Column('recipient_name', sa.String(255), nullable=True),
        sa.Column('recipient_phone', sa.String(20), nullable=True),
        sa.Column('address_full', sa.String(500), nullable=False),
        sa.Column('delivery_status', delivery_status, nullable=False, server_default='pending'),
        sa.Column('assigned_deliverer_id', sa.Integer(), nullable=True),
        sa.Column('package_value', sa.Float(), default=0.0),
        sa.Column('delivery_fee', sa.Float(), default=0.0),
        sa.Column('delivery_time', sa.DateTime(), nullable=True),
        sa.Column('delivery_notes', sa.String(500), nullable=True),
        sa.Column('barcode_ocr_attempt', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('package_id'),
        sa.ForeignKeyConstraint(['session_id'], ['delivery_sessions.session_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['address_id'], ['session_addresses.address_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_deliverer_id'], ['users.id'], ondelete='SET NULL'),
        sa.Index('ix_session_packages_session_id', 'session_id'),
        sa.Index('ix_session_packages_barcode', 'barcode'),
        sa.Index('ix_session_packages_delivery_status', 'delivery_status'),
        sa.Index('ix_session_packages_assigned_deliverer_id', 'assigned_deliverer_id')
    )
    
    # SessionDeliverer
    op.create_table(
        'session_deliverers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('deliverer_id', sa.Integer(), nullable=False),
        sa.Column('packages_assigned', sa.Integer(), default=0),
        sa.Column('packages_delivered', sa.Integer(), default=0),
        sa.Column('base_salary', sa.Float(), default=3000.0),
        sa.Column('commission_per_delivery', sa.Float(), default=5.0),
        sa.Column('total_earned', sa.Float(), default=0.0),
        sa.Column('total_distance', sa.Float(), nullable=True),
        sa.Column('estimated_time', sa.Float(), nullable=True),
        sa.Column('route_optimization', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['delivery_sessions.session_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['deliverer_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('session_id', 'deliverer_id', name='uq_session_deliverer'),
        sa.Index('ix_session_deliverers_session_id', 'session_id'),
        sa.Index('ix_session_deliverers_deliverer_id', 'deliverer_id')
    )


def downgrade() -> None:
    """Drop session management tables"""
    
    op.drop_table('session_deliverers')
    op.drop_table('session_packages')
    op.drop_table('session_addresses')
    op.drop_table('delivery_sessions')
    op.drop_table('session_audit')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS deliverystatus CASCADE')
    op.execute('DROP TYPE IF EXISTS sessionstatus CASCADE')

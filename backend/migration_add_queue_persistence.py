"""
Alembic Migration: Add Job Queue Persistence and System Metrics

Revision ID: add_queue_persistence
Revises: previous_revision
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_queue_persistence'
down_revision = None  # Update with your previous revision
branch_labels = None
depends_on = None

def upgrade():
    """Add new tables and columns for queue persistence and metrics"""
    
    # Add new columns to printers table
    op.add_column('printers', sa.Column('job_queue', postgresql.JSON, nullable=True))
    op.add_column('printers', sa.Column('current_job_id', sa.String(50), nullable=True))
    op.add_column('printers', sa.Column('queue_length', sa.Integer, default=0))
    op.add_column('printers', sa.Column('temperature', sa.Float, default=22.0))
    op.add_column('printers', sa.Column('humidity', sa.Float, default=45.0))
    op.add_column('printers', sa.Column('total_pages_printed', sa.Integer, default=0))
    op.add_column('printers', sa.Column('last_maintenance', sa.DateTime, server_default=sa.func.now()))
    
    # Add new columns to orders table
    op.add_column('orders', sa.Column('queue_position', sa.Integer, nullable=True))
    op.add_column('orders', sa.Column('scheduler_score', sa.Float, nullable=True))
    op.add_column('orders', sa.Column('scheduler_metadata', postgresql.JSON, nullable=True))
    
    # Add new status to OrderStatusEnum
    op.execute("ALTER TYPE orderstatusenum ADD VALUE IF NOT EXISTS 'Queued'")
    
    # Add new status to PaymentStatusEnum
    op.execute("ALTER TYPE paymentstatusenum ADD VALUE IF NOT EXISTS 'Refunded'")
    
    # Add new alert types
    op.execute("ALTER TYPE alerttypeenum ADD VALUE IF NOT EXISTS 'queue_full'")
    op.execute("ALTER TYPE alerttypeenum ADD VALUE IF NOT EXISTS 'resource_low'")
    
    # Add new printer statuses
    op.execute("ALTER TYPE printerstatusenum ADD VALUE IF NOT EXISTS 'Busy'")
    op.execute("ALTER TYPE printerstatusenum ADD VALUE IF NOT EXISTS 'Idle'")
    
    # Add metadata column to alerts
    # op.add_column('alerts', sa.Column('metadata', postgresql.JSON, nullable=True))
    
    # Create JobQueueStatusEnum
    jobqueuestatus_enum = postgresql.ENUM(
        'queued', 'processing', 'completed', 'failed', 'cancelled',
        name='jobqueuestatusenum',
        create_type=True
    )
    jobqueuestatus_enum.create(op.get_bind(), checkfirst=True)
    
    # Create job_queue_entries table
    op.create_table(
        'job_queue_entries',
        sa.Column('queue_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('printer_id', sa.String(50), sa.ForeignKey('printers.printer_id'), nullable=False),
        sa.Column('order_id', sa.String(50), sa.ForeignKey('orders.order_id'), nullable=False),
        sa.Column('queue_position', sa.Integer, nullable=False),
        sa.Column('priority', sa.Integer, default=5),
        sa.Column('status', sa.Enum('queued', 'processing', 'completed', 'failed', 'cancelled', name='jobqueuestatusenum'), default='queued'),
        sa.Column('queued_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('suborder_types', postgresql.JSON, nullable=True),
        sa.Column('scheduler_score', sa.Float, nullable=True),
        sa.Column('estimated_duration_minutes', sa.Float, nullable=True),
        sa.UniqueConstraint('order_id', name='uq_order_id'),
        sa.Index('ix_job_queue_entries_printer_id', 'printer_id'),
        sa.Index('ix_job_queue_entries_order_id', 'order_id'),
        sa.Index('ix_job_queue_entries_queue_position', 'queue_position'),
        sa.Index('ix_job_queue_entries_status', 'status'),
        sa.Index('ix_job_queue_entries_queued_at', 'queued_at'),
    )
    
    # Create system_metrics table
    op.create_table(
        'system_metrics',
        sa.Column('metric_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now()),
        sa.Column('total_printers', sa.Integer, default=0),
        sa.Column('idle_printers', sa.Integer, default=0),
        sa.Column('busy_printers', sa.Integer, default=0),
        sa.Column('error_printers', sa.Integer, default=0),
        sa.Column('total_orders', sa.Integer, default=0),
        sa.Column('pending_orders', sa.Integer, default=0),
        sa.Column('processing_orders', sa.Integer, default=0),
        sa.Column('completed_orders', sa.Integer, default=0),
        sa.Column('failed_orders', sa.Integer, default=0),
        sa.Column('total_queued_jobs', sa.Integer, default=0),
        sa.Column('average_queue_length', sa.Float, default=0.0),
        sa.Column('max_queue_length', sa.Integer, default=0),
        sa.Column('average_wait_time_minutes', sa.Float, default=0.0),
        sa.Column('average_processing_time_minutes', sa.Float, default=0.0),
        sa.Column('success_rate_percentage', sa.Float, default=0.0),
        sa.Column('total_revenue', sa.Float, default=0.0),
        sa.Column('revenue_per_hour', sa.Float, default=0.0),
        # sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.Index('ix_system_metrics_timestamp', 'timestamp'),
    )
    
    print("✅ Migration completed: Added queue persistence and metrics tables")

def downgrade():
    """Remove queue persistence and metrics tables"""
    
    # Drop tables
    op.drop_table('system_metrics')
    op.drop_table('job_queue_entries')
    
    # Drop enum
    op.execute('DROP TYPE IF EXISTS jobqueuestatusenum')
    
    # Remove columns from printers
    op.drop_column('printers', 'job_queue')
    op.drop_column('printers', 'current_job_id')
    op.drop_column('printers', 'queue_length')
    op.drop_column('printers', 'temperature')
    op.drop_column('printers', 'humidity')
    op.drop_column('printers', 'total_pages_printed')
    op.drop_column('printers', 'last_maintenance')
    
    # Remove columns from orders
    op.drop_column('orders', 'queue_position')
    op.drop_column('orders', 'scheduler_score')
    op.drop_column('orders', 'scheduler_metadata')
    
    # Remove column from alerts
    # op.drop_column('alerts', 'metadata')
    
    print("✅ Migration downgrade completed")
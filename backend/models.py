"""
SQLAlchemy Database Models - Updated for new order format
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from database import Base
import enum
from typing import Optional

# ==================== Enums ====================

class RoleEnum(str, enum.Enum):
    OPERATOR = "operator"
    SUPERVISOR = "supervisor"
    OWNER = "owner"

class PrinterType(str, enum.Enum):
    INKJET = "Inkjet"
    LASER = "Laser"
    THERMAL = "Thermal"
    DOT_MATRIX = "Dot Matrix"

class PrinterConnectionType(str, enum.Enum):
    USB = "USB"
    WIFI = "WiFi"
    ETHERNET = "Ethernet"
    CLOUD_PRINT = "Cloud Print"

class PrinterStatusEnum(str, enum.Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    ERROR = "Error"
    MAINTENANCE = "Maintenance"
    BUSY = "Busy"
    IDLE = "Idle"

class StoreStatusEnum(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    PAUSED = "paused"

class OrderStatusEnum(str, enum.Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    PRINTED = "Printed"
    READY_FOR_DELIVERY = "Ready for delivery"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"
    FAILED = "Failed"
    QUEUED = "Queued"
    COMPLETED = "Completed"

class PaymentStatusEnum(str, enum.Enum):
    PAID = "Paid"
    UNPAID = "Unpaid"
    FAILED = "Failed"
    REFUNDED = "Refunded"

class AlertTypeEnum(str, enum.Enum):
    PAPER_EMPTY = "paper_empty"
    LOW_PAPER = "low_paper"
    LOW_INK = "low_ink"
    ORDER_DELAY = "order_delay"
    JAM = "jam"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    QUEUE_FULL = "queue_full"
    RESOURCE_LOW = "resource_low"
    OTHER = "other"

class AlertSeverityEnum(str, enum.Enum):
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"

class AlertStatusEnum(str, enum.Enum):
    UNREAD = "Unread"
    ACKNOWLEDGED = "Acknowledged"
    RESOLVED = "Resolved"

class JobQueueStatusEnum(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class QueryStatusEnum(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"

class QueryTypeEnum(str, enum.Enum):
    PRINTER = "printer"
    USER_ORDER = "user_order"
    INVENTORY = "inventory"
    SYSTEM = "system"
    OTHER = "other"

class PrinterDownReasonEnum(str, enum.Enum):
    PAPER_JAM = "paper_jam"
    TONER_EMPTY = "toner_empty"
    NETWORK_ISSUE = "network_issue"
    MAINTENANCE = "maintenance"
    OTHER = "other"

# ==================== Models ====================

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(50), primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    phone = Column(String(20))
    address = Column(Text)
    balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    orders = relationship("Order", back_populates="user")

class Store(Base):
    __tablename__ = "stores"
    
    store_id = Column(String(50), primary_key=True, index=True)
    store_name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    contact_number = Column(String(20))
    email = Column(String(255))
    business_hours = Column(JSON)
    pricing_info = Column(JSON)
    payment_modes = Column(JSON)
    status = Column(SQLEnum(StoreStatusEnum), default=StoreStatusEnum.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supervisors = relationship("SupervisorData", back_populates="store")
    printers = relationship("Printer", back_populates="store")
    orders = relationship("Order", back_populates="store")
    alerts = relationship("Alert", back_populates="store")
    job_queue_entries = relationship("JobQueueEntry", back_populates="store", cascade="all, delete-orphan")

class SupervisorData(Base):
    __tablename__ = "supervisor_data"
    
    admin_id = Column(String(50), primary_key=True, index=True)
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.OPERATOR)
    address = Column(Text)
    notification_preferences = Column(JSON, nullable=True)
    contact_number = Column(String(20))
    email = Column(String(255))
    available = Column(Boolean, default=True)
    permissions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships - ADD foreign_keys specification
    store = relationship("Store", back_populates="supervisors")
    assigned_orders = relationship("Order", back_populates="assigned_supervisor")
    alerts = relationship(
        "Alert", 
        back_populates="supervisor",
        foreign_keys="[Alert.supervisor_id]",  # Specify which foreign key to use
        overlaps="acknowledged_supervisor,fixed_supervisor"
    )

class Printer(Base):
    __tablename__ = "printers"
    
    printer_id = Column(String(50), primary_key=True, index=True)
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False)
    printer_name = Column(String(255), nullable=False)
    printer_model = Column(String(255))
    type = Column(SQLEnum(PrinterType), default=PrinterType.LASER)
    supported_sizes = Column(JSON)
    color_support = Column(Boolean, default=False)
    duplex_support = Column(Boolean, default=False)
    connection_type = Column(SQLEnum(PrinterConnectionType), default=PrinterConnectionType.USB)
    status = Column(SQLEnum(PrinterStatusEnum), default=PrinterStatusEnum.ONLINE)
    pages_printed = Column(Integer, default=0)
    paper_capacity = Column(Integer, default=500)
    paper_available = Column(Integer, default=500)
    ink_toner_level = Column(JSON)
    
    # Job queue persistence
    job_queue = Column(JSON, default=list)
    current_job_id = Column(String(50), nullable=True)
    queue_length = Column(Integer, default=0)
    
    unauthorized_access = Column(Boolean, default=False)
    assigned_supervisor_id = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Hardware simulation data
    temperature = Column(Float, default=22.0)
    humidity = Column(Float, default=45.0)
    total_pages_printed = Column(Integer, default=0)
    last_maintenance = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    store = relationship("Store", back_populates="printers")
    assigned_supervisor = relationship("SupervisorData")
    orders = relationship("Order", back_populates="printer")
    alerts = relationship("Alert", back_populates="printer")
    job_queue_entries = relationship("JobQueueEntry", back_populates="printer", order_by="JobQueueEntry.queue_position")

class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False)
    printer_id = Column(String(50), ForeignKey("printers.printer_id"), nullable=True, index=True)
    document_id = Column(String(255))
    order_date = Column(DateTime, default=datetime.utcnow, index=True)
    completion_date = Column(DateTime, nullable=True)
    status = Column(SQLEnum(OrderStatusEnum), default=OrderStatusEnum.PENDING, index=True)
    pages_count = Column(Integer, nullable=False)
    total_pdf_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    copies = Column(Integer, default=1)
    print_settings = Column(JSON)
    price = Column(Float, nullable=False)
    payment_status = Column(SQLEnum(PaymentStatusEnum), default=PaymentStatusEnum.UNPAID)
    assigned_supervisor_id = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=True)
    ready_for_delivery = Column(Boolean, default=False, index=True)
    binding_required = Column(Boolean, default=False, index=True)
    binding_done = Column(Boolean, default=False, index=True)
    delivery_details = Column(JSON)
    # Payment info
    razorpay_order_id = Column(String(100))
    razorpay_payment_id = Column(String(100))
    razorpay_signature = Column(String(255))
    
    # File storage
    file_url = Column(Text, nullable=True)
    
    # Bulk order tracking
    bulk_order_id = Column(String(50), nullable=True, index=True)
    
    # Scheduling fields
    estimated_start_time = Column(DateTime, nullable=True)
    estimated_end_time = Column(DateTime, nullable=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    
    # Queue tracking
    queue_position = Column(Integer, nullable=True)
    scheduler_score = Column(Float, nullable=True)
    scheduler_metadata = Column(JSON, nullable=True)
    
    # NEW: Add binding cost field
    binding_cost = Column(Float, default=0.0)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    store = relationship("Store", back_populates="orders")
    printer = relationship("Printer", back_populates="orders")
    assigned_supervisor = relationship("SupervisorData", back_populates="assigned_orders")
    alerts = relationship("Alert", back_populates="order")
    payment_transactions = relationship("PaymentTransaction", back_populates="order")
    history = relationship("OrderHistory", back_populates="order", order_by="OrderHistory.created_at")
    queue_entry = relationship("JobQueueEntry", back_populates="order", uselist=False)

class Alert(Base):
    __tablename__ = "alerts"
    
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False)
    printer_id = Column(String(50), ForeignKey("printers.printer_id"), nullable=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=True)
    supervisor_id = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=True)
    alert_type = Column(SQLEnum(AlertTypeEnum), nullable=False)
    alert_message = Column(Text, nullable=False)
    severity = Column(SQLEnum(AlertSeverityEnum), default=AlertSeverityEnum.INFO)
    status = Column(SQLEnum(AlertStatusEnum), default=AlertStatusEnum.UNREAD)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # NEW FIELDS
    acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_by = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    fixed = Column(Boolean, default=False, index=True)
    fixed_by = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=True)
    fixed_at = Column(DateTime, nullable=True)
    muted = Column(Boolean, default=False, index=True)
    muted_until = Column(DateTime, nullable=True)
    action_taken = Column(String(255), nullable=True)
    alert_metadata = Column('metadata', JSON, nullable=True)
    
    # Relationships - SPECIFY foreign_keys for each relationship
    store = relationship("Store", back_populates="alerts")
    printer = relationship("Printer", back_populates="alerts")
    order = relationship("Order", back_populates="alerts")
    supervisor = relationship(
        "SupervisorData", 
        back_populates="alerts", 
        foreign_keys=[supervisor_id]
    )
    acknowledged_supervisor = relationship(
        "SupervisorData", 
        foreign_keys=[acknowledged_by],
        overlaps="supervisor"
    )
    fixed_supervisor = relationship(
        "SupervisorData", 
        foreign_keys=[fixed_by],
        overlaps="supervisor,acknowledged_supervisor"
    )

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    
    transaction_id = Column(String(100), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False, index=True)
    razorpay_order_id = Column(String(100), unique=True, nullable=False)
    razorpay_payment_id = Column(String(100), unique=True)
    razorpay_signature = Column(String(255))
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(20), default="created")
    gateway_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="payment_transactions")

class OrderHistory(Base):
    __tablename__ = "order_history"
    
    history_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False, index=True)
    status = Column(SQLEnum(OrderStatusEnum), nullable=False)
    message = Column(Text)
    meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    order = relationship("Order", back_populates="history")

class JobQueueEntry(Base):
    """
    Persistent job queue storage - tracks job position in printer queues
    """
    __tablename__ = "job_queue_entries"
    
    queue_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # NEW STORE COLUMN
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False, index=True)
    
    printer_id = Column(String(50), ForeignKey("printers.printer_id"), nullable=False, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False, unique=True, index=True)

    # Queue management
    queue_position = Column(Integer, nullable=False, index=True)
    priority = Column(Integer, default=5)
    
    # Status
    status = Column(SQLEnum(JobQueueStatusEnum), default=JobQueueStatusEnum.QUEUED, index=True)
    
    # Timing
    queued_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    suborder_types = Column(JSON, nullable=True)
    scheduler_score = Column(Float, nullable=True)
    estimated_duration_minutes = Column(Float, nullable=True)
    
    # Relationships
    printer = relationship("Printer", back_populates="job_queue_entries")
    order = relationship("Order", back_populates="queue_entry")
    store = relationship("Store", back_populates="job_queue_entries")
    
    def __repr__(self):
        return f"<JobQueueEntry(store={self.store_id}, printer={self.printer_id}, order={self.order_id}, pos={self.queue_position})>"


class SystemMetrics(Base):
    """
    Store system performance metrics over time
    """
    __tablename__ = "system_metrics"
    
    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Printer metrics
    total_printers = Column(Integer, default=0)
    idle_printers = Column(Integer, default=0)
    busy_printers = Column(Integer, default=0)
    error_printers = Column(Integer, default=0)
    
    # Order metrics
    total_orders = Column(Integer, default=0)
    pending_orders = Column(Integer, default=0)
    processing_orders = Column(Integer, default=0)
    completed_orders = Column(Integer, default=0)
    failed_orders = Column(Integer, default=0)
    
    # Queue metrics
    total_queued_jobs = Column(Integer, default=0)
    average_queue_length = Column(Float, default=0.0)
    max_queue_length = Column(Integer, default=0)
    
    # Performance metrics
    average_wait_time_minutes = Column(Float, default=0.0)
    average_processing_time_minutes = Column(Float, default=0.0)
    success_rate_percentage = Column(Float, default=0.0)
    
    # Revenue metrics
    total_revenue = Column(Float, default=0.0)
    revenue_per_hour = Column(Float, default=0.0)
    
    def __repr__(self):
        return f"<SystemMetrics(timestamp={self.timestamp}, orders={self.total_orders})>"
    
class SupervisorActivityLog(Base):
    """Tracks all supervisor actions"""
    __tablename__ = "supervisor_activity_logs"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    supervisor_id = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=False, index=True)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(45), nullable=True)
    
    # Relationships
    supervisor = relationship("SupervisorData")

class SupervisorQuery(Base):
    """Supervisor-raised issues/queries"""
    __tablename__ = "supervisor_queries"
    
    query_id = Column(String(50), primary_key=True, index=True)
    supervisor_id = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=False)
    query_type = Column(SQLEnum(QueryTypeEnum), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(QueryStatusEnum), default=QueryStatusEnum.OPEN, index=True)
    priority = Column(SQLEnum(AlertSeverityEnum), default=AlertSeverityEnum.INFO)
    
    # Related entities
    printer_id = Column(String(50), ForeignKey("printers.printer_id"), nullable=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=True)
    
    # File attachment
    file_url = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    supervisor = relationship("SupervisorData")
    printer = relationship("Printer")
    order = relationship("Order")

class PrinterDownHistory(Base):
    """Tracks printer downtime with reasons"""
    __tablename__ = "printer_down_history"
    
    history_id = Column(Integer, primary_key=True, autoincrement=True)
    printer_id = Column(String(50), ForeignKey("printers.printer_id"), nullable=False, index=True)
    supervisor_id = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=False)
    reason = Column(SQLEnum(PrinterDownReasonEnum), nullable=False)
    description = Column(Text, nullable=True)
    down_time = Column(DateTime, default=datetime.utcnow, index=True)
    up_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Relationships
    printer = relationship("Printer")
    supervisor = relationship("SupervisorData")
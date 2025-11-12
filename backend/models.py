"""
SQLAlchemy Database Models - Updated with User table
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

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

class StoreStatusEnum(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    PAUSED = "paused"

class OrderStatusEnum(str, enum.Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    FAILED = "Failed"

class PaymentStatusEnum(str, enum.Enum):
    PAID = "Paid"
    UNPAID = "Unpaid"
    FAILED = "Failed"

class AlertTypeEnum(str, enum.Enum):
    PAPER_EMPTY = "paper_empty"
    LOW_PAPER = "low_paper"
    LOW_INK = "low_ink"
    ORDER_DELAY = "order_delay"
    JAM = "jam"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    OTHER = "other"

class AlertSeverityEnum(str, enum.Enum):
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"

class AlertStatusEnum(str, enum.Enum):
    UNREAD = "Unread"
    ACKNOWLEDGED = "Acknowledged"
    RESOLVED = "Resolved"

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

class SupervisorData(Base):
    __tablename__ = "supervisor_data"
    
    admin_id = Column(String(50), primary_key=True, index=True)
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.OPERATOR)
    address = Column(Text)
    contact_number = Column(String(20))
    email = Column(String(255))
    available = Column(Boolean, default=True)
    permissions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    store = relationship("Store", back_populates="supervisors")
    assigned_orders = relationship("Order", back_populates="assigned_supervisor")
    alerts = relationship("Alert", back_populates="supervisor")

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
    unauthorized_access = Column(Boolean, default=False)
    assigned_supervisor_id = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    store = relationship("Store", back_populates="printers")
    assigned_supervisor = relationship("SupervisorData")
    orders = relationship("Order", back_populates="printer")
    alerts = relationship("Alert", back_populates="printer")

class Order(Base):
    __tablename__ = "orders"
    
    order_id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False)
    printer_id = Column(String(50), ForeignKey("printers.printer_id"), nullable=True)
    document_id = Column(String(255))
    order_date = Column(DateTime, default=datetime.utcnow, index=True)
    completion_date = Column(DateTime, nullable=True)
    status = Column(SQLEnum(OrderStatusEnum), default=OrderStatusEnum.PENDING, index=True)
    pages_count = Column(Integer, nullable=False)
    copies = Column(Integer, default=1)
    print_settings = Column(JSON)
    price = Column(Float, nullable=False)
    payment_status = Column(SQLEnum(PaymentStatusEnum), default=PaymentStatusEnum.UNPAID)
    assigned_supervisor_id = Column(String(50), ForeignKey("supervisor_data.admin_id"), nullable=True)
    razorpay_order_id = Column(String(100), unique=True)
    razorpay_payment_id = Column(String(100), unique=True)
    razorpay_signature = Column(String(255))
    file_url = Column(Text, nullable=True)
    
    # Scheduling fields
    estimated_start_time = Column(DateTime, nullable=True)
    estimated_end_time = Column(DateTime, nullable=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    store = relationship("Store", back_populates="orders")
    printer = relationship("Printer", back_populates="orders")
    assigned_supervisor = relationship("SupervisorData", back_populates="assigned_orders")
    alerts = relationship("Alert", back_populates="order")
    payment_transactions = relationship("PaymentTransaction", back_populates="order")
    history = relationship("OrderHistory", back_populates="order", order_by="OrderHistory.created_at")

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
    
    # Relationships
    store = relationship("Store", back_populates="alerts")
    printer = relationship("Printer", back_populates="alerts")
    order = relationship("Order", back_populates="alerts")
    supervisor = relationship("SupervisorData", back_populates="alerts")

# Add these classes to your existing models.py file

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    
    transaction_id = Column(String(100), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    razorpay_order_id = Column(String(100), unique=True, nullable=False)
    razorpay_payment_id = Column(String(100), unique=True)
    razorpay_signature = Column(String(255))
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(20), default="created")  # created, success, failed
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
    meta = Column(JSON)  # Store any additional context
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    # Relationships
    order = relationship("Order", back_populates="history")

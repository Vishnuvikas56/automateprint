from fastapi import APIRouter, Depends, HTTPException, status, Header, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from typing import Optional, List
import bcrypt
import jwt
import uuid
import logging
from database import get_db
from models import SupervisorData, Store, Order, User, Printer, OrderHistory, Alert, JobQueueEntry, PrinterDownHistory
from models import (
    OrderStatusEnum, PaymentStatusEnum, PrinterStatusEnum, AlertTypeEnum, 
    AlertSeverityEnum, JobQueueStatusEnum, SupervisorQuery, PrinterDownReasonEnum,
    PrinterType, PrinterConnectionType, RoleEnum, AlertStatusEnum, QueryStatusEnum, SupervisorActivityLog, QueryTypeEnum
)
import secrets
from fastapi.security import OAuth2PasswordBearer
import enum
import httpx

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/supervisor/signin")

router = APIRouter(prefix="/supervisor", tags=["Supervisor Authentication"])

# Configuration
SECRET_KEY = "8KREnQ5tYgw7WcXCCLe97kzlzM4HQAXMIgp9J8bK4EM"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Setup logger
logger = logging.getLogger("supervisor_auth")

# ==================== Pydantic Models ====================

class SupervisorSignIn(BaseModel):
    username: str
    password: str

class SupervisorSignUp(BaseModel):
    username: str
    password: str
    email: EmailStr
    store_id: str
    contact_number: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = "OPERATOR"

class OrderDetailsResponse(BaseModel):
    order_id: str
    base_price: float
    binding_cost: float
    total_price: float
    pages_count: int
    copies: int
    print_type: str
    paper_type: str
    binding_required: bool

class SupervisorResponse(BaseModel):
    admin_id: str
    username: str
    email: Optional[str]
    store_id: str
    role: str
    contact_number: Optional[str]
    address: Optional[str]
    available: bool

class PrinterStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(Online|Offline|Maintenance)$")
    reason: Optional[str] = None
    description: Optional[str] = None

class QueueOverrideRequest(BaseModel):
    target_printer_id: str
    reason: str

class AlertAcknowledge(BaseModel):
    action_taken: Optional[str] = None

class AlertFix(BaseModel):
    action_taken: str
    notes: Optional[str] = None

class AlertMute(BaseModel):
    duration_minutes: int = 60

class QueryCreate(BaseModel):
    query_type: str = Field(..., pattern="^(printer|user_order|inventory|system|other)$")
    title: str
    description: str
    priority: str = Field(
        default="Info",
        pattern="^(Info|Warning|Critical)$"
    )
    printer_id: Optional[str] = None
    order_id: Optional[str] = None

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    notification_preferences: Optional[dict] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: SupervisorResponse

class SupervisorOrderUpdate(BaseModel):
    status: str
    message: Optional[str] = None

class OrderReassignRequest(BaseModel):
    new_printer_id: str
    reason: str

class OrderIssueReport(BaseModel):
    issue_type: str = Field(..., pattern="^(missing_page|print_error|upload_error|paper_jam|other)$")
    description: str
    severity: str = Field(
        default="Info",
        pattern="^(Info|Warning|Critical)$"
    )

class OrderFilter(BaseModel):
    date: Optional[str] = None
    status: Optional[str] = None
    printer_id: Optional[str] = None
    search: Optional[str] = None
    today_only: bool = False

# ==================== Supervisor Status Enum ====================

class SupervisorStatusEnum(str, enum.Enum):
    PRINTING = "printing"
    BINDING = "binding"
    QC = "qc"
    READY = "ready"
    HANDED_OVER = "handed_over"

class PrinterCreate(BaseModel):
    printer_id: str
    printer_name: str
    printer_model: str
    type: str = Field(default="Laser", pattern="^(Inkjet|Laser|Thermal|Dot Matrix)$")
    supported_sizes: List[str] = Field(default=["A4"])
    color_support: bool = False
    duplex_support: bool = False
    connection_type: str = Field(default="USB", pattern="^(USB|WiFi|Ethernet|Cloud Print)$")
    paper_capacity: int = Field(default=500, gt=0)
    store_id: str = "STORE001"  # Default store for now

class PrinterUpdate(BaseModel):
    status: str = Field(..., pattern="^(Online|Offline|Maintenance|Error)$")
    reason: Optional[str] = None


# ==================== Helper Functions ====================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_admin_id() -> str:
    """Generate unique admin ID"""
    return f"SUP{secrets.token_hex(8).upper()}"

def get_current_supervisor(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> SupervisorData:
    """Extract and validate supervisor JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id: str = payload.get("sub")
        
        if admin_id is None or payload.get("type") != "supervisor":
            raise HTTPException(status_code=401, detail="Invalid token")
        
        supervisor = db.query(SupervisorData).filter(SupervisorData.admin_id == admin_id).first()
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        return supervisor
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def parse_page_string(page_str: str, total_pages: int) -> List[int]:
    """Parse page string like '1-3,5,7-9' into list of page numbers"""
    pages = []
    if not page_str.strip():
        return list(range(1, total_pages + 1))
    
    parts = page_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            start = int(start.strip())
            end = int(end.strip())
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    
    return pages

def calculate_price_breakdown(order: Order, db: Session) -> dict:
    """Calculate detailed price breakdown for an order"""
    settings = order.print_settings or {}
    
    # Get store pricing
    store = db.query(Store).filter(Store.store_id == order.store_id).first()
    store_prices = store.pricing_info if store else {}
    
    default_prices = {
        'bw_per_page': 2,
        'color_per_page': 10,
        'glossy_per_page': 15,
        'thick_per_page': 15,
        'poster_per_page': 20,
        'binding': 10
    }
    
    prices = {**default_prices, **store_prices}
    
    # Parse the new format
    pages_config = settings.get('pages', {})
    print_types = settings.get('print_type', {})
    extras = settings.get('extras', {})
    copies = order.copies
    total_pdf_pages = order.total_pdf_pages or order.pages_count
    
    breakdown = {
        'print_costs': [],
        'binding_cost': 0.0,
        'total_print_cost': 0.0,
        'total_cost': 0.0
    }
    
    # Calculate printing cost for each type
    for print_type, config in pages_config.items():
        page_str = config.get('pages', '')
        exclude = config.get('exclude', False)
        
        # Get pages to print for this type
        if not page_str.strip():
            pages_to_print = list(range(1, total_pdf_pages + 1))
        else:
            pages_to_print = parse_page_string(page_str, total_pdf_pages)
        
        if exclude:
            all_pages = set(range(1, total_pdf_pages + 1))
            specified_pages = set(pages_to_print)
            pages_to_print = list(all_pages - specified_pages)
        
        page_count = len(pages_to_print)
        
        if page_count > 0:
            price_key = f"{print_type}_per_page"
            price_per_page = prices.get(price_key, default_prices.get(price_key, 2))
            cost = page_count * price_per_page * copies
            
            breakdown['print_costs'].append({
                'type': print_type,
                'pages': page_count,
                'price_per_page': price_per_page,
                'copies': copies,
                'subtotal': cost
            })
            
            breakdown['total_print_cost'] += cost
    
    # Add binding cost
    if extras.get('binding'):
        breakdown['binding_cost'] = prices.get('binding', 10)
    
    breakdown['total_cost'] = breakdown['total_print_cost'] + breakdown['binding_cost']
    
    return breakdown

# ==================== Authentication Routes ====================

@router.post("/signin", response_model=TokenResponse)
async def supervisor_signin(
    credentials: SupervisorSignIn,
    db: Session = Depends(get_db)
):
    """
    Supervisor Sign In
    - Authenticates supervisor with username and password
    - Returns access token and supervisor data
    """
    # Find supervisor by username
    supervisor = db.query(SupervisorData).filter(
        SupervisorData.username == credentials.username
    ).first()
    
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, supervisor.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if supervisor is available
    if not supervisor.available:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact administrator."
        )
    
    # Update last login
    supervisor.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    token_data = {
        "sub": supervisor.admin_id,
        "username": supervisor.username,
        "role": supervisor.role,
        "type": "supervisor"
    }
    access_token = create_access_token(token_data)
    
    # Prepare response
    supervisor_response = SupervisorResponse(
        admin_id=supervisor.admin_id,
        username=supervisor.username,
        email=supervisor.email,
        store_id=supervisor.store_id,
        role=supervisor.role,
        contact_number=supervisor.contact_number,
        address=supervisor.address,
        available=supervisor.available
    )
    
    return TokenResponse(
        access_token=access_token,
        user=supervisor_response
    )

@router.post("/signup", response_model=TokenResponse)
async def supervisor_signup(
    data: SupervisorSignUp,
    db: Session = Depends(get_db)
):
    """
    Supervisor Sign Up
    - Creates new supervisor account
    - Requires valid store_id
    - Returns access token and supervisor data
    """
    # Check if username already exists
    existing_supervisor = db.query(SupervisorData).filter(
        SupervisorData.username == data.username
    ).first()
    
    if existing_supervisor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    if data.email:
        existing_email = db.query(SupervisorData).filter(
            SupervisorData.email == data.email
        ).first()
        
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Verify store exists
    store = db.query(Store).filter(Store.store_id == data.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    # Hash password
    hashed_password = hash_password(data.password)
    
    # Generate admin ID
    admin_id = generate_admin_id()
    
    # Create supervisor
    new_supervisor = SupervisorData(
        admin_id=admin_id,
        username=data.username,
        password=hashed_password,
        email=data.email,
        store_id=data.store_id,
        contact_number=data.contact_number,
        address=data.address,
        role=data.role,
        available=True,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    
    db.add(new_supervisor)
    db.commit()
    db.refresh(new_supervisor)
    
    # Create access token
    token_data = {
        "sub": new_supervisor.admin_id,
        "username": new_supervisor.username,
        "role": new_supervisor.role,
        "type": "supervisor"
    }
    access_token = create_access_token(token_data)
    
    # Prepare response
    supervisor_response = SupervisorResponse(
        admin_id=new_supervisor.admin_id,
        username=new_supervisor.username,
        email=new_supervisor.email,
        store_id=new_supervisor.store_id,
        role=new_supervisor.role,
        contact_number=new_supervisor.contact_number,
        address=new_supervisor.address,
        available=new_supervisor.available
    )
    
    return TokenResponse(
        access_token=access_token,
        user=supervisor_response
    )

@router.get("/me", response_model=SupervisorResponse)
async def get_current_supervisor_endpoint(
    current_supervisor: SupervisorData = Depends(get_current_supervisor)
):
    """Get current authenticated supervisor"""
    return SupervisorResponse(
        admin_id=current_supervisor.admin_id,
        username=current_supervisor.username,
        email=current_supervisor.email,
        store_id=current_supervisor.store_id,
        role=current_supervisor.role,
        contact_number=current_supervisor.contact_number,
        address=current_supervisor.address,
        available=current_supervisor.available
    )

# ==================== Supervisor Orders Management ====================

@router.get("/orders")
def get_supervisor_orders(
    date: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    today_only: bool = False,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get orders for supervisor dashboard with filtering"""
    query = db.query(Order).filter(Order.store_id == current_supervisor.store_id)
    
    # Apply filters
    if today_only:
        today = datetime.now().date()
        query = query.filter(Order.order_date >= today)
    
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(Order.order_date >= filter_date)
        except ValueError:
            pass  # Ignore invalid date formats
    
    if status:
        # Convert string to proper enum value
        status_map = {
            'pending': OrderStatusEnum.PENDING,
            'processing': OrderStatusEnum.PROCESSING,
            'completed': OrderStatusEnum.PRINTED,
            'failed': OrderStatusEnum.FAILED,
            'cancelled': OrderStatusEnum.CANCELLED,
            'queued': OrderStatusEnum.QUEUED
        }
        if status.lower() in status_map:
            query = query.filter(Order.status == status_map[status.lower()])
    
    if search:
        search_term = f"%{search}%"
        query = query.join(User).filter(
            (Order.order_id.ilike(search_term)) |
            (User.username.ilike(search_term)) |
            (Order.printer_id.ilike(search_term))
        )
    
    # Get all orders with user info
    orders = query.join(User).add_columns(
        User.username, User.full_name
    ).order_by(
        Order.order_date.desc()
    ).all()
    
    # Separate orders by category
    processing_orders = []
    pending_orders = []
    completed_orders = []
    failed_orders = []
    
    for order, username, full_name in orders:
        order_data = {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "username": username,
            "full_name": full_name,
            "printer_id": order.printer_id,
            "status": order.status.value,
            "pages_count": order.pages_count,
            "copies": order.copies,
            "print_type": order.print_settings.get("print_type", "bw") if order.print_settings else "bw",
            "paper_type": order.print_settings.get("paper_type", "A4") if order.print_settings else "A4",
            "priority": order.print_settings.get("priority", 5) if order.print_settings else 5,
            "order_date": order.order_date.isoformat(),
            "estimated_start": order.estimated_start_time.isoformat() if order.estimated_start_time else None,
            "estimated_end": order.estimated_end_time.isoformat() if order.estimated_end_time else None,
            "actual_start": order.actual_start_time.isoformat() if order.actual_start_time else None,
            "actual_end": order.actual_end_time.isoformat() if order.actual_end_time else None,
            "completion_date": order.completion_date.isoformat() if order.completion_date else None,
            "file_url": order.file_url,
            "price": order.price,
            "binding_cost": order.binding_cost or 0.0,
            "queue_position": order.queue_position,
            "scheduler_score": order.scheduler_score
        }
        
        # Get queue entry for stack index
        queue_entry = db.query(JobQueueEntry).filter(
            JobQueueEntry.order_id == order.order_id
        ).first()
        
        if queue_entry:
            order_data["stack_index"] = queue_entry.queue_position
            order_data["queue_status"] = queue_entry.status.value
        else:
            order_data["stack_index"] = 0
            order_data["queue_status"] = "unknown"
        
        # Categorize orders
        if order.status == OrderStatusEnum.FAILED:
            failed_orders.append(order_data)
        elif order.status == OrderStatusEnum.PRINTED:
            completed_orders.append(order_data)
        elif order.status == OrderStatusEnum.PENDING:
            pending_orders.append(order_data)
        else:  # PROCESSING, QUEUED
            processing_orders.append(order_data)
    
    # Get available printers for reassignment
    printers = db.query(Printer).filter(Printer.status.in_([
        PrinterStatusEnum.ONLINE, 
        PrinterStatusEnum.IDLE
    ])).all()
    
    available_printers = [
        {
            "printer_id": p.printer_id,
            "printer_name": p.printer_name,
            "status": p.status.value,
            "paper_available": p.paper_available,
            "ink_toner_level": p.ink_toner_level,
            "capabilities": {
                "color": p.color_support,
                "duplex": p.duplex_support
            }
        }
        for p in printers
    ]
    
    return {
        "processing_orders": {
            "total": len(processing_orders),
            "orders": processing_orders
        },
        "pending_orders": {
            "total": len(pending_orders),
            "orders": pending_orders
        },
        "completed_orders": {
            "total": len(completed_orders),
            "orders": completed_orders
        },
        "failed_orders": {
            "total": len(failed_orders),
            "orders": failed_orders
        },
        "available_printers": available_printers
    }

@router.post("/orders/{order_id}/update-status")
def update_order_supervisor_status(
    order_id: str,
    request: SupervisorOrderUpdate,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Update supervisor status (binding done, handed over, etc.)"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Validate status transition
    valid_transitions = {
        "printing": ["binding"],
        "binding": ["qc"],
        "qc": ["ready"],
        "ready": ["handed_over"],
        "handed_over": []  # Final state
    }
    
    current_supervisor_status = order.supervisor_status.value if order.supervisor_status else "printing"
    
    if request.status not in valid_transitions.get(current_supervisor_status, []):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status transition from {current_supervisor_status} to {request.status}"
        )
    
    # Update supervisor status
    order.supervisor_status = SupervisorStatusEnum(request.status)
    
    # Create history entry
    history = OrderHistory(
        order_id=order_id,
        status=order.status,
        message=f"Supervisor status updated: {current_supervisor_status} → {request.status}",
        meta={
            "supervisor_action": True,
            "supervisor_id": current_supervisor.admin_id,
            "previous_supervisor_status": current_supervisor_status,
            "new_supervisor_status": request.status,
            "note": request.message
        }
    )
    db.add(history)
    
    # If handed over, update completion if not already done
    if request.status == "handed_over" and order.status != OrderStatusEnum.PRINTED:
        order.status = OrderStatusEnum.PRINTED
        order.completion_date = datetime.now()
    
    db.commit()
    
    # Log supervisor action
    logger.info(f"🔄 Supervisor {current_supervisor.username} updated order {order_id}: {current_supervisor_status} → {request.status}")
    
    return {
        "success": True,
        "order_id": order_id,
        "previous_status": current_supervisor_status,
        "new_status": request.status,
        "message": request.message
    }

@router.post("/orders/{order_id}/report-issue")
def report_order_issue(
    order_id: str,
    request: OrderIssueReport,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Report an issue with an order"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Create alert for the issue
    alert = Alert(
        alert_id=f"ALERT-{uuid.uuid4().hex[:8].upper()}",
        order_id=order_id,
        printer_id=order.printer_id,
        alert_type=AlertTypeEnum.ISSUE,
        severity=AlertSeverityEnum(request.severity),
        title=f"Order Issue: {request.issue_type}",
        description=request.description,
        status="open",
        reported_by=current_supervisor.admin_id,
        metadata={
            "issue_type": request.issue_type,
            "order_details": {
                "user_id": order.user_id,
                "pages": order.pages_count,
                "copies": order.copies,
                "print_type": order.print_settings.get("print_type") if order.print_settings else "bw"
            }
        }
    )
    
    # Update order status if needed
    if request.issue_type in ["paper_jam", "print_error"]:
        order.status = OrderStatusEnum.FAILED
        order.supervisor_status = SupervisorStatusEnum("printing")  # Reset to printing for reprint
    
    # Create history entry
    history = OrderHistory(
        order_id=order_id,
        status=order.status,
        message=f"Issue reported: {request.issue_type} - {request.description}",
        meta={
            "supervisor_action": True,
            "supervisor_id": current_supervisor.admin_id,
            "issue_type": request.issue_type,
            "severity": request.severity,
            "description": request.description
        }
    )
    
    db.add(alert)
    db.add(history)
    db.commit()
    
    logger.warning(f"🚨 Issue reported for order {order_id}: {request.issue_type} by {current_supervisor.username}")
    
    return {
        "success": True,
        "order_id": order_id,
        "alert_id": alert.alert_id,
        "issue_type": request.issue_type,
        "severity": request.severity,
        "description": request.description
    }

@router.post("/orders/{order_id}/reassign")
def reassign_order(
    order_id: str,
    request: OrderReassignRequest,
    background_tasks: BackgroundTasks,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Reassign order to another printer"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if new printer exists and is available
    new_printer = db.query(Printer).filter(Printer.printer_id == request.new_printer_id).first()
    if not new_printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    if new_printer.status not in [PrinterStatusEnum.ONLINE, PrinterStatusEnum.IDLE]:
        raise HTTPException(status_code=400, detail="Printer is not available")
    
    old_printer_id = order.printer_id
    
    # Update order with new printer
    order.printer_id = request.new_printer_id
    order.supervisor_status = SupervisorStatusEnum("printing")  # Reset to printing
    
    # Update queue entry if exists
    queue_entry = db.query(JobQueueEntry).filter(JobQueueEntry.order_id == order_id).first()
    if queue_entry:
        queue_entry.printer_id = request.new_printer_id
        queue_entry.status = JobQueueStatusEnum.QUEUED
        queue_entry.queued_at = datetime.now()
    
    # Create history entry
    history = OrderHistory(
        order_id=order_id,
        status=order.status,
        message=f"Order reassigned from {old_printer_id} to {request.new_printer_id}",
        meta={
            "supervisor_action": True,
            "supervisor_id": current_supervisor.admin_id,
            "old_printer": old_printer_id,
            "new_printer": request.new_printer_id,
            "reason": request.reason
        }
    )
    db.add(history)
    
    db.commit()
    
    # Resubmit to printer simulation in background
    if order.status == OrderStatusEnum.PROCESSING:
        background_tasks.add_task(resubmit_to_printer, order_id, request.new_printer_id, db)
    
    logger.info(f"🔄 Order {order_id} reassigned from {old_printer_id} to {request.new_printer_id} by {current_supervisor.username}")
    
    return {
        "success": True,
        "order_id": order_id,
        "old_printer": old_printer_id,
        "new_printer": request.new_printer_id,
        "reason": request.reason
    }

async def resubmit_to_printer(order_id: str, printer_id: str, db: Session):
    """Resubmit order to new printer simulation"""
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            return
        
        settings = order.print_settings or {}
        
        # Import the send_to_printer_simulation function
        from backend import send_to_printer_simulation
        
        await send_to_printer_simulation(
            printer_id,
            order_id,
            order.pages_count,
            order.copies,
            settings.get("print_type", "bw"),
            settings.get("paper_type", "A4"),
            settings.get("duplex", False),
            order.file_url
        )
        
        logger.info(f"✅ Resubmitted order {order_id} to printer {printer_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to resubmit order {order_id}: {e}")

@router.get("/orders/{order_id}/timeline")
def get_order_timeline(
    order_id: str,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get complete order timeline including supervisor actions"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get all history entries
    history = db.query(OrderHistory).filter(
        OrderHistory.order_id == order_id
    ).order_by(OrderHistory.created_at.asc()).all()
    
    # Build timeline
    timeline = []
    
    # Add order creation
    timeline.append({
        "timestamp": order.order_date.isoformat(),
        "event": "order_created",
        "title": "Order Created",
        "description": f"Order placed by user",
        "status": "pending",
        "icon": "📝"
    })
    
    # Add payment if paid
    if order.payment_status == PaymentStatusEnum.PAID:
        payment_history = next((h for h in history if "payment" in h.message.lower()), None)
        if payment_history:
            timeline.append({
                "timestamp": payment_history.created_at.isoformat(),
                "event": "payment_verified",
                "title": "Payment Verified",
                "description": "Payment completed successfully",
                "status": "completed",
                "icon": "💳"
            })
    
    # Add scheduler assignment
    if order.printer_id:
        assignment_history = next((h for h in history if "assigned to" in h.message.lower()), None)
        if assignment_history:
            timeline.append({
                "timestamp": assignment_history.created_at.isoformat(),
                "event": "printer_assigned",
                "title": "Printer Assigned",
                "description": f"Assigned to {order.printer_id}",
                "status": "completed",
                "icon": "🖨️",
                "metadata": {
                    "printer_id": order.printer_id,
                    "score": order.scheduler_score
                }
            })
    
    # Add printing events
    printing_history = [h for h in history if h.status == OrderStatusEnum.PROCESSING]
    if printing_history:
        timeline.append({
            "timestamp": printing_history[0].created_at.isoformat(),
            "event": "printing_started",
            "title": "Printing Started",
            "description": "Print job initiated",
            "status": "completed",
            "icon": "🔄"
        })
    
    # Add supervisor status changes
    supervisor_events = [h for h in history if h.meta and h.meta.get("supervisor_action")]
    for event in supervisor_events:
        meta = event.meta
        if "supervisor_status" in meta:
            status_map = {
                "binding": {"title": "Binding", "icon": "📚"},
                "qc": {"title": "Quality Check", "icon": "🔍"},
                "ready": {"title": "Ready for Pickup", "icon": "✅"},
                "handed_over": {"title": "Handed Over", "icon": "🎯"}
            }
            status_info = status_map.get(meta["new_supervisor_status"], {"title": "Status Update", "icon": "📋"})
            
            timeline.append({
                "timestamp": event.created_at.isoformat(),
                "event": "supervisor_status_update",
                "title": status_info["title"],
                "description": f"Status updated by supervisor",
                "status": "completed",
                "icon": status_info["icon"],
                "metadata": meta
            })
    
    # Add completion
    if order.status == OrderStatusEnum.PRINTED:
        completion_history = next((h for h in history if h.status == OrderStatusEnum.PRINTED), None)
        if completion_history:
            timeline.append({
                "timestamp": completion_history.created_at.isoformat(),
                "event": "order_completed",
                "title": "Order Completed",
                "description": "Order processing finished",
                "status": "completed",
                "icon": "🎉"
            })
    
    # Sort timeline by timestamp
    timeline.sort(key=lambda x: x["timestamp"])
    
    return {
        "order_id": order_id,
        "current_supervisor_status": order.supervisor_status.value if order.supervisor_status else "printing",
        "timeline": timeline
    }

# ==================== Supervisor Dashboard Routes ====================

@router.get("/dashboard-stats")
def get_supervisor_dashboard_stats(
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get supervisor dashboard statistics"""
    
    today = datetime.now().date()

    try:
        # -------------------------------
        # 1. Orders Today
        # -------------------------------
        orders_today = db.query(Order).filter(
            Order.store_id == current_supervisor.store_id,
            Order.order_date >= today
        ).all()

        total_orders_today = len(orders_today)
        revenue_today = sum(order.price for order in orders_today)
        completed_today = sum(1 for o in orders_today if o.status == OrderStatusEnum.PRINTED)
        active_orders = sum(1 for o in orders_today if o.status in [
            OrderStatusEnum.PENDING, OrderStatusEnum.PROCESSING
        ])

        # -------------------------------
        # 2. Pending Binding (safe check)
        # -------------------------------
        pending_binding = 0
        first_order = db.query(Order).first()

        if first_order is not None and hasattr(first_order, "supervisor_status"):
            pending_binding = db.query(Order).filter(
                Order.store_id == current_supervisor.store_id,
                Order.supervisor_status == SupervisorStatusEnum.BINDING
            ).count()

        # -------------------------------
        # 3. Printer Stats
        # -------------------------------
        printers = db.query(Printer).filter(
            Printer.store_id == current_supervisor.store_id
        ).all()

        total_printers = len(printers)
        up_printers = sum(1 for p in printers if p.status in [
            PrinterStatusEnum.ONLINE, PrinterStatusEnum.IDLE
        ])
        down_printers = total_printers - up_printers

        # -------------------------------
        # 4. Alerts
        # -------------------------------
        sla_breaches = db.query(Alert).filter(
            Alert.store_id == current_supervisor.store_id,
            Alert.alert_type == AlertTypeEnum.ORDER_DELAY,
            Alert.status == AlertStatusEnum.UNREAD
        ).count()

        low_inventory = db.query(Alert).filter(
            Alert.store_id == current_supervisor.store_id,
            Alert.alert_type.in_([AlertTypeEnum.LOW_PAPER, AlertTypeEnum.LOW_INK]),
            Alert.status == AlertStatusEnum.UNREAD
        ).count()

        # -------------------------------
        # 5. Printer Load Summary
        # -------------------------------
        printer_load = []
        for printer in printers:
            pages_today = printer.total_pages_printed or 0
            load_pct = min(100, (pages_today / 1000) * 100)

            printer_load.append({
                "printer_id": printer.printer_id,
                "printer_name": printer.printer_name,
                "pages_printed_today": pages_today,
                "load_percentage": load_pct
            })

        # -------------------------------
        # Final Response
        # -------------------------------
        return {
            "orders": {
                "total_today": total_orders_today,
                "revenue_today": revenue_today,
                "active_orders": active_orders,
                "completed_today": completed_today,
                "pending_binding": pending_binding
            },
            "printers": {
                "total": total_printers,
                "up_count": up_printers,
                "down_count": down_printers
            },
            "alerts": {
                "sla_breaches": sla_breaches,
                "low_inventory": low_inventory
            },
            "printer_load": printer_load
        }

    except Exception as e:
        logger.error(f"[Dashboard Stats Error] {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load dashboard statistics."
        )
    
@router.get("/recent-alerts")
def get_recent_alerts(
    limit: int = 5,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get recent alerts for supervisor dashboard"""
    try:
        alerts = db.query(Alert).filter(
            Alert.status == AlertStatusEnum.UNREAD
        ).order_by(Alert.created_at.desc()).limit(limit).all()
        
        return {
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "title": f"{alert.alert_type.value.replace('_', ' ').title()}",
                    "description": alert.alert_message,
                    "severity": alert.severity.value,
                    "created_at": alert.created_at.isoformat()
                }
                for alert in alerts
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching recent alerts: {e}")
        # Return empty array if there's an error
        return {"alerts": []}

@router.get("/printers")
def get_supervisor_printers(
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get all printers for supervisor's store"""
    printers = db.query(Printer).filter(
        Printer.store_id == current_supervisor.store_id
    ).all()
    
    return {
        "printers": [
            {
                "printer_id": p.printer_id,
                "printer_name": p.printer_name,
                "printer_model": p.printer_model,
                "type": p.type.value,
                "status": p.status.value,
                "paper_available": p.paper_available,
                "ink_toner_level": p.ink_toner_level,
                "color_support": p.color_support,
                "duplex_support": p.duplex_support,
                "connection_type": p.connection_type.value,
                "pages_printed": p.pages_printed,
                "current_job_id": p.current_job_id,
                "queue_length": p.queue_length,
                "temperature": p.temperature,
                "humidity": p.humidity,
                "total_pages_printed": p.total_pages_printed,
                "last_maintenance": p.last_maintenance.isoformat() if p.last_maintenance else None
            }
            for p in printers
        ]
    }

@router.post("/printers")
def create_printer(
    printer_data: PrinterCreate,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Create a new printer"""
    # Check if printer already exists
    existing_printer = db.query(Printer).filter(
        Printer.printer_id == printer_data.printer_id
    ).first()
    
    if existing_printer:
        raise HTTPException(status_code=400, detail="Printer ID already exists")
    
    # Create new printer
    printer = Printer(
        printer_id=printer_data.printer_id,
        store_id=current_supervisor.store_id,
        printer_name=printer_data.printer_name,
        printer_model=printer_data.printer_model,
        type=PrinterType(printer_data.type),
        supported_sizes=printer_data.supported_sizes,
        color_support=printer_data.color_support,
        duplex_support=printer_data.duplex_support,
        connection_type=PrinterConnectionType(printer_data.connection_type),
        paper_capacity=printer_data.paper_capacity,
        paper_available=printer_data.paper_capacity,
        ink_toner_level={"black": 100, "cyan": 100, "magenta": 100, "yellow": 100},
        status=PrinterStatusEnum.ONLINE,
        pages_printed=0,
        total_pages_printed=0,
        queue_length=0,
        job_queue=[],
        temperature=22.0,
        humidity=45.0,
        last_maintenance=datetime.utcnow()
    )
    
    db.add(printer)
    db.commit()
    db.refresh(printer)
    
    logger.info(f"✅ Printer created: {printer_data.printer_id} by {current_supervisor.username}")
    
    return {
        "success": True,
        "message": "Printer created successfully",
        "printer_id": printer.printer_id
    }

@router.post("/printers/{printer_id}/status")
def update_printer_status(
    printer_id: str,
    status_data: PrinterStatusUpdate,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Update printer status with alerts, activity logs, and downtime tracking."""
    
    printer = db.query(Printer).filter(
        Printer.printer_id == printer_id,
        Printer.store_id == current_supervisor.store_id
    ).first()

    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    old_status = printer.status.value
    new_status = status_data.status

    # -----------------------------
    # 1. Update Printer Status
    # -----------------------------
    printer.status = PrinterStatusEnum(new_status)

    # -----------------------------
    # 2. Create Activity Log
    # -----------------------------
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="printer_status_change",
        entity_type="printer",
        entity_id="PRINTER - " + printer_id,
        old_value={"status": old_status},
        new_value={"status": new_status, "reason": status_data.reason}
    )
    db.add(activity_log)

    # -----------------------------
    # 3. Handle Downtime Tracking
    # -----------------------------
    if new_status == "Offline" and status_data.reason:
        # Create new down event
        down_entry = PrinterDownHistory(
            printer_id=printer_id,
            supervisor_id=current_supervisor.admin_id,
            reason=PrinterDownReasonEnum(status_data.reason),
            description=status_data.description,
            down_time=datetime.utcnow()
        )
        db.add(down_entry)

    elif new_status == "Online" and old_status == "Offline":
        # Close last downtime record
        down_record = db.query(PrinterDownHistory).filter(
            PrinterDownHistory.printer_id == printer_id,
            PrinterDownHistory.up_time.is_(None)
        ).order_by(PrinterDownHistory.down_time.desc()).first()

        if down_record:
            down_record.up_time = datetime.utcnow()
            down_record.duration_minutes = int(
                (down_record.up_time - down_record.down_time).total_seconds() / 60
            )

    # -----------------------------
    # 4. Generate Alerts (if needed)
    # -----------------------------
    if new_status in ["Offline", "Error"] and status_data.reason:
        alert_type = AlertTypeEnum.OFFLINE if new_status == "Offline" else AlertTypeEnum.OTHER

        alert = Alert(
            store_id=current_supervisor.store_id,
            printer_id=printer_id,
            alert_type=alert_type,
            alert_message=f"Printer {new_status.lower()}: {status_data.reason}",
            severity=AlertSeverityEnum.WARNING,
            status=AlertStatusEnum.UNREAD,
            supervisor_id=current_supervisor.admin_id
        )
        db.add(alert)

    # -----------------------------
    # 5. Commit Changes
    # -----------------------------
    db.commit()

    logger.info(
        f"🖨️ Printer {printer_id} status changed from {old_status} to {new_status} "
        f"by {current_supervisor.username}"
    )

    return {
        "success": True,
        "printer_id": printer_id,
        "old_status": old_status,
        "new_status": new_status,
        "reason": status_data.reason
    }


@router.delete("/printers/{printer_id}")
def delete_printer(
    printer_id: str,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Delete a printer"""
    printer = db.query(Printer).filter(
        Printer.printer_id == printer_id,
        Printer.store_id == current_supervisor.store_id
    ).first()
    
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    # Check if printer has active jobs
    active_jobs = db.query(JobQueueEntry).filter(
        JobQueueEntry.printer_id == printer_id,
        JobQueueEntry.status.in_([JobQueueStatusEnum.QUEUED, JobQueueStatusEnum.PROCESSING])
    ).count()
    
    if active_jobs > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete printer with {active_jobs} active jobs"
        )
    
    db.delete(printer)
    db.commit()
    
    logger.info(f"🗑️ Printer deleted: {printer_id} by {current_supervisor.username}")
    
    return {
        "success": True,
        "message": "Printer deleted successfully"
    }

# ==================== Printer Management Routes ====================

@router.get("/printers/detailed")
def get_detailed_printers(
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get detailed printer information for printer management page"""
    printers = db.query(Printer).filter(
        Printer.store_id == current_supervisor.store_id
    ).all()
    
    # Get today's date for pages printed today calculation
    today = datetime.now().date()
    
    detailed_printers = []
    for printer in printers:
        # Calculate pages printed today (simplified - using total pages for now)
        pages_today = printer.total_pages_printed
        
        # Get current queue length
        queue_length = db.query(JobQueueEntry).filter(
            JobQueueEntry.printer_id == printer.printer_id,
            JobQueueEntry.status.in_([JobQueueStatusEnum.QUEUED, JobQueueStatusEnum.PROCESSING])
        ).count()
        
        # Get last jam timestamp from alerts
        last_jam = db.query(Alert).filter(
            Alert.printer_id == printer.printer_id,
            Alert.alert_type == AlertTypeEnum.JAM
        ).order_by(Alert.created_at.desc()).first()
        
        detailed_printers.append({
            "printer_id": printer.printer_id,
            "printer_name": printer.printer_name,
            "printer_model": printer.printer_model,
            "type": printer.type.value,
            "status": printer.status.value,
            "paper_available": printer.paper_available,
            "paper_capacity": printer.paper_capacity,
            "ink_toner_level": printer.ink_toner_level,
            "color_support": printer.color_support,
            "duplex_support": printer.duplex_support,
            "connection_type": printer.connection_type.value,
            "pages_printed_today": pages_today,
            "total_pages_printed": printer.total_pages_printed,
            "queue_length": queue_length,
            "current_job_id": printer.current_job_id,
            "temperature": printer.temperature,
            "humidity": printer.humidity,
            "last_maintenance": printer.last_maintenance.isoformat() if printer.last_maintenance else None,
            "last_jam_timestamp": last_jam.created_at.isoformat() if last_jam else None,
            "capabilities": {
                "supported_sizes": printer.supported_sizes,
                "color": printer.color_support,
                "duplex": printer.duplex_support
            }
        })
    
    return {"printers": detailed_printers}

@router.post("/printers/{printer_id}/queue-override")
def override_printer_queue(
    printer_id: str,
    override_data: QueueOverrideRequest,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Move all pending jobs from one printer to another"""
    # Check if source printer exists
    source_printer = db.query(Printer).filter(
        Printer.printer_id == printer_id,
        Printer.store_id == current_supervisor.store_id
    ).first()
    
    if not source_printer:
        raise HTTPException(status_code=404, detail="Source printer not found")
    
    # Check if target printer exists and is available
    target_printer = db.query(Printer).filter(
        Printer.printer_id == override_data.target_printer_id,
        Printer.store_id == current_supervisor.store_id
    ).first()
    
    if not target_printer:
        raise HTTPException(status_code=404, detail="Target printer not found")
    
    if target_printer.status not in [PrinterStatusEnum.ONLINE, PrinterStatusEnum.IDLE]:
        raise HTTPException(status_code=400, detail="Target printer is not available")
    
    # Get all queued jobs from source printer
    queued_jobs = db.query(JobQueueEntry).filter(
        JobQueueEntry.printer_id == printer_id,
        JobQueueEntry.status == JobQueueStatusEnum.QUEUED
    ).all()
    
    moved_jobs = []
    for job in queued_jobs:
        old_printer_id = job.printer_id
        job.printer_id = override_data.target_printer_id
        
        # Update associated order
        order = db.query(Order).filter(Order.order_id == job.order_id).first()
        if order:
            order.printer_id = override_data.target_printer_id
        
        moved_jobs.append(job.order_id)
        
        # Log the move
        activity_log = SupervisorActivityLog(
            supervisor_id=current_supervisor.admin_id,
            action="queue_override",
            entity_type="order",
            entity_id=job.order_id,
            old_value={"printer_id": old_printer_id},
            new_value={"printer_id": override_data.target_printer_id, "reason": override_data.reason}
        )
        db.add(activity_log)
    
    db.commit()
    
    logger.info(f"🔄 Queue override: {len(moved_jobs)} jobs moved from {printer_id} to {override_data.target_printer_id} by {current_supervisor.username}")
    
    return {
        "success": True,
        "moved_jobs_count": len(moved_jobs),
        "moved_jobs": moved_jobs,
        "source_printer": printer_id,
        "target_printer": override_data.target_printer_id,
        "reason": override_data.reason
    }

# ==================== Activity Logs Routes ====================

@router.get("/activity-logs")
def get_activity_logs(
    entity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get supervisor activity logs"""
    query = db.query(SupervisorActivityLog).filter(
        SupervisorActivityLog.supervisor_id == current_supervisor.admin_id
    )
    
    if entity_type:
        query = query.filter(SupervisorActivityLog.entity_type == entity_type)
    
    if start_date:
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(SupervisorActivityLog.timestamp >= start_datetime)
    
    if end_date:
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(SupervisorActivityLog.timestamp <= end_datetime)
    
    logs = query.order_by(SupervisorActivityLog.timestamp.desc()).limit(limit).all()
    
    return {
        "logs": [
            {
                "log_id": log.log_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address
            }
            for log in logs
        ]
    }

# ==================== Query Management Routes ====================

@router.get("/queries")
def get_supervisor_queries(
    status: Optional[str] = None,
    query_type: Optional[str] = None,
    limit: int = 50,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get supervisor queries/issues"""
    query = db.query(SupervisorQuery).filter(
        SupervisorQuery.supervisor_id == current_supervisor.admin_id
    )
    
    if status:
        query = query.filter(SupervisorQuery.status == QueryStatusEnum(status))
    if query_type:
        query = query.filter(SupervisorQuery.query_type == QueryTypeEnum(query_type))
    
    queries = query.order_by(SupervisorQuery.created_at.desc()).limit(limit).all()
    
    return {
        "queries": [
            {
                "query_id": q.query_id,
                "query_type": q.query_type.value,
                "title": q.title,
                "description": q.description,
                "status": q.status.value,
                "priority": q.priority.value,
                "printer_id": q.printer_id,
                "order_id": q.order_id,
                "file_url": q.file_url,
                "file_name": q.file_name,
                "created_at": q.created_at.isoformat(),
                "updated_at": q.updated_at.isoformat(),
                "resolved_at": q.resolved_at.isoformat() if q.resolved_at else None
            }
            for q in queries
        ]
    }

@router.post("/queries")
def create_supervisor_query(
    query_data: QueryCreate,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Create a new supervisor query/issue"""
    query_id = f"QUERY-{uuid.uuid4().hex[:8].upper()}"
    
    query = SupervisorQuery(
        query_id=query_id,
        supervisor_id=current_supervisor.admin_id,
        query_type=QueryTypeEnum(query_data.query_type),
        title=query_data.title,
        description=query_data.description,
        priority=AlertSeverityEnum(query_data.priority),
        printer_id=query_data.printer_id,
        order_id=query_data.order_id,
        status="IN_PROGRESS"
    )
    
    db.add(query)
    
    # Log the action
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="query_created",
        entity_type="query",
        entity_id="QUERY - " + query_id,
        new_value={
            "type": query_data.query_type,
            "title": query_data.title,
            "priority": query_data.priority
        }
    )
    db.add(activity_log)
    
    db.commit()
    
    logger.info(f"❓ Query created: {query_id} by {current_supervisor.username}")
    
    return {
        "success": True,
        "query_id": query_id,
        "message": "Query created successfully"
    }

@router.post("/queries/{query_id}/update-status")
def update_query_status(
    query_id: str,
    status: str = Query(..., pattern="^(open|in_progress|resolved)$"),
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Update query status"""
    query = db.query(SupervisorQuery).filter(
        SupervisorQuery.query_id == query_id,
        SupervisorQuery.supervisor_id == current_supervisor.admin_id
    ).first()
    
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    old_status = query.status.value
    query.status = QueryStatusEnum(status)
    query.updated_at = datetime.utcnow()
    
    if status == "resolved":
        query.resolved_at = datetime.utcnow()
    
    # Log the action
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="query_status_updated",
        entity_type="query",
        entity_id="QUERY - " + query_id,
        old_value={"status": old_status},
        new_value={"status": status}
    )
    db.add(activity_log)
    
    db.commit()
    
    return {
        "success": True,
        "query_id": query_id,
        "old_status": old_status,
        "new_status": status
    }

# ==================== Profile Management Routes ====================

@router.get("/profile")
def get_supervisor_profile(
    current_supervisor: SupervisorData = Depends(get_current_supervisor)
):
    """Get supervisor profile"""
    return {
        "admin_id": current_supervisor.admin_id,
        "username": current_supervisor.username,
        "email": current_supervisor.email,
        "store_id": current_supervisor.store_id,
        "role": current_supervisor.role,
        "contact_number": current_supervisor.contact_number,
        "address": current_supervisor.address,
        "notification_preferences": current_supervisor.notification_preferences or {
            "sms": True,
            "email": True,
            "system_alerts": True
        },
        "created_at": current_supervisor.created_at.isoformat(),
        "last_login": current_supervisor.last_login.isoformat() if current_supervisor.last_login else None
    }

@router.put("/profile")
def update_supervisor_profile(
    profile_data: ProfileUpdate,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Update supervisor profile"""
    old_values = {
        "contact_number": current_supervisor.contact_number,
        "address": current_supervisor.address,
        "notification_preferences": current_supervisor.notification_preferences
    }
    
    if profile_data.contact_number is not None:
        current_supervisor.contact_number = profile_data.contact_number
    if profile_data.address is not None:
        current_supervisor.address = profile_data.address
    if profile_data.notification_preferences is not None:
        current_supervisor.notification_preferences = profile_data.notification_preferences
    
    # Log the action
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="profile_updated",
        entity_type="profile",
        entity_id=current_supervisor.admin_id,
        old_value=old_values,
        new_value={
            "contact_number": current_supervisor.contact_number,
            "address": current_supervisor.address,
            "notification_preferences": current_supervisor.notification_preferences
        }
    )
    db.add(activity_log)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Profile updated successfully"
    }

@router.post("/change-password")
def change_supervisor_password(
    password_data: PasswordChange,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Change supervisor password"""
    # Verify current password
    if not verify_password(password_data.current_password, current_supervisor.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Hash new password
    new_hashed_password = hash_password(password_data.new_password)
    current_supervisor.password = new_hashed_password
    
    # Log the action
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="password_changed",
        entity_type="profile",
        entity_id=current_supervisor.admin_id
    )
    db.add(activity_log)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }

@router.post("/printers/{printer_id}/pause")
async def pause_printer(
    printer_id: str,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Pause printer via supervisor"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://localhost:8001/printers/{printer_id}/pause"
            )
            response.raise_for_status()
            result = response.json()
        
        # Log activity
        activity_log = SupervisorActivityLog(
            supervisor_id=current_supervisor.admin_id,
            action="printer_paused",
            entity_type="printer",
            entity_id="PRINTER - " + printer_id,
            new_value={"status": "paused"}
        )
        db.add(activity_log)
        db.commit()
        
        logger.info(f"⏸️ Printer {printer_id} paused by {current_supervisor.username}")
        
        return result
    except Exception as e:
        logger.error(f"Failed to pause printer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/printers/{printer_id}/resume")
async def resume_printer(
    printer_id: str,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Resume paused printer"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://localhost:8001/printers/{printer_id}/resume"
            )
            response.raise_for_status()
            result = response.json()
        
        # Log activity
        activity_log = SupervisorActivityLog(
            supervisor_id=current_supervisor.admin_id,
            action="printer_resumed",
            entity_type="printer",
            entity_id="PRINTER - " + printer_id,
            new_value={"status": "resumed"}
        )
        db.add(activity_log)
        db.commit()
        
        logger.info(f"▶️ Printer {printer_id} resumed by {current_supervisor.username}")
        
        return result
    except Exception as e:
        logger.error(f"Failed to resume printer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/printers/{printer_id}/cancel-job")
async def cancel_printer_job(
    printer_id: str,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Cancel current printing job"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://localhost:8001/printers/{printer_id}/cancel-job"
            )
            response.raise_for_status()
            result = response.json()
        
        cancelled_job_id = result.get("cancelled_job_id")
        
        # Update order in database if exists
        if cancelled_job_id:
            order = db.query(Order).filter(Order.order_id == cancelled_job_id).first()
            if order:
                order.status = OrderStatusEnum.CANCELLED
                
                history = OrderHistory(
                    order_id=cancelled_job_id,
                    status=OrderStatusEnum.CANCELLED,
                    message=f"Job cancelled by supervisor {current_supervisor.username}"
                )
                db.add(history)
        
        # Log activity
        activity_log = SupervisorActivityLog(
            supervisor_id=current_supervisor.admin_id,
            action="job_cancelled",
            entity_type="printer",
            entity_id="PRINTER - " + printer_id,
            new_value={"cancelled_job_id": cancelled_job_id}
        )
        db.add(activity_log)
        db.commit()
        
        logger.warning(f"🛑 Job cancelled on {printer_id} by {current_supervisor.username}")
        
        return result
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/printers/{printer_id}/test-print")
async def test_print_printer(
    printer_id: str,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Run test print on printer"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://localhost:8001/printers/{printer_id}/test-print"
            )
            response.raise_for_status()
            result = response.json()
        
        # Log activity
        activity_log = SupervisorActivityLog(
            supervisor_id=current_supervisor.admin_id,
            action="test_print",
            entity_type="printer",
            entity_id="PRINTER - " + printer_id,
            new_value={"test_job_id": result.get("test_job_id")}
        )
        db.add(activity_log)
        db.commit()
        
        logger.info(f"🧪 Test print on {printer_id} by {current_supervisor.username}")
        
        return result
    except Exception as e:
        logger.error(f"Failed to start test print: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/notifications")
def get_notifications(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    printer_id: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get notifications with advanced filtering and grouping"""
    
    # Base query - exclude muted and already handled alerts
    query = db.query(Alert).filter(
        Alert.store_id == current_supervisor.store_id,
        Alert.muted == False
    )
    
    # Exclude acknowledged info/warning alerts
    query = query.filter(
        ~((Alert.severity.in_([AlertSeverityEnum.INFO, AlertSeverityEnum.WARNING])) & 
          (Alert.acknowledged == True))
    )
    
    # Exclude fixed critical alerts
    query = query.filter(
        ~((Alert.severity == AlertSeverityEnum.CRITICAL) & (Alert.fixed == True))
    )
    
    # Apply filters
    if severity:
        query = query.filter(Alert.severity == AlertSeverityEnum(severity))
    
    if category:
        query = query.filter(Alert.alert_type == AlertTypeEnum(category))
    
    if printer_id:
        query = query.filter(Alert.printer_id == printer_id)
    
    if unread_only:
        query = query.filter(Alert.status == AlertStatusEnum.UNREAD)
    
    # Get total count before pagination
    total_count = query.count()
    
    # Get alerts with pagination
    alerts = query.order_by(
        Alert.severity.desc(),  # Critical first
        Alert.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    # Get summary statistics
    summary = {
        "critical": db.query(Alert).filter(
            Alert.store_id == current_supervisor.store_id,
            Alert.severity == AlertSeverityEnum.CRITICAL,
            Alert.fixed == False,
            Alert.muted == False
        ).count(),
        "warning": db.query(Alert).filter(
            Alert.store_id == current_supervisor.store_id,
            Alert.severity == AlertSeverityEnum.WARNING,
            Alert.acknowledged == False,
            Alert.muted == False
        ).count(),
        "info": db.query(Alert).filter(
            Alert.store_id == current_supervisor.store_id,
            Alert.severity == AlertSeverityEnum.INFO,
            Alert.acknowledged == False,
            Alert.muted == False
        ).count()
    }
    
    # Group alerts by printer - MANUALLY build response to avoid circular refs
    grouped_alerts = {}
    for alert in alerts:
        printer_key = alert.printer_id or "system"
        
        if printer_key not in grouped_alerts:
            printer = None
            if alert.printer_id:
                printer = db.query(Printer).filter(
                    Printer.printer_id == alert.printer_id
                ).first()
            
            grouped_alerts[printer_key] = {
                "printer_id": alert.printer_id,
                "printer_name": printer.printer_name if printer else "System",
                "alerts": []
            }
        
        # Manually build alert dict to avoid relationship loading
        grouped_alerts[printer_key]["alerts"].append({
            "alert_id": alert.alert_id,
            "alert_type": alert.alert_type.value,
            "alert_message": alert.alert_message,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "printer_id": alert.printer_id,
            "order_id": alert.order_id,
            "created_at": alert.created_at.isoformat(),
            "acknowledged": alert.acknowledged,
            "fixed": alert.fixed,
            "metadata": alert.alert_metadata or {}  # Use alert_metadata not metadata
        })
    
    return {
        "summary": summary,
        "total_count": total_count,
        "grouped_alerts": list(grouped_alerts.values()),
        "has_more": (offset + limit) < total_count
    }

@router.post("/notifications/{alert_id}/acknowledge")
def acknowledge_notification(
    alert_id: int,
    data: AlertAcknowledge,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Acknowledge a notification (for Info/Warning alerts)"""
    
    alert = db.query(Alert).filter(
        Alert.alert_id == alert_id,
        Alert.store_id == current_supervisor.store_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Only Info and Warning can be acknowledged
    if alert.severity == AlertSeverityEnum.CRITICAL:
        raise HTTPException(
            status_code=400, 
            detail="Critical alerts must be fixed, not acknowledged"
        )
    
    alert.acknowledged = True
    alert.acknowledged_by = current_supervisor.admin_id
    alert.acknowledged_at = datetime.utcnow()
    alert.status = AlertStatusEnum.ACKNOWLEDGED
    
    if data.action_taken:
        alert.action_taken = data.action_taken
    
    # Log activity
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="alert_acknowledged",
        entity_type="alert",
        entity_id=str(alert_id),
        new_value={"action_taken": data.action_taken}
    )
    db.add(activity_log)
    
    db.commit()
    
    logger.info(f"✅ Alert {alert_id} acknowledged by {current_supervisor.username}")
    
    return {
        "success": True,
        "alert_id": alert_id,
        "acknowledged": True,
        "action_taken": data.action_taken
    }

@router.post("/notifications/{alert_id}/fix")
def fix_critical_notification(
    alert_id: int,
    data: AlertFix,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Fix a critical notification"""
    
    alert = db.query(Alert).filter(
        Alert.alert_id == alert_id,
        Alert.store_id == current_supervisor.store_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Mark as fixed
    alert.fixed = True
    alert.fixed_by = current_supervisor.admin_id
    alert.fixed_at = datetime.utcnow()
    alert.status = AlertStatusEnum.RESOLVED
    alert.resolved_at = datetime.utcnow()
    alert.action_taken = data.action_taken
    
    # Update metadata with fix notes
    if alert.alert_metadata is None:
        alert.alert_metadata = {}
    alert.alert_metadata["fix_notes"] = data.notes
    
    # Log activity
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="alert_fixed",
        entity_type="alert",
        entity_id=str(alert_id),
        new_value={
            "action_taken": data.action_taken,
            "notes": data.notes
        }
    )
    db.add(activity_log)
    
    db.commit()
    
    logger.info(f"🔧 Critical alert {alert_id} fixed by {current_supervisor.username}")
    
    return {
        "success": True,
        "alert_id": alert_id,
        "fixed": True,
        "action_taken": data.action_taken
    }

@router.post("/notifications/{alert_id}/mute")
def mute_notification(
    alert_id: int,
    data: AlertMute,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Mute a notification for specified duration"""
    
    alert = db.query(Alert).filter(
        Alert.alert_id == alert_id,
        Alert.store_id == current_supervisor.store_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.muted = True
    alert.muted_until = datetime.utcnow() + timedelta(minutes=data.duration_minutes)
    
    # Log activity
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="alert_muted",
        entity_type="alert",
        entity_id=str(alert_id),
        new_value={"muted_until": alert.muted_until.isoformat()}
    )
    db.add(activity_log)
    
    db.commit()
    
    logger.info(f"🔇 Alert {alert_id} muted by {current_supervisor.username} for {data.duration_minutes} minutes")
    
    return {
        "success": True,
        "alert_id": alert_id,
        "muted": True,
        "muted_until": alert.muted_until.isoformat()
    }

@router.post("/notifications/{alert_id}/unmute")
def unmute_notification(
    alert_id: int,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Unmute a notification"""
    
    alert = db.query(Alert).filter(
        Alert.alert_id == alert_id,
        Alert.store_id == current_supervisor.store_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.muted = False
    alert.muted_until = None
    
    db.commit()
    
    return {
        "success": True,
        "alert_id": alert_id,
        "muted": False
    }

@router.get("/notifications/summary")
def get_notifications_summary(
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get quick notification summary for dashboard"""
    
    critical = db.query(Alert).filter(
        Alert.store_id == current_supervisor.store_id,
        Alert.severity == AlertSeverityEnum.CRITICAL,
        Alert.fixed == False,
        Alert.muted == False
    ).count()
    
    warning = db.query(Alert).filter(
        Alert.store_id == current_supervisor.store_id,
        Alert.severity == AlertSeverityEnum.WARNING,
        Alert.acknowledged == False,
        Alert.muted == False
    ).count()
    
    info = db.query(Alert).filter(
        Alert.store_id == current_supervisor.store_id,
        Alert.severity == AlertSeverityEnum.INFO,
        Alert.acknowledged == False,
        Alert.muted == False
    ).count()
    
    total_printers = db.query(Printer).filter(
        Printer.store_id == current_supervisor.store_id
    ).count()
    
    healthy_printers = db.query(Printer).filter(
        Printer.store_id == current_supervisor.store_id,
        Printer.status.in_([PrinterStatusEnum.ONLINE, PrinterStatusEnum.IDLE])
    ).count()
    
    return {
        "critical_issues": critical,
        "warnings": warning,
        "info_alerts": info,
        "total_alerts": critical + warning + info,
        "printers_ok": healthy_printers == total_printers,
        "healthy_printers": healthy_printers,
        "total_printers": total_printers
    }

# Add this Pydantic model
class MarkDeliveredRequest(BaseModel):
    notes: Optional[str] = None

class MarkBindingCompletedRequest(BaseModel):
    notes: Optional[str] = None

# Add these new routes

@router.post("/orders/{order_id}/mark-delivered")
def mark_order_delivered(
    order_id: str,
    data: MarkDeliveredRequest,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Mark order as delivered/handed over"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order is completed by printer backend
    if order.status != OrderStatusEnum.READY_FOR_DELIVERY:
        raise HTTPException(
            status_code=400, 
            detail="Order must be completed by printer before delivery"
        )
    
    # Update order to mark as delivered (we'll use a custom field or keep completed status)
    # Add a delivered flag in print_settings
    if not order.delivery_details:
        order.delivery_details = {}
    
    details = dict(order.delivery_details or {})
    details.update({
        "delivered": True,
        "delivered_at": datetime.utcnow().isoformat(),
        "delivered_by": current_supervisor.admin_id
    })
    order.delivery_details = details
    order.status = OrderStatusEnum.DELIVERED
    
    # Create history entry
    history = OrderHistory(
        order_id=order_id,
        status=OrderStatusEnum.PRINTED,
        message=f"Order marked as delivered by supervisor",
        meta={
            "supervisor_action": True,
            "supervisor_id": current_supervisor.admin_id,
            "action": "delivered",
            "notes": data.notes
        }
    )
    db.add(history)
    
    # Log activity
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="order_delivered",
        entity_type="order",
        entity_id=order_id,
        new_value={"status": "delivered", "notes": data.notes}
    )
    db.add(activity_log)
    
    db.commit()
    
    logger.info(f"📦 Order {order_id} marked as delivered by {current_supervisor.username}")
    
    return {
        "success": True,
        "order_id": order_id,
        "status": "delivered",
        "message": "Order marked as delivered successfully"
    }

@router.post("/orders/{order_id}/mark-binding-completed")
def mark_binding_completed(
    order_id: str,
    data: MarkBindingCompletedRequest,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Mark binding as completed and set order ready for delivery"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order is completed by printer
    if order.status != OrderStatusEnum.PRINTED:
        raise HTTPException(
            status_code=400,
            detail="Order must be completed by printer before binding can be marked"
        )
    
    # Update print_settings to mark binding as done and ready for delivery
    if not order.print_settings:
        order.print_settings = {}
    
    order.binding_done = True
    order.print_settings["binding_completed_at"] = datetime.utcnow().isoformat()
    order.ready_for_delivery = True
    order.status = OrderStatusEnum.READY_FOR_DELIVERY
    
    # Create history entry
    history = OrderHistory(
        order_id=order_id,
        status=order.status,
        message=f"Binding completed - Ready for delivery",
        meta={
            "supervisor_action": True,
            "supervisor_id": current_supervisor.admin_id,
            "action": "binding_completed",
            "notes": data.notes
        }
    )
    db.add(history)
    
    # Log activity
    activity_log = SupervisorActivityLog(
        supervisor_id=current_supervisor.admin_id,
        action="binding_completed",
        entity_type="order",
        entity_id=order_id,
        new_value={"binding_done": True, "ready_for_delivery": True, "notes": data.notes}
    )
    db.add(activity_log)
    
    db.commit()
    
    logger.info(f"📚 Binding completed for order {order_id} - Ready for delivery")
    
    return {
        "success": True,
        "order_id": order_id,
        "binding_done": True,
        "ready_for_delivery": True,
        "message": "Binding completed - Order ready for delivery"
    }

@router.get("/orders/active-jobs")
def get_active_print_jobs(
    search: Optional[str] = None,
    date: Optional[str] = None,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get only non-delivered orders: 
       - status = PROCESSING OR COMPLETED
       - delivery_details.delivered = false OR delivery_details is null
    """

    # Base query — filter at SQL level
    query = db.query(Order).filter(
        Order.store_id == current_supervisor.store_id,
        Order.status.in_([OrderStatusEnum.PROCESSING, OrderStatusEnum.PRINTED, OrderStatusEnum.READY_FOR_DELIVERY]),
        # delivery_details JSON: either null OR delivered = false
        or_(
            Order.delivery_details.is_(None),
            Order.delivery_details["delivered"].as_boolean() == False
        )
    )

    # Date filter
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(Order.order_date >= filter_date)
        except ValueError:
            pass

    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.join(User).filter(
            (Order.order_id.ilike(search_term)) |
            (User.username.ilike(search_term)) |
            (Order.printer_id.ilike(search_term))
        )
    else:
        query = query.join(User)

    # fetch orders + user data
    orders = query.add_columns(
        User.username, User.full_name
    ).order_by(
        Order.order_date.desc()
    ).all()

    active_jobs = []

    for order, username, full_name in orders:
        delivery_details = order.delivery_details or {}

        start_time = order.actual_start_time or order.order_date
        elapsed_min = int((datetime.utcnow() - start_time).total_seconds() / 60)

        base_price = order.price - (order.binding_cost or 0)

        active_jobs.append({
            "order_id": order.order_id,
            "user_id": order.user_id,
            "username": username,
            "full_name": full_name,
            "printer_id": order.printer_id,
            "binding_required": order.binding_required,
            "binding_done": order.binding_done,
            "ready_for_delivery": order.ready_for_delivery,
            "pages_count": order.pages_count,
            "copies": order.copies,
            "time_elapsed_minutes": elapsed_min,
            "status": order.status.value,
            "order_date": order.order_date.isoformat(),
            "actual_start_time": order.actual_start_time.isoformat() if order.actual_start_time else None,
            "estimated_end_time": order.estimated_end_time.isoformat() if order.estimated_end_time else None,
            "print_type": (order.print_settings or {}).get("print_type", {}),
            "paper_type": (order.print_settings or {}).get("paper_type", {}),
            "is_delivered": delivery_details.get("delivered", False),
            "base_price": base_price,
            "binding_cost": order.binding_cost or 0,
            "total_price": order.price
        })

    return {
        "active_jobs": active_jobs,
        "total": len(active_jobs)
    }

@router.get("/orders/history")
def get_orders_history(
    search: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get completed, pending, and failed orders (excluding processing)"""
    query = db.query(Order).filter(
        Order.store_id == current_supervisor.store_id,
        Order.status.in_([OrderStatusEnum.PRINTED, OrderStatusEnum.PENDING, OrderStatusEnum.FAILED, OrderStatusEnum.CANCELLED])
    )
    
    # Apply filters
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(Order.order_date >= filter_date)
        except ValueError:
            pass
    
    if status:
        status_map = {
            'pending': OrderStatusEnum.PENDING,
            'completed': OrderStatusEnum.PRINTED,
            'failed': OrderStatusEnum.FAILED,
            'cancelled': OrderStatusEnum.CANCELLED
        }
        if status.lower() in status_map:
            query = query.filter(Order.status == status_map[status.lower()])
    
    if search:
        search_term = f"%{search}%"
        query = query.join(User).filter(
            (Order.order_id.ilike(search_term)) |
            (User.username.ilike(search_term)) |
            (Order.printer_id.ilike(search_term))
        )
    
    orders = query.join(User).add_columns(
        User.username, User.full_name
    ).order_by(
        Order.order_date.desc()
    ).all()
    
    # Separate by status
    pending_orders = []
    completed_orders = []
    failed_orders = []
    
    for order, username, full_name in orders:
        settings = order.print_settings or {}
        
        order_data = {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "username": username,
            "full_name": full_name,
            "printer_id": order.printer_id,
            "binding_required": order.binding_required,
            "pages_count": order.pages_count,
            "copies": order.copies,
            "status": order.status.value,
            "order_date": order.order_date.isoformat(),
            "completion_date": order.completion_date.isoformat() if order.completion_date else None,
            "print_type": settings.get("print_type", "bw"),
            "paper_type": settings.get("paper_type", "A4"),
            "price": order.price,
            "is_delivered": settings.get("delivered", False)
        }
        
        if order.status == OrderStatusEnum.PENDING:
            pending_orders.append(order_data)
        elif order.status == OrderStatusEnum.PRINTED:
            completed_orders.append(order_data)
        elif order.status in [OrderStatusEnum.FAILED, OrderStatusEnum.CANCELLED]:
            failed_orders.append(order_data)
    
    return {
        "pending_orders": {
            "total": len(pending_orders),
            "orders": pending_orders
        },
        "completed_orders": {
            "total": len(completed_orders),
            "orders": completed_orders
        },
        "failed_orders": {
            "total": len(failed_orders),
            "orders": failed_orders
        }
    }

@router.get("/orders/{order_id}/details")
def get_order_details(
    order_id: str,
    current_supervisor: SupervisorData = Depends(get_current_supervisor),
    db: Session = Depends(get_db)
):
    """Get detailed price breakdown for an order"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    breakdown = calculate_price_breakdown(order, db)
    settings = order.print_settings or {}
    
    return {
        "order_id": order.order_id,
        "pages_count": order.pages_count,
        "total_pdf_pages": order.total_pdf_pages or order.pages_count,
        "copies": order.copies,
        "print_breakdown": breakdown['print_costs'],
        "total_print_cost": breakdown['total_print_cost'],
        "binding_cost": breakdown['binding_cost'],
        "total_cost": breakdown['total_cost'],
        "binding_required": order.binding_required,
        "duplex": settings.get('duplex', False),
        "collate": settings.get('collate', True)
    }
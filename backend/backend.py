"""
Production-Grade Integrated Backend
Seamlessly connects Realistic Printer Simulation + Production Scheduler + Database
Features: SSE, Webhooks, Zero Polling, Full Hardware Integration
"""
from fastapi import FastAPI, HTTPException, Depends, status, Header, BackgroundTasks, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, validator
from storage import upload_pdf_to_gcs
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import httpx
import uuid
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
import os
import asyncio
import json
from collections import defaultdict
from PyPDF2 import PdfReader
import io

# Import from your modules
from database import get_db, init_db
from models import (
    Store, SupervisorData, Printer, Order, Alert, User,
    OrderStatusEnum, PaymentStatusEnum, PrinterStatusEnum,
    AlertTypeEnum, AlertSeverityEnum, StoreStatusEnum,
    PaymentTransaction, OrderHistory, JobQueueEntry, JobQueueStatusEnum
)
from auth import (
    hash_password, verify_password, create_access_token,
    decode_access_token, generate_user_id
)

# Import production scheduler
import sys
sys.path.append('.')
from smart_scheduler import (
    PrinterScheduler, Config, Validator, 
    InsufficientResourceError, NoCapablePrinterError,
    QueueOverflowError, ValidationError as SchedulerValidationError,
    ResourceConflictError
)

from payment import create_razorpay_order, verify_payment_signature, get_payment_details
from dotenv import load_dotenv

load_dotenv()
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")

# ==================== Logging Setup ====================

logger = logging.getLogger("integrated_backend")
logger.setLevel(logging.INFO)

os.makedirs("logs", exist_ok=True)

file_handler = RotatingFileHandler("logs/integrated_backend.log", maxBytes=10*1024*1024, backupCount=5)
console_handler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ==================== SSE Event Management ====================

class SSEManager:
    """Manages Server-Sent Events for real-time updates"""
    
    def __init__(self):
        self.connections: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def connect(self, user_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        async with self.lock:
            self.connections[user_id].append(queue)
        logger.info(f"✅ SSE connected: {user_id}")
        return queue
    
    async def disconnect(self, user_id: str, queue: asyncio.Queue):
        async with self.lock:
            if user_id in self.connections:
                if queue in self.connections[user_id]:
                    self.connections[user_id].remove(queue)
                if not self.connections[user_id]:
                    del self.connections[user_id]
        logger.info(f"❌ SSE disconnected: {user_id}")
    
    async def send_update(self, user_id: str, event_type: str, data: dict):
        async with self.lock:
            if user_id not in self.connections:
                return
            queues = self.connections[user_id].copy()
        
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        for queue in queues:
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"SSE send failed for {user_id}: {e}")

sse_manager = SSEManager()

# ==================== Request/Response Models ====================

class PrintJobRequest(BaseModel):
    """Request to create a print job"""
    pages: int = Field(gt=0, le=10000)
    copies: int = Field(default=1, gt=0, le=100)
    print_type: str = Field(..., pattern="^(bw|color|thick|glossy|postersize)$")
    paper_type: str = Field(default="A4", pattern="^(A4|A3|Letter|Legal|Thick|Glossy|Poster)$")
    priority: int = Field(default=5, ge=1, le=10)
    duplex: bool = Field(default=False)
    collate: bool = Field(default=True)
    store_id: str = Field(default="STORE001")
    file_url: Optional[str] = None

class CreatePaymentRequest(BaseModel):
    """Unified request for single or bulk orders"""
    orders: List[PrintJobRequest] = Field(..., min_items=1, max_items=50)

class SignupRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None

class SigninRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class RazorpayVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class WebhookPrinterUpdate(BaseModel):
    """Webhook from printer simulation"""
    job_id: str
    status: str  # printing, completed, failed
    progress_percent: int
    printer_id: str
    message: Optional[str] = None
    timestamp: Optional[str] = None

class StoreCreate(BaseModel):
    store_id: str
    store_name: str
    address: str
    contact_number: Optional[str]
    email: Optional[str]
    business_hours: Optional[dict]
    pricing_info: Optional[dict]
    payment_modes: Optional[list]

# ==================== Global State ====================

scheduler: Optional[PrinterScheduler] = None
PRINTER_API_URL = "http://localhost:8001"

# ==================== Lifespan Management ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all systems on startup"""
    global scheduler
    
    logger.info("🚀 Starting Integrated Backend System...")
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        raise
    
    # Initialize scheduler with printer simulation data
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRINTER_API_URL}/printers", timeout=10.0)
            response.raise_for_status()
            printer_data = response.json()
        
        # Convert printer simulation format to scheduler format
        printers_dict = {}
        for p in printer_data:
            printers_dict[p["printer_id"]] = {
                "name": p["name"],
                "model": p["model"],
                "manufacturer": p["manufacturer"],
                "supported": p["supported"],
                "paper_count": p["paper_count"],
                "ink": p["ink"],
                "speed": p["speed"],
                "status": p["status"],
                "current_job": p["current_job"],
                "queue": [],  # Initialize empty, will be managed
                "location": p["location"],
                "ip_address": p["ip_address"],
                "serial_number": p["serial_number"],
                "firmware_version": p["firmware_version"],
                "total_pages_printed": p["total_pages_printed"],
                "last_maintenance": p["last_maintenance"],
                "temperature": p["temperature"],
                "humidity": p["humidity"],
                "capabilities": p["capabilities"]
            }
        
        scheduler = PrinterScheduler(printers_dict)
        logger.info(f"✅ Production Scheduler initialized with {len(printers_dict)} printers")
        
        # Log printer details
        for pid, info in printers_dict.items():
            logger.info(f"  📠 {pid}: {info['name']} - {info['supported']}")
    
    except Exception as e:
        logger.error(f"❌ Scheduler initialization failed: {e}")
        raise
    
    yield
    
    logger.info("🛑 Shutting down Integrated Backend...")

# ==================== FastAPI App ====================

app = FastAPI(
    title="Integrated Print Management System",
    version="3.0",
    description="Production-grade system with realistic printer simulation + advanced scheduler",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Helper Functions ====================

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """Extract and validate JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

# Update the calculate_price function in backend.py
def calculate_price(pages: int, copies: int, print_type: str, store_id: str, db: Session) -> float:
    """Calculate job price based on store pricing"""
    try:
        # Use a fresh query to avoid transaction issues
        store = db.query(Store).filter(Store.store_id == store_id).first()
        
        if store and store.pricing_info:
            pricing = store.pricing_info
            price_map = {
                'bw': pricing.get('bw_per_page', 2.0),
                'color': pricing.get('color_per_page', 10.0),
                'thick': pricing.get('thick_per_page', 15.0),
                'glossy': pricing.get('glossy_per_page', 15.0),
                'postersize': pricing.get('poster_per_page', 50.0)
            }
        else:
            # Fallback pricing
            price_map = {
                'bw': 2.0,
                'color': 10.0,
                'thick': 15.0,
                'glossy': 15.0,
                'postersize': 50.0
            }
        
        total_pages = pages * copies
        price_per_page = price_map.get(print_type, 5.0)
        
        return round(total_pages * price_per_page, 2)
        
    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        # Emergency fallback pricing
        price_map = {
            'bw': 2.0,
            'color': 10.0,
            'thick': 15.0,
            'glossy': 15.0,
            'postersize': 50.0
        }
        total_pages = pages * copies
        price_per_page = price_map.get(print_type, 5.0)
        return round(total_pages * price_per_page, 2)

async def send_to_printer_simulation(
    printer_id: str, 
    job_id: str, 
    pages: int, 
    copies: int, 
    print_type: str,
    paper_type: str,
    duplex: bool,
    file_url: Optional[str] = None
):
    """Send job to realistic printer simulation API"""
    webhook_url = f"http://localhost:8000/webhook/printer-update"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PRINTER_API_URL}/printers/{printer_id}/print",
                json={
                    "job_id": job_id,
                    "print_type": print_type,
                    "paper_type": paper_type,
                    "pages": pages,
                    "copies": copies,
                    "priority": 5,
                    "file_url": file_url,
                    "webhook_url": webhook_url,
                    "duplex": duplex,
                    "collate": True
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to send job {job_id} to printer {printer_id}: {e}")
        raise

def sync_printer_status_from_simulation(db: Session):
    """Sync printer status from simulation to database"""
    try:
        import requests
        response = requests.get(f"{PRINTER_API_URL}/printers", timeout=5.0)
        response.raise_for_status()
        sim_printers = response.json()
        
        for sp in sim_printers:
            db_printer = db.query(Printer).filter(Printer.printer_id == sp["printer_id"]).first()
            
            if not db_printer:
                # Create printer in DB if doesn't exist
                db_printer = Printer(
                    printer_id=sp["printer_id"],
                    store_id="STORE001",  # Default store
                    printer_name=sp["name"],
                    printer_model=sp["model"],
                    color_support=sp["capabilities"]["color"],
                    duplex_support=sp["capabilities"]["duplex"],
                    status=PrinterStatusEnum.ONLINE if sp["status"] == "idle" else PrinterStatusEnum.BUSY,
                    paper_available=sum(sp["paper_count"].values()),
                    ink_toner_level=sp["ink"],
                    temperature=sp["temperature"],
                    humidity=sp["humidity"],
                    total_pages_printed=sp["total_pages_printed"],
                    last_maintenance=sp["last_maintenance"]
                )
                db.add(db_printer)
            else:
                # Update existing printer
                status_map = {
                    "idle": PrinterStatusEnum.IDLE,
                    "busy": PrinterStatusEnum.BUSY,
                    "warming_up": PrinterStatusEnum.BUSY,
                    "offline": PrinterStatusEnum.OFFLINE,
                    "error": PrinterStatusEnum.ERROR,
                    "paper_jam": PrinterStatusEnum.ERROR,
                    "maintenance": PrinterStatusEnum.MAINTENANCE
                }
                db_printer.status = status_map.get(sp["status"].lower(), PrinterStatusEnum.ONLINE)
                db_printer.paper_available = sum(sp["paper_count"].values())
                db_printer.ink_toner_level = sp["ink"]
                db_printer.temperature = sp["temperature"]
                db_printer.humidity = sp["humidity"]
                db_printer.total_pages_printed = sp["total_pages_printed"]
        
        db.commit()
        logger.info(f"✅ Synced {len(sim_printers)} printers from simulation")
        
    except Exception as e:
        logger.error(f"Failed to sync printer status: {e}")

# ==================== API Endpoints ====================

@app.get("/system/db-health")
def check_db_health(db: Session = Depends(get_db)):
    """Check database health and connectivity"""
    try:
        # Test basic query
        stores_count = db.query(Store).count()
        users_count = db.query(User).count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "stores_count": stores_count,
            "users_count": users_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
@app.get("/")
def root():
    return {
        "service": "Integrated Print Management System",
        "version": "3.0",
        "components": {
            "scheduler": "Production-Grade Weight-Based Scheduler",
            "printer_sim": "Realistic Hardware Simulation",
            "database": "PostgreSQL with Full Persistence",
            "realtime": "SSE + Webhooks (Zero Polling)"
        },
        "status": {
            "scheduler_active": scheduler is not None,
            "printer_api": PRINTER_API_URL
        }
    }

# ==================== Authentication ====================

@app.post("/auth/signup", response_model=AuthResponse)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """User registration"""
    existing = db.query(User).filter(
        (User.email == request.email) | (User.username == request.username)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already exists")
    
    user = User(
        user_id=generate_user_id(),
        email=request.email,
        username=request.username,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        phone=request.phone,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token(data={"sub": user.user_id})
    
    logger.info(f"✅ User registered: {user.username}")
    
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user={
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "balance": user.balance
        }
    )

@app.post("/auth/signin", response_model=AuthResponse)
def signin(request: SigninRequest, db: Session = Depends(get_db)):
    """User login"""
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    token = create_access_token(data={"sub": user.user_id})
    
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user={
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "balance": user.balance
        }
    )

@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "balance": current_user.balance,
        "created_at": current_user.created_at
    }

# ==================== SSE Real-Time Updates ====================

@app.get("/orders/stream")
async def stream_order_updates(current_user: User = Depends(get_current_user)):
    """SSE endpoint for real-time order updates - NO POLLING NEEDED"""
    queue = await sse_manager.connect(current_user.user_id)
    
    async def event_generator():
        try:
            yield f"data: {json.dumps({'event': 'connected', 'user_id': current_user.user_id})}\n\n"
            
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'event': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            await sse_manager.disconnect(current_user.user_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# ==================== Webhook from Printer Simulation ====================

@app.post("/webhook/printer-update")
async def printer_webhook(payload: WebhookPrinterUpdate, db: Session = Depends(get_db)):
    """
    Receives updates from printer simulation
    This is the ONLY way status changes - no polling!
    """
    logger.info(f"📨 Webhook: {payload.job_id} -> {payload.status} ({payload.progress_percent}%)")
    
    order = db.query(Order).filter(Order.order_id == payload.job_id).first()
    if not order:
        logger.warning(f"Webhook for unknown order: {payload.job_id}")
        return {"status": "ignored"}
    
    # Update order based on printer status
    if payload.status == "printing":
        if order.status != OrderStatusEnum.PROCESSING:
            order.status = OrderStatusEnum.PROCESSING
            order.actual_start_time = datetime.now()
            
            history = OrderHistory(
                order_id=order.order_id,
                status=OrderStatusEnum.PROCESSING,
                message=f"Printing started on {payload.printer_id}"
            )
            db.add(history)
            
            # Update queue entry
            queue_entry = db.query(JobQueueEntry).filter(
                JobQueueEntry.order_id == order.order_id
            ).first()
            if queue_entry:
                queue_entry.status = JobQueueStatusEnum.PROCESSING
                queue_entry.started_at = datetime.now()
    
    elif payload.status == "completed":
        order.status = OrderStatusEnum.COMPLETED
        order.actual_end_time = datetime.now()
        order.completion_date = datetime.now()
        
        history = OrderHistory(
            order_id=order.order_id,
            status=OrderStatusEnum.COMPLETED,
            message="Print job completed successfully"
        )
        db.add(history)
        
        # Update queue entry
        queue_entry = db.query(JobQueueEntry).filter(
            JobQueueEntry.order_id == order.order_id
        ).first()
        if queue_entry:
            queue_entry.status = JobQueueStatusEnum.COMPLETED
            queue_entry.completed_at = datetime.now()
        
        logger.info(f"✅ Order {order.order_id} completed")
    
    elif payload.status == "failed":
        order.status = OrderStatusEnum.FAILED
        
        history = OrderHistory(
            order_id=order.order_id,
            status=OrderStatusEnum.FAILED,
            message=payload.message or "Print job failed"
        )
        db.add(history)
        
        # Update queue entry
        queue_entry = db.query(JobQueueEntry).filter(
            JobQueueEntry.order_id == order.order_id
        ).first()
        if queue_entry:
            queue_entry.status = JobQueueStatusEnum.FAILED
        
        logger.error(f"❌ Order {order.order_id} failed: {payload.message}")
    
    db.commit()
    db.refresh(order)
    
    # Push real-time update to user via SSE
    await sse_manager.send_update(
        order.user_id,
        "order_update",
        {
            "order_id": order.order_id,
            "status": order.status.value,
            "progress": payload.progress_percent,
            "printer_id": payload.printer_id,
            "message": payload.message
        }
    )
    
    return {"status": "success"}

# ==================== Order Management ====================

@app.post("/orders/create-payment")
async def create_payment_order(
    request: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Step 1: Create order(s) and payment - handles both single and bulk"""
    order_count = len(request.orders)
    logger.info(f"Creating payment for {order_count} order(s) for {current_user.username}")
    
    # Sync printer status first
    sync_printer_status_from_simulation(db)
    
    created_orders = []
    total_price = 0
    bulk_id = f"BULK-{uuid.uuid4().hex[:8].upper()}" if order_count > 1 else None
    
    try:
        # Create all orders
        for idx, order_request in enumerate(request.orders, 1):
            order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            price = calculate_price(
                order_request.pages, 
                order_request.copies, 
                order_request.print_type, 
                order_request.store_id, 
                db
            )
            total_price += price
            
            order = Order(
                order_id=order_id,
                user_id=current_user.user_id,
                store_id=order_request.store_id,
                pages_count=order_request.pages,
                copies=order_request.copies,
                print_settings={
                    "print_type": order_request.print_type,
                    "paper_type": order_request.paper_type,
                    "priority": order_request.priority,
                    "duplex": order_request.duplex,
                    "collate": order_request.collate
                },
                price=price,
                status=OrderStatusEnum.PENDING,
                payment_status=PaymentStatusEnum.UNPAID,
                file_url=order_request.file_url,
                bulk_order_id=bulk_id  # None for single orders
            )
            
            db.add(order)
            created_orders.append(order)
            
            message = f"Order created ({order_request.print_type}, {order_request.pages}p × {order_request.copies}c)"
            if order_count > 1:
                message = f"Bulk order {idx}/{order_count}: {message}"
            
            history = OrderHistory(
                order_id=order_id,
                status=OrderStatusEnum.PENDING,
                message=message
            )
            db.add(history)
        
        db.commit()
        
        # Refresh all orders
        for order in created_orders:
            db.refresh(order)
        
        # Create single Razorpay order for total amount
        reference_id = bulk_id if bulk_id else created_orders[0].order_id
        razorpay_order = create_razorpay_order(total_price, reference_id)
        
        # Update all orders with the same razorpay_order_id
        for order in created_orders:
            order.razorpay_order_id = razorpay_order["razorpay_order_id"]
        
        # Create single transaction
        transaction = PaymentTransaction(
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            order_id=created_orders[0].order_id,
            razorpay_order_id=razorpay_order["razorpay_order_id"],
            amount=total_price,
            currency="INR",
            status="created",
            metadata={
                "order_ids": [o.order_id for o in created_orders],
                "order_count": order_count,
                "is_bulk": order_count > 1
            } if order_count > 1 else None
        )
        db.add(transaction)
        db.commit()
        
        logger.info(f"✅ Payment order created: {order_count} order(s), total: ₹{total_price}")
        
        return {
            "bulk_order_id": bulk_id,
            "order_ids": [o.order_id for o in created_orders],
            "razorpay_order_id": razorpay_order["razorpay_order_id"],
            "amount": total_price,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID,
            "order_count": order_count,
            "order_details": [
                {
                    "order_id": o.order_id,
                    "print_type": o.print_settings["print_type"],
                    "paper_type": o.print_settings["paper_type"],
                    "pages": o.pages_count,
                    "copies": o.copies,
                    "duplex": o.print_settings["duplex"],
                    "price": o.price
                }
                for o in created_orders
            ]
        }
        
    except Exception as e:
        # Rollback all created orders
        for order in created_orders:
            db.delete(order)
        db.commit()
        logger.error(f"❌ Order creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orders/verify-payment")
async def verify_payment(
    payload: RazorpayVerifyRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Step 2: Verify payment and schedule print job(s) - handles both single and bulk"""
    
    # Find all orders with this razorpay_order_id
    orders = db.query(Order).filter(
        Order.razorpay_order_id == payload.razorpay_order_id
    ).all()
    
    if not orders:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify user owns all orders
    if any(order.user_id != current_user.user_id for order in orders):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Verify payment signature
    is_valid = verify_payment_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    
    # Update all orders with payment info
    for order in orders:
        order.razorpay_payment_id = payload.razorpay_payment_id
        order.razorpay_signature = payload.razorpay_signature
        order.payment_status = PaymentStatusEnum.PAID
        
        history = OrderHistory(
            order_id=order.order_id,
            status=OrderStatusEnum.PENDING,
            message="Payment verified, scheduling print job"
        )
        db.add(history)
    
    # Update transaction
    transaction = db.query(PaymentTransaction).filter(
        PaymentTransaction.razorpay_order_id == payload.razorpay_order_id
    ).first()
    if transaction:
        transaction.razorpay_payment_id = payload.razorpay_payment_id
        transaction.status = "success"
    
    db.commit()
    
    # Schedule all print jobs in background
    for order in orders:
        background_tasks.add_task(process_print_job, order.order_id, db)
    
    logger.info(f"✅ Payment verified for {len(orders)} order(s), scheduling...")
    
    return {
        "success": True,
        "order_ids": [o.order_id for o in orders],
        "order_count": len(orders),
        "message": f"Payment successful, {len(orders)} job(s) being scheduled"
    }

async def process_print_job(order_id: str, db: Session):
    """
    Background task: Use production scheduler to assign printer
    Then send to printer simulation API
    """
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            return
        
        logger.info(f"🔄 Processing print job: {order_id}")
        
        # Build order dict for scheduler
        settings = order.print_settings or {}
        print_type = settings.get("print_type", "bw")
        paper_type = settings.get("paper_type", "A4")
        
        scheduler_order = {
            print_type: {
                "paper_count": {
                    paper_type: order.pages_count * order.copies
                }
            }
        }
        
        # Use production scheduler
        try:
            result = scheduler.schedule_order(
                scheduler_order,
                order_id=order_id,
                priority=settings.get("priority", 5)
            )
            
            assigned_printer = result['assignments'][0]
            score = result['scores'][0]
            
            logger.info(f"✅ Scheduler assigned {order_id} to {assigned_printer} (score: {score:.3f})")
            
            # Update order with assignment
            order.printer_id = assigned_printer
            order.scheduler_score = score
            order.scheduler_metadata = {
                "suborders": result['suborders'],
                "assignments": result['assignments'],
                "scores": result['scores']
            }
            order.status = OrderStatusEnum.PROCESSING
            
            # Create queue entry
            queue_entry = JobQueueEntry(
                printer_id=assigned_printer,
                order_id=order_id,
                queue_position=0,
                priority=settings.get("priority", 5),
                status=JobQueueStatusEnum.QUEUED,
                suborder_types=[print_type],
                scheduler_score=score
            )
            db.add(queue_entry)
            
            history = OrderHistory(
                order_id=order_id,
                status=OrderStatusEnum.PROCESSING,
                message=f"Assigned to {assigned_printer} by scheduler",
                meta={"score": score, "suborders": result['suborders']}
            )
            db.add(history)
            db.commit()
            
            # Notify user via SSE
            await sse_manager.send_update(
                order.user_id,
                "order_scheduled",
                {
                    "order_id": order_id,
                    "printer_id": assigned_printer,
                    "score": score
                }
            )
            
            # Send to printer simulation
            await send_to_printer_simulation(
                assigned_printer,
                order_id,
                order.pages_count,
                order.copies,
                print_type,
                paper_type,
                settings.get("duplex", False),
                order.file_url
            )
            
            logger.info(f"✅ Job {order_id} sent to printer simulation")
            
        except InsufficientResourceError as e:
            order.status = OrderStatusEnum.FAILED
            history = OrderHistory(
                order_id=order_id,
                status=OrderStatusEnum.FAILED,
                message=f"Insufficient resources: {str(e)}"
            )
            db.add(history)
            db.commit()
            
            await sse_manager.send_update(
                order.user_id,
                "order_failed",
                {"order_id": order_id, "reason": "insufficient_resources", "details": str(e)}
            )
            
            logger.error(f"❌ {order_id} failed: Insufficient resources")
            
        except NoCapablePrinterError as e:
            order.status = OrderStatusEnum.FAILED
            history = OrderHistory(
                order_id=order_id,
                status=OrderStatusEnum.FAILED,
                message=f"No capable printer: {str(e)}"
            )
            db.add(history)
            db.commit()
            
            await sse_manager.send_update(
                order.user_id,
                "order_failed",
                {"order_id": order_id, "reason": "no_printer", "details": str(e)}
            )
            
            logger.error(f"❌ {order_id} failed: No capable printer")
            
        except QueueOverflowError as e:
            order.status = OrderStatusEnum.FAILED
            history = OrderHistory(
                order_id=order_id,
                status=OrderStatusEnum.FAILED,
                message=f"Queue overflow: {str(e)}"
            )
            db.add(history)
            db.commit()
            
            await sse_manager.send_update(
                order.user_id,
                "order_failed",
                {"order_id": order_id, "reason": "queue_full", "details": str(e)}
            )
            
            logger.error(f"❌ {order_id} failed: Queue overflow")
            
        except Exception as e:
            order.status = OrderStatusEnum.FAILED
            history = OrderHistory(
                order_id=order_id,
                status=OrderStatusEnum.FAILED,
                message=f"Scheduler error: {str(e)}"
            )
            db.add(history)
            db.commit()
            
            await sse_manager.send_update(
                order.user_id,
                "order_failed",
                {"order_id": order_id, "reason": "scheduler_error", "details": str(e)}
            )
            
            logger.error(f"❌ {order_id} failed: {e}")
            
    except Exception as e:
        logger.error(f"Background task error for {order_id}: {e}")

# ==================== Order Queries ====================

@app.get("/orders/my-orders")
def get_my_orders(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get user's orders with optional status filter"""
    query = db.query(Order).filter(Order.user_id == current_user.user_id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.order_date.desc()).limit(limit).all()
    
    return {
        "total": len(orders),
        "orders": [
            {
                "order_id": o.order_id,
                "status": o.status.value,
                "printer_id": o.printer_id,
                "pages_count": o.pages_count,
                "copies": o.copies,
                "price": o.price,
                "payment_status": o.payment_status.value,
                "order_date": o.order_date.isoformat(),
                "completion_date": o.completion_date.isoformat() if o.completion_date else None,
                "print_settings": o.print_settings,
                "estimated_start": o.estimated_start_time.isoformat() if o.estimated_start_time else None,
                "estimated_end": o.estimated_end_time.isoformat() if o.estimated_end_time else None,
                "queue_position": o.queue_position,
                "scheduler_score": o.scheduler_score
            }
            for o in orders
        ]
    }

@app.get("/orders/{order_id}")
def get_order_details(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed order information"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get queue entry if exists
    queue_entry = db.query(JobQueueEntry).filter(
        JobQueueEntry.order_id == order_id
    ).first()
    
    return {
        "order": {
            "order_id": order.order_id,
            "status": order.status.value,
            "printer_id": order.printer_id,
            "pages_count": order.pages_count,
            "copies": order.copies,
            "price": order.price,
            "payment_status": order.payment_status.value,
            "print_settings": order.print_settings,
            "order_date": order.order_date.isoformat(),
            "completion_date": order.completion_date.isoformat() if order.completion_date else None,
            "file_url": order.file_url,
            "estimated_start": order.estimated_start_time.isoformat() if order.estimated_start_time else None,
            "estimated_end": order.estimated_end_time.isoformat() if order.estimated_end_time else None,
            "actual_start": order.actual_start_time.isoformat() if order.actual_start_time else None,
            "actual_end": order.actual_end_time.isoformat() if order.actual_end_time else None,
            "scheduler_score": order.scheduler_score,
            "scheduler_metadata": order.scheduler_metadata
        },
        "queue_info": {
            "position": queue_entry.queue_position if queue_entry else None,
            "priority": queue_entry.priority if queue_entry else None,
            "status": queue_entry.status.value if queue_entry else None,
            "queued_at": queue_entry.queued_at.isoformat() if queue_entry else None,
            "started_at": queue_entry.started_at.isoformat() if queue_entry and queue_entry.started_at else None
        } if queue_entry else None
    }

@app.get("/orders/{order_id}/history")
def get_order_history(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete order history timeline"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    history = db.query(OrderHistory).filter(
        OrderHistory.order_id == order_id
    ).order_by(OrderHistory.created_at.asc()).all()
    
    return {
        "order_id": order_id,
        "total_events": len(history),
        "history": [
            {
                "status": h.status.value,
                "message": h.message,
                "meta": h.meta,
                "created_at": h.created_at.isoformat()
            }
            for h in history
        ]
    }

# ==================== Printer Management ====================

@app.get("/printers")
async def list_printers(db: Session = Depends(get_db)):
    """List all printers with live status from simulation"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRINTER_API_URL}/printers", timeout=10.0)
            response.raise_for_status()
            sim_printers = response.json()
        
        # Sync to database
        sync_printer_status_from_simulation(db)
        
        # Get scheduler status
        system_status = scheduler.get_system_status() if scheduler else {}
        
        return {
            "total": len(sim_printers),
            "printers": sim_printers,
            "scheduler_info": system_status
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch printers: {e}")
        raise HTTPException(status_code=503, detail="Printer service unavailable")

@app.get("/printers/{printer_id}")
async def get_printer_details(printer_id: str):
    """Get detailed printer information from simulation"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PRINTER_API_URL}/printers/{printer_id}",
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Printer not found")
        raise HTTPException(status_code=503, detail="Printer service error")

@app.get("/printers/{printer_id}/status")
def get_printer_status(printer_id: str, db: Session = Depends(get_db)):
    """Get printer status from scheduler"""
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    try:
        status = scheduler.get_printer_status(printer_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/printers/{printer_id}/refill")
async def refill_printer(printer_id: str):
    """Trigger printer refill in simulation"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PRINTER_API_URL}/printers/{printer_id}/refill",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/printers/{printer_id}/maintenance")
async def perform_maintenance(printer_id: str):
    """Trigger maintenance in simulation"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PRINTER_API_URL}/printers/{printer_id}/maintenance",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Store Management ====================

@app.post("/stores", status_code=status.HTTP_201_CREATED)
def create_store(store_data: StoreCreate, db: Session = Depends(get_db)):
    """Create new store"""
    existing = db.query(Store).filter(Store.store_id == store_data.store_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Store already exists")
    
    store = Store(
        store_id=store_data.store_id,
        store_name=store_data.store_name,
        address=store_data.address,
        contact_number=store_data.contact_number,
        email=store_data.email,
        business_hours=store_data.business_hours or {"open": "09:00", "close": "21:00"},
        pricing_info=store_data.pricing_info or {
            "bw_per_page": 2.0,
            "color_per_page": 10.0,
            "thick_per_page": 15.0,
            "glossy_per_page": 15.0,
            "poster_per_page": 50.0
        },
        payment_modes=store_data.payment_modes or ["cash", "upi", "card"]
    )
    
    db.add(store)
    db.commit()
    
    return {"message": "Store created", "store_id": store.store_id}

@app.get("/stores")
def list_stores(db: Session = Depends(get_db)):
    """List all stores"""
    stores = db.query(Store).all()
    return {"total": len(stores), "stores": stores}

# ==================== Statistics & Monitoring ====================

@app.get("/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """Comprehensive system statistics"""
    try:
        # Printer simulation stats
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRINTER_API_URL}/stats", timeout=5.0)
            printer_stats = response.json()
    except:
        printer_stats = {}
    
    # Database stats
    total_orders = db.query(Order).count()
    completed = db.query(Order).filter(Order.status == OrderStatusEnum.COMPLETED).count()
    pending = db.query(Order).filter(Order.status == OrderStatusEnum.PENDING).count()
    processing = db.query(Order).filter(Order.status == OrderStatusEnum.PROCESSING).count()
    failed = db.query(Order).filter(Order.status == OrderStatusEnum.FAILED).count()
    
    # Queue stats
    total_queued = db.query(JobQueueEntry).filter(
        JobQueueEntry.status == JobQueueStatusEnum.QUEUED
    ).count()
    
    # Scheduler stats
    scheduler_status = scheduler.get_system_status() if scheduler else {}
    
    return {
        "timestamp": datetime.now().isoformat(),
        "printers": printer_stats.get("printers", {}),
        "orders": {
            "total": total_orders,
            "completed": completed,
            "pending": pending,
            "processing": processing,
            "failed": failed,
            "success_rate": f"{(completed/total_orders*100):.1f}%" if total_orders > 0 else "N/A"
        },
        "queue": {
            "total_queued": total_queued
        },
        "scheduler": scheduler_status,
        "printer_jobs": printer_stats.get("jobs", {})
    }

@app.get("/stats/scheduler")
def get_scheduler_stats():
    """Get detailed scheduler statistics"""
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    return scheduler.get_system_status()

@app.get("/alerts")
def get_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get system alerts"""
    query = db.query(Alert)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)
    
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    
    return {
        "total": len(alerts),
        "alerts": alerts
    }

# ==================== File Upload ====================

@app.post("/orders/upload-bulk-files")
async def upload_bulk_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload multiple PDF files in PARALLEL - Max 10 files, 30MB each"""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed")

    temp_order_id = f"BULK-{uuid.uuid4().hex[:8].upper()}"

    file_data = []
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename} (only PDF allowed)"
            )

        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)

        if file_size_mb > 30:
            raise HTTPException(
                status_code=400,
                detail=f"{file.filename} too large: {file_size_mb:.2f}MB (max 30MB)"
            )

        # ✅ Extract PDF page count
        try:
            pdf_reader = PdfReader(io.BytesIO(file_content))
            page_count = len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"Error reading PDF {file.filename}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Could not read {file.filename} — possibly corrupted or encrypted"
            )

        file_data.append({
            'content': file_content,
            'filename': file.filename,
            'size_mb': file_size_mb,
            'page_count': page_count
        })

    # ✅ PARALLEL UPLOAD using asyncio.gather
    async def upload_single_file(file_info):
        try:
            file_url = upload_pdf_to_gcs(
                file_info['content'],
                file_info['filename'],
                temp_order_id
            )

            if not file_url:
                return None

            return {
                "filename": file_info['filename'],
                "file_url": file_url,
                "size_mb": round(file_info['size_mb'], 2),
                "page_count": file_info['page_count']
            }
        except Exception as e:
            logger.error(f"Upload failed for {file_info['filename']}: {e}")
            return None

    upload_tasks = [upload_single_file(file_info) for file_info in file_data]
    results = await asyncio.gather(*upload_tasks)

    uploaded_files = [r for r in results if r is not None]

    if len(uploaded_files) == 0:
        raise HTTPException(status_code=500, detail="All file uploads failed")

    if len(uploaded_files) < len(files):
        logger.warning(f"Some files failed to upload: {len(files) - len(uploaded_files)} failures")

    logger.info(f"Bulk upload: {len(uploaded_files)}/{len(files)} files for user {current_user.username}")

    return {
        "success": True,
        "temp_order_id": temp_order_id,
        "files": uploaded_files,
        "total_files": len(uploaded_files),
        "failed_count": len(files) - len(uploaded_files)
    }

# ==================== System Management ====================

@app.post("/system/sync-printers")
def sync_printers(db: Session = Depends(get_db)):
    """Manually sync printer status from simulation"""
    sync_printer_status_from_simulation(db)
    return {"message": "Printers synced successfully"}

@app.post("/system/reset")
async def reset_system(db: Session = Depends(get_db)):
    """Reset entire system"""
    logger.warning("⚠️ System reset initiated")
    
    # Reset printer simulation
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{PRINTER_API_URL}/reset", timeout=10.0)
    except:
        pass
    
    # Clear database
    db.query(JobQueueEntry).delete()
    db.query(OrderHistory).delete()
    db.query(PaymentTransaction).delete()
    db.query(Order).delete()
    db.query(Alert).delete()
    db.commit()
    
    # Clear scheduler cache
    if scheduler:
        scheduler.cache.clear()
    
    logger.info("✅ System reset complete")
    
    return {"message": "System reset successfully"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    
    # Check database
    try:
        db.execute("SELECT 1")
        db_healthy = True
    except:
        db_healthy = False
    
    # Check printer API
    try:
        import requests
        response = requests.get(f"{PRINTER_API_URL}/health", timeout=3.0)
        printer_api_healthy = response.status_code == 200
    except:
        printer_api_healthy = False
    
    # Check scheduler
    scheduler_healthy = scheduler is not None
    
    overall_healthy = db_healthy and printer_api_healthy and scheduler_healthy
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "healthy" if db_healthy else "unhealthy",
            "printer_api": "healthy" if printer_api_healthy else "unhealthy",
            "scheduler": "healthy" if scheduler_healthy else "unhealthy"
        },
        "version": "3.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
Job Management FastAPI Server with PostgreSQL and Authentication
Run: uvicorn backend:app --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import httpx
import uuid
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
import os

from database import get_db, init_db
from models import (
    Store, SupervisorData, Printer, Order, Alert, User,
    OrderStatusEnum, PaymentStatusEnum, PrinterStatusEnum,
    AlertTypeEnum, AlertSeverityEnum, StoreStatusEnum
)
from auth import (
    hash_password, verify_password, create_access_token,
    decode_access_token, generate_user_id
)

from smart_scheduler import (
    SmartScheduler, Printer as SchedulerPrinter, PrintJob,
    ColorMode as SchedulerColorMode, PrinterStatus as SchedulerPrinterStatus
)

# ==================== Logging Setup ====================

logger = logging.getLogger("backend")
logger.setLevel(logging.INFO)

os.makedirs("logs", exist_ok=True)

file_handler = RotatingFileHandler("logs/backend.log", maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ==================== FastAPI App ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and scheduler using lifespan events"""
    global scheduler

    logger.info("🚀 Starting Backend API...")

    # --- Database Initialization ---
    try:
        init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")

    # --- Scheduler Initialization ---
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRINTER_API_URL}/printers", timeout=5.0)
            response.raise_for_status()
            printer_data = response.json()

        printers = []
        for p in printer_data:
            printers.append(SchedulerPrinter(
                id=p["printer_id"],
                name=p["name"],
                supports_color=p["supports_color"],
                bw_speed=p["bw_speed"],
                color_speed=p.get("color_speed", 0.0) or 0.0,
                status=SchedulerPrinterStatus.IDLE,
                next_available_time=datetime.now(),
                current_load=0,
                location=p["location"]
            ))

        scheduler = SmartScheduler(printers)
        logger.info(f"✓ Scheduler initialized with {len(printers)} printers")

    except Exception as e:
        logger.error(f"✗ Scheduler initialization failed: {e}")

    # --- Startup complete ---
    yield  # ← this lets FastAPI continue running the app

    # --- (Optional) Shutdown logic ---
    logger.info("🛑 Shutting down Backend API...")
    
app = FastAPI(title="Smart Print Management API", version="2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PRINTER_API_URL = "http://localhost:8001"

# ==================== Request/Response Models ====================

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

class SubmitJobRequest(BaseModel):
    pages: int
    copies: int = 1
    color_mode: str
    priority: int = 2
    store_id: str = "STORE001"

class JobResponse(BaseModel):
    order_id: str
    status: str
    assigned_printer_id: Optional[str]
    estimated_start_time: Optional[datetime]
    estimated_end_time: Optional[datetime]
    estimated_wait_seconds: Optional[int]
    price: float
    message: str

class StoreCreate(BaseModel):
    store_id: str
    store_name: str
    address: str
    contact_number: Optional[str]
    email: Optional[str]
    business_hours: Optional[dict]
    pricing_info: Optional[dict]
    payment_modes: Optional[list]

class PrinterCreate(BaseModel):
    printer_id: str
    store_id: str
    printer_name: str
    printer_model: Optional[str]
    color_support: bool
    duplex_support: bool = False

# ==================== Global Scheduler ====================

scheduler: Optional[SmartScheduler] = None

# ==================== Helper Functions ====================

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

def calculate_price(pages: int, copies: int, color_mode: str, store_id: str, db: Session) -> float:
    """Calculate print job price"""
    store = db.query(Store).filter(Store.store_id == store_id).first()
    
    if store and store.pricing_info:
        pricing = store.pricing_info
        bw_price = pricing.get("bw_per_page", 2.0)
        color_price = pricing.get("color_per_page", 10.0)
    else:
        bw_price = 2.0
        color_price = 10.0
    
    total_pages = pages * copies
    price_per_page = color_price if color_mode == "color" else bw_price
    
    return round(total_pages * price_per_page, 2)

async def send_to_printer_api(printer_id: str, job_id: str, pages: int, copies: int, color_mode: str):
    """Send job to printer simulation API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PRINTER_API_URL}/printers/{printer_id}/print",
                json={
                    "job_id": job_id,
                    "pages": pages,
                    "copies": copies,
                    "color_mode": color_mode,
                    "priority": 2
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to send job {job_id} to printer {printer_id}: {e}")
        raise

def create_alert(db: Session, store_id: str, alert_type: AlertTypeEnum, message: str, 
                severity: AlertSeverityEnum, printer_id: Optional[str] = None, 
                order_id: Optional[str] = None):
    """Create system alert"""
    alert = Alert(
        store_id=store_id,
        printer_id=printer_id,
        order_id=order_id,
        alert_type=alert_type,
        alert_message=message,
        severity=severity
    )
    db.add(alert)
    db.commit()
    logger.info(f"Alert created: {alert_type} - {message}")

# ==================== API Endpoints ====================

@app.get("/")
def root():
    return {
        "message": "Smart Print Management API",
        "version": "2.0",
        "scheduler_active": scheduler is not None,
        "database": "PostgreSQL"
    }

# ==================== Authentication ====================

@app.post("/auth/signup", response_model=AuthResponse)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """User signup"""
    logger.info(f"Signup attempt: {request.username}")
    
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.email == request.email) | (User.username == request.username)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    # Create user
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
    
    # Create token
    access_token = create_access_token(data={"sub": user.user_id})
    
    logger.info(f"User created: {user.user_id}")
    
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name
        }
    )

@app.post("/auth/signin", response_model=AuthResponse)
def signin(request: SigninRequest, db: Session = Depends(get_db)):
    """User signin"""
    logger.info(f"Signin attempt: {request.username}")
    
    # Find user
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create token
    access_token = create_access_token(data={"sub": user.user_id})
    
    logger.info(f"User signed in: {user.user_id}")
    
    return AuthResponse(
        access_token=access_token,
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
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "balance": current_user.balance,
        "created_at": current_user.created_at
    }

# ==================== Store Management ====================

@app.post("/stores", status_code=status.HTTP_201_CREATED)
def create_store(store_data: StoreCreate, db: Session = Depends(get_db)):
    """Create new store"""
    logger.info(f"Creating store: {store_data.store_id}")
    
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
        pricing_info=store_data.pricing_info or {"bw_per_page": 2.0, "color_per_page": 10.0},
        payment_modes=store_data.payment_modes or ["cash", "upi"]
    )
    
    db.add(store)
    db.commit()
    db.refresh(store)
    
    logger.info(f"Store {store_data.store_id} created successfully")
    return {"message": "Store created", "store_id": store.store_id}

@app.get("/stores")
def list_stores(db: Session = Depends(get_db)):
    """List all stores"""
    stores = db.query(Store).all()
    return {"total": len(stores), "stores": stores}

@app.get("/stores/{store_id}")
def get_store(store_id: str, db: Session = Depends(get_db)):
    """Get store details"""
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

# ==================== Order Management ====================

@app.post("/orders/submit", response_model=JobResponse)
async def submit_order(
    request: SubmitJobRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit new print order"""
    
    logger.info(f"Order from user {current_user.username}: {request.pages}p × {request.copies}, {request.color_mode}")
    
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    price = calculate_price(request.pages, request.copies, request.color_mode, request.store_id, db)
    
    # Create scheduler job
    scheduler_job = PrintJob(
        job_id=order_id,
        pages=request.pages,
        copies=request.copies,
        color_mode=SchedulerColorMode.COLOR if request.color_mode == "color" else SchedulerColorMode.BW,
        priority=request.priority,
        submitted_at=datetime.now(),
        user_id=current_user.user_id
    )
    
    scheduled = scheduler.schedule_job(scheduler_job)
    
    if not scheduled:
        logger.warning(f"No printer available for order {order_id}")
        create_alert(db, request.store_id, AlertTypeEnum.OTHER, 
                    "No suitable printer available", AlertSeverityEnum.CRITICAL)
        raise HTTPException(status_code=503, detail="No suitable printer available")
    
    # Create order in database
    order = Order(
        order_id=order_id,
        user_id=current_user.user_id,
        store_id=request.store_id,
        printer_id=scheduled.printer_id,
        pages_count=request.pages,
        copies=request.copies,
        print_settings={
            "color_mode": request.color_mode,
            "priority": request.priority
        },
        price=price,
        status=OrderStatusEnum.PROCESSING,
        estimated_start_time=scheduled.start_time,
        estimated_end_time=scheduled.end_time
    )
    
    db.add(order)
    db.commit()
    
    logger.info(f"Order {order_id} scheduled to {scheduled.printer_id}, price={price}")
    
    # Send to printer API
    try:
        await send_to_printer_api(
            scheduled.printer_id,
            order_id,
            request.pages,
            request.copies,
            request.color_mode
        )
        
        order.status = OrderStatusEnum.PROCESSING
        order.actual_start_time = datetime.now()
        db.commit()
        
        logger.info(f"Order {order_id} sent to printer successfully")
        
    except Exception as e:
        order.status = OrderStatusEnum.FAILED
        db.commit()
        
        create_alert(db, request.store_id, AlertTypeEnum.OTHER,
                    f"Failed to send order {order_id} to printer", AlertSeverityEnum.CRITICAL,
                    printer_id=scheduled.printer_id, order_id=order_id)
        
        raise HTTPException(status_code=500, detail=f"Failed to send to printer: {e}")
    
    return JobResponse(
        order_id=order_id,
        status=order.status.value,
        assigned_printer_id=scheduled.printer_id,
        estimated_start_time=scheduled.start_time,
        estimated_end_time=scheduled.end_time,
        estimated_wait_seconds=scheduled.estimated_wait_seconds,
        price=price,
        message="Order submitted successfully"
    )

@app.get("/orders/my-orders")
def get_my_orders(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get current user's orders"""
    orders = db.query(Order).filter(Order.user_id == current_user.user_id)\
        .order_by(Order.order_date.desc()).limit(limit).all()
    
    return {
        "total": len(orders),
        "orders": orders
    }

@app.get("/orders/{order_id}")
async def get_order_status(order_id: str, db: Session = Depends(get_db)):
    """Get order status"""
    
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Try to get real-time status from printer API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PRINTER_API_URL}/jobs/{order_id}")
            if response.status_code == 200:
                printer_status = response.json()
                
                if printer_status["status"] == "printing":
                    order.status = OrderStatusEnum.PROCESSING
                elif printer_status["status"] == "completed":
                    order.status = OrderStatusEnum.COMPLETED
                    if not order.actual_end_time:
                        order.actual_end_time = datetime.now()
                        order.completion_date = datetime.now()
                elif printer_status["status"] == "failed":
                    order.status = OrderStatusEnum.FAILED
                
                db.commit()
                
                return {
                    "order": order,
                    "printer_status": printer_status
                }
    except:
        pass
    
    return {"order": order}

@app.get("/orders")
def list_orders(
    status: Optional[str] = None,
    store_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List orders with filters"""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status == status)
    if store_id:
        query = query.filter(Order.store_id == store_id)
    
    orders = query.order_by(Order.order_date.desc()).limit(limit).all()
    
    return {
        "total": len(orders),
        "orders": orders
    }

# ==================== Stats ====================

@app.get("/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PRINTER_API_URL}/stats")
            printer_stats = response.json()
    except:
        printer_stats = {}
    
    total_orders = db.query(Order).count()
    completed_orders = db.query(Order).filter(Order.status == OrderStatusEnum.COMPLETED).count()
    pending_orders = db.query(Order).filter(Order.status == OrderStatusEnum.PENDING).count()
    
    return {
        "printers": printer_stats.get("printers", {}),
        "orders": {
            "total": total_orders,
            "completed": completed_orders,
            "pending": pending_orders
        },
        "printer_jobs": printer_stats.get("jobs", {})
    }

@app.post("/system/reset")
async def reset_system(db: Session = Depends(get_db)):
    """Reset system"""
    logger.warning("System reset initiated")
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{PRINTER_API_URL}/reset")
    except:
        pass
    
    db.query(Order).delete()
    db.query(Alert).delete()
    db.commit()
    
    await startup_event()
    
    logger.info("System reset complete")
    return {"message": "System reset successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
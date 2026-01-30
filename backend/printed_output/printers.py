"""
Printer Simulation FastAPI Server with Webhook Support
Simulates 6 printers (4 BW, 2 Color) with realistic print timing
NOW: Pushes updates via webhooks instead of requiring polling
Run: uvicorn printer_simulation:app --port 8001 --reload
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import uuid
from enum import Enum
import logging
from logging.handlers import RotatingFileHandler
import httpx

# ==================== Logging Setup ====================

logger = logging.getLogger("printer_simulation")
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(
    "logs/printer_simulation.log",
    maxBytes=10*1024*1024,
    backupCount=5
)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

import os
os.makedirs("logs", exist_ok=True)

app = FastAPI(title="Printer Simulation API", version="1.0")

# ==================== Models ====================

class ColorMode(str, Enum):
    BW = "bw"
    COLOR = "color"

class JobStatus(str, Enum):
    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"

class PrinterStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"

class PrintRequest(BaseModel):
    job_id: str
    pages: int
    copies: int
    color_mode: ColorMode
    priority: int = 2
    file_url: Optional[str] = None
    webhook_url: Optional[str] = None  # ✅ Backend provides this

class PrinterInfo(BaseModel):
    printer_id: str
    name: str
    supports_color: bool
    bw_speed: float
    color_speed: Optional[float]
    status: PrinterStatus
    current_job: Optional[str]
    queue_length: int
    location: str

class JobInfo(BaseModel):
    job_id: str
    printer_id: str
    status: JobStatus
    pages: int
    copies: int
    color_mode: ColorMode
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress_percent: int

# ==================== Simulated Printers ====================

PRINTERS: Dict[str, Dict] = {
    "P1": {
        "name": "BW Printer 1",
        "supports_color": False,
        "bw_speed": 1.0,
        "color_speed": None,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Campus-A"
    },
    "P2": {
        "name": "BW Printer 2",
        "supports_color": False,
        "bw_speed": 1.0,
        "color_speed": None,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Campus-A"
    },
    "P3": {
        "name": "BW Printer 3",
        "supports_color": False,
        "bw_speed": 1.0,
        "color_speed": None,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Campus-B"
    },
    "P4": {
        "name": "BW Printer 4",
        "supports_color": False,
        "bw_speed": 1.0,
        "color_speed": None,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Campus-B"
    },
    "P5": {
        "name": "Color Printer 1",
        "supports_color": True,
        "bw_speed": 1.0,
        "color_speed": 0.33,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Campus-A"
    },
    "P6": {
        "name": "Color Printer 2",
        "supports_color": True,
        "bw_speed": 1.0,
        "color_speed": 0.33,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Campus-B"
    }
}

JOBS: Dict[str, Dict] = {}

# ==================== Webhook Helper ====================

async def send_webhook(webhook_url: str, job_id: str, status: str, progress: int, printer_id: str, message: str = None):
    """Send webhook update to backend"""
    if not webhook_url:
        return
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            payload = {
                "job_id": job_id,
                "status": status,
                "progress_percent": progress,
                "printer_id": printer_id,
                "message": message
            }
            
            response = await client.post(webhook_url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Webhook sent for {job_id}: {status} ({progress}%)")
            else:
                logger.warning(f"⚠️ Webhook failed for {job_id}: {response.status_code}")
                
    except Exception as e:
        logger.error(f"❌ Webhook error for {job_id}: {e}")

# ==================== Simulation Logic ====================

async def simulate_printing(printer_id: str, job_id: str):
    """Simulate actual printing process with webhook updates"""
    printer = PRINTERS[printer_id]
    job = JOBS[job_id]
    
    try:
        logger.info(f"[{printer_id}] Starting job {job_id} - {job['pages']} pages, {job['copies']} copies, {job['color_mode']}")
        
        # Mark as printing
        job["status"] = JobStatus.PRINTING
        job["started_at"] = datetime.now()
        printer["status"] = PrinterStatus.BUSY
        printer["current_job"] = job_id
        
        # ✅ Send webhook: printing started
        await send_webhook(
            job.get("webhook_url"),
            job_id,
            "printing",
            0,
            printer_id,
            "Print job started"
        )
        
        # Calculate print time
        total_pages = job["pages"] * job["copies"]
        if job["color_mode"] == ColorMode.COLOR:
            speed = printer["color_speed"]
        else:
            speed = printer["bw_speed"]
        
        total_time = total_pages / speed
        
        # Simulate printing with progress updates
        steps = 10
        step_time = total_time / steps
        
        for i in range(1, steps + 1):
            await asyncio.sleep(step_time)
            progress = int((i / steps) * 100)
            job["progress_percent"] = progress
            
            # ✅ Send webhook: progress update (every 25%)
            if progress in [25, 50, 75]:
                await send_webhook(
                    job.get("webhook_url"),
                    job_id,
                    "printing",
                    progress,
                    printer_id,
                    f"Printing in progress: {progress}%"
                )
                logger.info(f"[{printer_id}] Job {job_id} - {progress}% complete")
        
        # Mark as completed
        job["status"] = JobStatus.COMPLETED
        job["completed_at"] = datetime.now()
        job["progress_percent"] = 100
        printer["current_job"] = None
        
        # ✅ Send webhook: completed
        await send_webhook(
            job.get("webhook_url"),
            job_id,
            "completed",
            100,
            printer_id,
            "Print job completed successfully"
        )
        
        logger.info(f"[{printer_id}] Job {job_id} completed in {total_time:.1f}s")
        
        # Process next job in queue if any
        if printer["queue"]:
            next_job_id = printer["queue"].pop(0)
            logger.info(f"[{printer_id}] Processing next job from queue: {next_job_id}")
            asyncio.create_task(simulate_printing(printer_id, next_job_id))
        else:
            printer["status"] = PrinterStatus.IDLE
            logger.info(f"[{printer_id}] Now idle")
            
    except Exception as e:
        job["status"] = JobStatus.FAILED
        printer["status"] = PrinterStatus.IDLE
        printer["current_job"] = None
        
        # ✅ Send webhook: failed
        await send_webhook(
            job.get("webhook_url"),
            job_id,
            "failed",
            job.get("progress_percent", 0),
            printer_id,
            f"Print job failed: {str(e)}"
        )
        
        logger.error(f"[{printer_id}] Job {job_id} failed: {e}")

# ==================== API Endpoints ====================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Printer Simulation API started with Webhook support")

@app.get("/")
def root():
    return {
        "message": "Printer Simulation API",
        "printers": len(PRINTERS),
        "active_jobs": len([j for j in JOBS.values() if j["status"] in [JobStatus.PRINTING, JobStatus.QUEUED]]),
        "features": ["webhooks", "real-time-updates"]
    }

@app.get("/printers", response_model=List[PrinterInfo])
def list_printers():
    """Get all available printers and their status"""
    result = []
    for pid, printer in PRINTERS.items():
        result.append(PrinterInfo(
            printer_id=pid,
            name=printer["name"],
            supports_color=printer["supports_color"],
            bw_speed=printer["bw_speed"],
            color_speed=printer.get("color_speed"),
            status=printer["status"],
            current_job=printer["current_job"],
            queue_length=len(printer["queue"]),
            location=printer["location"]
        ))
    return result

@app.get("/printers/{printer_id}", response_model=PrinterInfo)
def get_printer(printer_id: str):
    """Get specific printer details"""
    if printer_id not in PRINTERS:
        logger.warning(f"Printer {printer_id} not found")
        raise HTTPException(status_code=404, detail="Printer not found")
    
    printer = PRINTERS[printer_id]
    return PrinterInfo(
        printer_id=printer_id,
        name=printer["name"],
        supports_color=printer["supports_color"],
        bw_speed=printer["bw_speed"],
        color_speed=printer.get("color_speed"),
        status=printer["status"],
        current_job=printer["current_job"],
        queue_length=len(printer["queue"]),
        location=printer["location"]
    )

@app.post("/printers/{printer_id}/print")
async def submit_print_job(printer_id: str, request: PrintRequest, background_tasks: BackgroundTasks):
    """Submit a print job to a specific printer"""
    if printer_id not in PRINTERS:
        logger.warning(f"Attempt to print to non-existent printer: {printer_id}")
        raise HTTPException(status_code=404, detail="Printer not found")
    
    printer = PRINTERS[printer_id]
    
    # Validate color support
    if request.color_mode == ColorMode.COLOR and not printer["supports_color"]:
        logger.warning(f"Color print attempted on BW printer {printer_id}")
        raise HTTPException(status_code=400, detail="Printer does not support color printing")
    
    # Create job record
    job_data = {
        "job_id": request.job_id,
        "printer_id": printer_id,
        "status": JobStatus.QUEUED,
        "pages": request.pages,
        "copies": request.copies,
        "color_mode": request.color_mode,
        "priority": request.priority,
        "file_url": request.file_url,
        "webhook_url": request.webhook_url,  # ✅ Store webhook URL
        "started_at": None,
        "completed_at": None,
        "progress_percent": 0,
        "queued_at": datetime.now()
    }
    
    JOBS[request.job_id] = job_data
    
    file_info = f" (with file: {request.file_url})" if request.file_url else ""
    webhook_info = f" [webhook: {request.webhook_url}]" if request.webhook_url else ""
    logger.info(f"Job {request.job_id} submitted to {printer_id}{file_info}{webhook_info}")
    
    # If printer is idle, start immediately
    if printer["status"] == PrinterStatus.IDLE:
        background_tasks.add_task(simulate_printing, printer_id, request.job_id)
    else:
        # Add to queue
        printer["queue"].append(request.job_id)
        job_data["status"] = JobStatus.QUEUED
        logger.info(f"Job {request.job_id} queued (position {len(printer['queue'])})")
    
    return {
        "message": "Job submitted successfully",
        "job_id": request.job_id,
        "printer_id": printer_id,
        "status": job_data["status"],
        "queue_position": len(printer["queue"]) if job_data["status"] == JobStatus.QUEUED else 0,
        "has_file": bool(request.file_url),
        "webhook_enabled": bool(request.webhook_url)
    }
    
@app.get("/jobs/{job_id}", response_model=JobInfo)
def get_job_status(job_id: str):
    """Get status of a specific print job"""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = JOBS[job_id]
    return JobInfo(
        job_id=job["job_id"],
        printer_id=job["printer_id"],
        status=job["status"],
        pages=job["pages"],
        copies=job["copies"],
        color_mode=job["color_mode"],
        started_at=job["started_at"],
        completed_at=job["completed_at"],
        progress_percent=job["progress_percent"]
    )

@app.get("/jobs")
def list_all_jobs():
    """List all jobs"""
    return {
        "total_jobs": len(JOBS),
        "jobs": list(JOBS.values())
    }

@app.post("/printers/{printer_id}/status")
def update_printer_status(printer_id: str, status: PrinterStatus):
    """Manually update printer status"""
    if printer_id not in PRINTERS:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    PRINTERS[printer_id]["status"] = status
    logger.info(f"Printer {printer_id} status updated to {status}")
    return {"message": f"Printer {printer_id} status updated to {status}"}

@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    """Cancel a queued job"""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = JOBS[job_id]
    if job["status"] == JobStatus.PRINTING:
        raise HTTPException(status_code=400, detail="Cannot cancel job that is already printing")
    
    printer_id = job["printer_id"]
    if job_id in PRINTERS[printer_id]["queue"]:
        PRINTERS[printer_id]["queue"].remove(job_id)
    
    job["status"] = JobStatus.FAILED
    logger.info(f"Job {job_id} cancelled")
    return {"message": f"Job {job_id} cancelled"}

@app.post("/reset")
def reset_simulation():
    """Reset all printers and jobs"""
    global JOBS
    JOBS = {}
    
    for printer in PRINTERS.values():
        printer["status"] = PrinterStatus.IDLE
        printer["current_job"] = None
        printer["queue"] = []
    
    logger.info("Simulation reset")
    return {"message": "Simulation reset successfully"}

@app.get("/stats")
def get_statistics():
    """Get overall system statistics"""
    total_jobs = len(JOBS)
    completed_jobs = len([j for j in JOBS.values() if j["status"] == JobStatus.COMPLETED])
    printing_jobs = len([j for j in JOBS.values() if j["status"] == JobStatus.PRINTING])
    queued_jobs = len([j for j in JOBS.values() if j["status"] == JobStatus.QUEUED])
    
    idle_printers = len([p for p in PRINTERS.values() if p["status"] == PrinterStatus.IDLE])
    busy_printers = len([p for p in PRINTERS.values() if p["status"] == PrinterStatus.BUSY])
    
    return {
        "printers": {
            "total": len(PRINTERS),
            "idle": idle_printers,
            "busy": busy_printers,
            "bw_printers": 4,
            "color_printers": 2
        },
        "jobs": {
            "total": total_jobs,
            "completed": completed_jobs,
            "printing": printing_jobs,
            "queued": queued_jobs,
            "failed": len([j for j in JOBS.values() if j["status"] == JobStatus.FAILED])
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

# V2

#     """
# Enhanced Printer Simulation FastAPI Server
# Features: Multiple print types, consumable tracking, automated alerts
# Run: uvicorn printers:app --port 8001 --reload
# """

# from fastapi import FastAPI, HTTPException, BackgroundTasks
# from pydantic import BaseModel
# from typing import Dict, List, Optional
# from datetime import datetime, timedelta
# import asyncio
# import uuid
# from enum import Enum
# import logging
# from logging.handlers import RotatingFileHandler
# import httpx

# # ==================== Logging Setup ====================

# logger = logging.getLogger("printer_simulation")
# logger.setLevel(logging.INFO)

# file_handler = RotatingFileHandler(
#     "logs/printer_simulation.log",
#     maxBytes=10*1024*1024,
#     backupCount=5
# )
# file_handler.setLevel(logging.INFO)

# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.INFO)

# formatter = logging.Formatter(
#     '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
# file_handler.setFormatter(formatter)
# console_handler.setFormatter(formatter)

# logger.addHandler(file_handler)
# logger.addHandler(console_handler)

# import os
# os.makedirs("logs", exist_ok=True)

# app = FastAPI(title="Enhanced Printer Simulation API", version="2.0")

# # ==================== Models ====================

# class PrintType(str, Enum):
#     BW = "bw"
#     COLOR = "color"
#     THICK = "thick"
#     GLOSSY = "glossy"

# class JobStatus(str, Enum):
#     QUEUED = "queued"
#     PRINTING = "printing"
#     COMPLETED = "completed"
#     FAILED = "failed"

# class PrinterStatus(str, Enum):
#     IDLE = "idle"
#     BUSY = "busy"
#     OFFLINE = "offline"
#     MAINTENANCE = "maintenance"

# class AlertType(str, Enum):
#     PAPER_LOW = "PAPER_LOW"
#     PAPER_OUT = "PAPER_OUT"
#     INK_LOW = "INK_LOW"
#     INK_EMPTY = "INK_EMPTY"
#     TONER_LOW = "TONER_LOW"
#     TONER_EMPTY = "TONER_EMPTY"
#     THICK_PAPER_LOW = "THICK_PAPER_LOW"
#     GLOSSY_PAPER_LOW = "GLOSSY_PAPER_LOW"

# class PrintRequest(BaseModel):
#     job_id: str
#     pages: int
#     copies: int
#     print_type: PrintType
#     priority: int = 2
#     file_url: Optional[str] = None
#     webhook_url: Optional[str] = None

# class PrinterInfo(BaseModel):
#     printer_id: str
#     name: str
#     supported_types: List[PrintType]
#     bw_speed: float
#     color_speed: Optional[float]
#     status: PrinterStatus
#     current_job: Optional[str]
#     queue_length: int
#     location: str
#     consumables: Dict

# class JobInfo(BaseModel):
#     job_id: str
#     printer_id: str
#     status: JobStatus
#     pages: int
#     copies: int
#     print_type: PrintType
#     started_at: Optional[datetime]
#     completed_at: Optional[datetime]
#     progress_percent: int

# class AlertPayload(BaseModel):
#     alert_code: str
#     category: str
#     description: str
#     severity: str
#     printer_id: str
#     printer_name: str
#     timestamp: datetime
#     consumable_levels: Dict
#     action_taken: str

# # ==================== Alert Thresholds ====================

# ALERT_THRESHOLDS = {
#     "paper_low": 500,
#     "ink_low": 20,
#     "toner_low": 15,
#     "thick_paper_low": 50,
#     "glossy_paper_low": 50
# }

# # ==================== Simulated Printers with Consumables ====================

# PRINTERS: Dict[str, Dict] = {
#     "P1": {
#         "name": "BW Printer 1",
#         "supported_types": [PrintType.BW],
#         "bw_speed": 1.0,
#         "color_speed": None,
#         "status": PrinterStatus.IDLE,
#         "current_job": None,
#         "queue": [],
#         "location": "Campus-A",
#         "consumables": {
#             "paper": 2000,
#             "toner_bw": 85,  # percentage
#             "ink_black": None,
#             "ink_cyan": None,
#             "ink_magenta": None,
#             "ink_yellow": None,
#             "thick_paper": 0,
#             "glossy_paper": 0
#         }
#     },
#     "P2": {
#         "name": "BW Printer 2",
#         "supported_types": [PrintType.BW],
#         "bw_speed": 1.0,
#         "color_speed": None,
#         "status": PrinterStatus.IDLE,
#         "current_job": None,
#         "queue": [],
#         "location": "Campus-A",
#         "consumables": {
#             "paper": 1800,
#             "toner_bw": 60,
#             "ink_black": None,
#             "ink_cyan": None,
#             "ink_magenta": None,
#             "ink_yellow": None,
#             "thick_paper": 0,
#             "glossy_paper": 0
#         }
#     },
#     "P3": {
#         "name": "Premium Multi-Function 1",
#         "supported_types": [PrintType.BW, PrintType.COLOR, PrintType.THICK, PrintType.GLOSSY],
#         "bw_speed": 1.0,
#         "color_speed": 0.33,
#         "status": PrinterStatus.IDLE,
#         "current_job": None,
#         "queue": [],
#         "location": "Campus-B",
#         "consumables": {
#             "paper": 2500,
#             "toner_bw": None,
#             "ink_black": 75,
#             "ink_cyan": 80,
#             "ink_magenta": 70,
#             "ink_yellow": 85,
#             "thick_paper": 150,
#             "glossy_paper": 120
#         }
#     },
#     "P4": {
#         "name": "BW High-Speed Printer",
#         "supported_types": [PrintType.BW, PrintType.THICK],
#         "bw_speed": 1.5,
#         "color_speed": None,
#         "status": PrinterStatus.IDLE,
#         "current_job": None,
#         "queue": [],
#         "location": "Campus-B",
#         "consumables": {
#             "paper": 3000,
#             "toner_bw": 90,
#             "ink_black": None,
#             "ink_cyan": None,
#             "ink_magenta": None,
#             "ink_yellow": None,
#             "thick_paper": 200,
#             "glossy_paper": 0
#         }
#     },
#     "P5": {
#         "name": "Color Printer Standard",
#         "supported_types": [PrintType.BW, PrintType.COLOR],
#         "bw_speed": 1.0,
#         "color_speed": 0.33,
#         "status": PrinterStatus.IDLE,
#         "current_job": None,
#         "queue": [],
#         "location": "Campus-A",
#         "consumables": {
#             "paper": 2200,
#             "toner_bw": None,
#             "ink_black": 65,
#             "ink_cyan": 55,
#             "ink_magenta": 60,
#             "ink_yellow": 70,
#             "thick_paper": 0,
#             "glossy_paper": 0
#         }
#     },
#     "P6": {
#         "name": "Premium Multi-Function 2",
#         "supported_types": [PrintType.BW, PrintType.COLOR, PrintType.THICK, PrintType.GLOSSY],
#         "bw_speed": 1.0,
#         "color_speed": 0.33,
#         "status": PrinterStatus.IDLE,
#         "current_job": None,
#         "queue": [],
#         "location": "Campus-B",
#         "consumables": {
#             "paper": 2800,
#             "toner_bw": None,
#             "ink_black": 88,
#             "ink_cyan": 92,
#             "ink_magenta": 85,
#             "ink_yellow": 90,
#             "thick_paper": 180,
#             "glossy_paper": 100
#         }
#     }
# }

# JOBS: Dict[str, Dict] = {}
# ALERT_BACKEND_URL = "http://localhost:8000/api/alerts/printer"  # Backend alert endpoint

# # ==================== Consumable Management ====================

# def consume_resources(printer_id: str, print_type: PrintType, pages: int, copies: int):
#     """Deduct consumables based on print job"""
#     printer = PRINTERS[printer_id]
#     consumables = printer["consumables"]
#     total_pages = pages * copies
    
#     # Deduct paper
#     if print_type == PrintType.THICK:
#         consumables["thick_paper"] -= total_pages
#     elif print_type == PrintType.GLOSSY:
#         consumables["glossy_paper"] -= total_pages
#     else:
#         consumables["paper"] -= total_pages
    
#     # Deduct ink/toner (percentage depletion)
#     if print_type == PrintType.BW:
#         if consumables["toner_bw"] is not None:
#             consumables["toner_bw"] -= total_pages * 0.05  # 0.05% per page
#     elif print_type in [PrintType.COLOR, PrintType.GLOSSY]:
#         if consumables["ink_black"] is not None:
#             consumables["ink_black"] -= total_pages * 0.08
#             consumables["ink_cyan"] -= total_pages * 0.1
#             consumables["ink_magenta"] -= total_pages * 0.1
#             consumables["ink_yellow"] -= total_pages * 0.1
    
#     logger.info(f"[{printer_id}] Consumed resources for {total_pages} pages ({print_type})")

# async def check_and_send_alerts(printer_id: str):
#     """Check consumable levels and send alerts if needed"""
#     printer = PRINTERS[printer_id]
#     consumables = printer["consumables"]
#     alerts_sent = []
    
#     # Check paper
#     if consumables["paper"] < ALERT_THRESHOLDS["paper_low"]:
#         alert = await send_alert(
#             printer_id,
#             AlertType.PAPER_LOW if consumables["paper"] > 0 else AlertType.PAPER_OUT,
#             f"Regular paper {'low' if consumables['paper'] > 0 else 'empty'}: {consumables['paper']} sheets",
#             consumables
#         )
#         if alert:
#             alerts_sent.append(alert)
#             # Auto-refill
#             consumables["paper"] = 2500
#             logger.info(f"✅ [{printer_id}] Paper auto-refilled to 2500 sheets")
    
#     # Check thick paper
#     if consumables["thick_paper"] > 0 and consumables["thick_paper"] < ALERT_THRESHOLDS["thick_paper_low"]:
#         alert = await send_alert(
#             printer_id,
#             AlertType.THICK_PAPER_LOW,
#             f"Thick paper low: {consumables['thick_paper']} sheets",
#             consumables
#         )
#         if alert:
#             alerts_sent.append(alert)
#             consumables["thick_paper"] = 200
#             logger.info(f"✅ [{printer_id}] Thick paper auto-refilled to 200 sheets")
    
#     # Check glossy paper
#     if consumables["glossy_paper"] > 0 and consumables["glossy_paper"] < ALERT_THRESHOLDS["glossy_paper_low"]:
#         alert = await send_alert(
#             printer_id,
#             AlertType.GLOSSY_PAPER_LOW,
#             f"Glossy paper low: {consumables['glossy_paper']} sheets",
#             consumables
#         )
#         if alert:
#             alerts_sent.append(alert)
#             consumables["glossy_paper"] = 150
#             logger.info(f"✅ [{printer_id}] Glossy paper auto-refilled to 150 sheets")
    
#     # Check toner
#     if consumables["toner_bw"] is not None and consumables["toner_bw"] < ALERT_THRESHOLDS["toner_low"]:
#         alert = await send_alert(
#             printer_id,
#             AlertType.TONER_LOW if consumables["toner_bw"] > 0 else AlertType.TONER_EMPTY,
#             f"BW Toner {'low' if consumables['toner_bw'] > 0 else 'empty'}: {consumables['toner_bw']:.1f}%",
#             consumables
#         )
#         if alert:
#             alerts_sent.append(alert)
#             consumables["toner_bw"] = 100
#             logger.info(f"✅ [{printer_id}] BW Toner auto-refilled to 100%")
    
#     # Check ink levels
#     ink_colors = ["ink_black", "ink_cyan", "ink_magenta", "ink_yellow"]
#     for ink in ink_colors:
#         if consumables[ink] is not None and consumables[ink] < ALERT_THRESHOLDS["ink_low"]:
#             alert = await send_alert(
#                 printer_id,
#                 AlertType.INK_LOW if consumables[ink] > 0 else AlertType.INK_EMPTY,
#                 f"{ink.replace('ink_', '').title()} ink {'low' if consumables[ink] > 0 else 'empty'}: {consumables[ink]:.1f}%",
#                 consumables
#             )
#             if alert:
#                 alerts_sent.append(alert)
#                 consumables[ink] = 100
#                 logger.info(f"✅ [{printer_id}] {ink.replace('ink_', '').title()} ink auto-refilled to 100%")
    
#     return alerts_sent

# async def send_alert(printer_id: str, alert_type: AlertType, description: str, consumables: Dict):
#     """Send alert to backend"""
#     printer = PRINTERS[printer_id]
    
#     # Map alert type to category and severity
#     alert_mapping = {
#         AlertType.PAPER_LOW: ("Consumable", "Warning", "PAPER_OUT"),
#         AlertType.PAPER_OUT: ("Consumable", "Critical", "PAPER_OUT"),
#         AlertType.INK_LOW: ("Consumable", "Info", "TONER_LOW"),
#         AlertType.INK_EMPTY: ("Consumable", "Critical", "TONER_EMPTY"),
#         AlertType.TONER_LOW: ("Consumable", "Info", "TONER_LOW"),
#         AlertType.TONER_EMPTY: ("Consumable", "Critical", "TONER_EMPTY"),
#         AlertType.THICK_PAPER_LOW: ("Consumable", "Warning", "PAPER_OUT"),
#         AlertType.GLOSSY_PAPER_LOW: ("Consumable", "Warning", "PAPER_OUT"),
#     }
    
#     category, severity, alert_code = alert_mapping.get(alert_type, ("Consumable", "Info", alert_type.value))
    
#     payload = AlertPayload(
#         alert_code=alert_code,
#         category=category,
#         description=description,
#         severity=severity,
#         printer_id=printer_id,
#         printer_name=printer["name"],
#         timestamp=datetime.now(),
#         consumable_levels=consumables.copy(),
#         action_taken="Auto-refill initiated"
#     )
    
#     try:
#         async with httpx.AsyncClient(timeout=5.0) as client:
#             response = await client.post(ALERT_BACKEND_URL, json=payload.dict())
            
#             if response.status_code == 200:
#                 logger.info(f"🚨 Alert sent to backend: {alert_code} for {printer_id}")
#                 return payload
#             else:
#                 logger.warning(f"⚠️ Alert send failed: {response.status_code}")
#                 return None
                
#     except Exception as e:
#         logger.error(f"❌ Alert send error: {e}")
#         return None

# # ==================== Webhook Helper ====================

# async def send_webhook(webhook_url: str, job_id: str, status: str, progress: int, printer_id: str, message: str = None):
#     """Send webhook update to backend"""
#     if not webhook_url:
#         return
    
#     try:
#         async with httpx.AsyncClient(timeout=5.0) as client:
#             payload = {
#                 "job_id": job_id,
#                 "status": status,
#                 "progress_percent": progress,
#                 "printer_id": printer_id,
#                 "message": message
#             }
            
#             response = await client.post(webhook_url, json=payload)
            
#             if response.status_code == 200:
#                 logger.info(f"✅ Webhook sent for {job_id}: {status} ({progress}%)")
#             else:
#                 logger.warning(f"⚠️ Webhook failed for {job_id}: {response.status_code}")
                
#     except Exception as e:
#         logger.error(f"❌ Webhook error for {job_id}: {e}")

# # ==================== Simulation Logic ====================

# async def simulate_printing(printer_id: str, job_id: str):
#     """Simulate actual printing process with webhook updates and consumable tracking"""
#     printer = PRINTERS[printer_id]
#     job = JOBS[job_id]
    
#     try:
#         logger.info(f"[{printer_id}] Starting job {job_id} - {job['pages']} pages, {job['copies']} copies, {job['print_type']}")
        
#         # Mark as printing
#         job["status"] = JobStatus.PRINTING
#         job["started_at"] = datetime.now()
#         printer["status"] = PrinterStatus.BUSY
#         printer["current_job"] = job_id
        
#         # Send webhook: printing started
#         await send_webhook(
#             job.get("webhook_url"),
#             job_id,
#             "printing",
#             0,
#             printer_id,
#             "Print job started"
#         )
        
#         # Calculate print time
#         total_pages = job["pages"] * job["copies"]
#         if job["print_type"] in [PrintType.COLOR, PrintType.GLOSSY]:
#             speed = printer["color_speed"]
#         else:
#             speed = printer["bw_speed"]
        
#         total_time = total_pages / speed
        
#         # Simulate printing with progress updates
#         steps = 10
#         step_time = total_time / steps
        
#         for i in range(1, steps + 1):
#             await asyncio.sleep(step_time)
#             progress = int((i / steps) * 100)
#             job["progress_percent"] = progress
            
#             # Send webhook: progress update
#             if progress in [25, 50, 75]:
#                 await send_webhook(
#                     job.get("webhook_url"),
#                     job_id,
#                     "printing",
#                     progress,
#                     printer_id,
#                     f"Printing in progress: {progress}%"
#                 )
#                 logger.info(f"[{printer_id}] Job {job_id} - {progress}% complete")
        
#         # Consume resources
#         consume_resources(printer_id, job["print_type"], job["pages"], job["copies"])
        
#         # Check consumables and send alerts if needed
#         alerts = await check_and_send_alerts(printer_id)
        
#         # Mark as completed
#         job["status"] = JobStatus.COMPLETED
#         job["completed_at"] = datetime.now()
#         job["progress_percent"] = 100
#         printer["current_job"] = None
        
#         # Send webhook: completed
#         await send_webhook(
#             job.get("webhook_url"),
#             job_id,
#             "completed",
#             100,
#             printer_id,
#             "Print job completed successfully"
#         )
        
#         logger.info(f"[{printer_id}] Job {job_id} completed in {total_time:.1f}s")
        
#         # Process next job in queue if any
#         if printer["queue"]:
#             next_job_id = printer["queue"].pop(0)
#             logger.info(f"[{printer_id}] Processing next job from queue: {next_job_id}")
#             asyncio.create_task(simulate_printing(printer_id, next_job_id))
#         else:
#             printer["status"] = PrinterStatus.IDLE
#             logger.info(f"[{printer_id}] Now idle")
            
#     except Exception as e:
#         job["status"] = JobStatus.FAILED
#         printer["status"] = PrinterStatus.IDLE
#         printer["current_job"] = None
        
#         # Send webhook: failed
#         await send_webhook(
#             job.get("webhook_url"),
#             job_id,
#             "failed",
#             job.get("progress_percent", 0),
#             printer_id,
#             f"Print job failed: {str(e)}"
#         )
        
#         logger.error(f"[{printer_id}] Job {job_id} failed: {e}")

# # ==================== API Endpoints ====================

# @app.on_event("startup")
# async def startup_event():
#     logger.info("🚀 Enhanced Printer Simulation API started")
#     logger.info("📊 Features: Multi-type printing, Consumable tracking, Auto-alerts")

# @app.get("/")
# def root():
#     return {
#         "message": "Enhanced Printer Simulation API v2.0",
#         "printers": len(PRINTERS),
#         "active_jobs": len([j for j in JOBS.values() if j["status"] in [JobStatus.PRINTING, JobStatus.QUEUED]]),
#         "features": [
#             "webhooks",
#             "real-time-updates",
#             "multi-type-printing",
#             "consumable-tracking",
#             "automated-alerts"
#         ]
#     }

# @app.get("/printers", response_model=List[PrinterInfo])
# def list_printers():
#     """Get all available printers and their status"""
#     result = []
#     for pid, printer in PRINTERS.items():
#         result.append(PrinterInfo(
#             printer_id=pid,
#             name=printer["name"],
#             supported_types=printer["supported_types"],
#             bw_speed=printer["bw_speed"],
#             color_speed=printer.get("color_speed"),
#             status=printer["status"],
#             current_job=printer["current_job"],
#             queue_length=len(printer["queue"]),
#             location=printer["location"],
#             consumables=printer["consumables"]
#         ))
#     return result

# @app.get("/printers/{printer_id}", response_model=PrinterInfo)
# def get_printer(printer_id: str):
#     """Get specific printer details"""
#     if printer_id not in PRINTERS:
#         logger.warning(f"Printer {printer_id} not found")
#         raise HTTPException(status_code=404, detail="Printer not found")
    
#     printer = PRINTERS[printer_id]
#     return PrinterInfo(
#         printer_id=printer_id,
#         name=printer["name"],
#         supported_types=printer["supported_types"],
#         bw_speed=printer["bw_speed"],
#         color_speed=printer.get("color_speed"),
#         status=printer["status"],
#         current_job=printer["current_job"],
#         queue_length=len(printer["queue"]),
#         location=printer["location"],
#         consumables=printer["consumables"]
#     )

# @app.post("/printers/{printer_id}/print")
# async def submit_print_job(printer_id: str, request: PrintRequest, background_tasks: BackgroundTasks):
#     """Submit a print job to a specific printer"""
#     if printer_id not in PRINTERS:
#         logger.warning(f"Attempt to print to non-existent printer: {printer_id}")
#         raise HTTPException(status_code=404, detail="Printer not found")
    
#     printer = PRINTERS[printer_id]
    
#     # Validate print type support
#     if request.print_type not in printer["supported_types"]:
#         logger.warning(f"{request.print_type} print attempted on incompatible printer {printer_id}")
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Printer does not support {request.print_type} printing. Supported: {printer['supported_types']}"
#         )
    
#     # Check consumable availability
#     consumables = printer["consumables"]
#     total_pages = request.pages * request.copies
    
#     if request.print_type == PrintType.THICK and consumables["thick_paper"] < total_pages:
#         raise HTTPException(status_code=400, detail="Insufficient thick paper")
#     elif request.print_type == PrintType.GLOSSY and consumables["glossy_paper"] < total_pages:
#         raise HTTPException(status_code=400, detail="Insufficient glossy paper")
#     elif request.print_type in [PrintType.BW, PrintType.COLOR] and consumables["paper"] < total_pages:
#         raise HTTPException(status_code=400, detail="Insufficient regular paper")
    
#     # Create job record
#     job_data = {
#         "job_id": request.job_id,
#         "printer_id": printer_id,
#         "status": JobStatus.QUEUED,
#         "pages": request.pages,
#         "copies": request.copies,
#         "print_type": request.print_type,
#         "priority": request.priority,
#         "file_url": request.file_url,
#         "webhook_url": request.webhook_url,
#         "started_at": None,
#         "completed_at": None,
#         "progress_percent": 0,
#         "queued_at": datetime.now()
#     }
    
#     JOBS[request.job_id] = job_data
    
#     logger.info(f"Job {request.job_id} submitted to {printer_id} - Type: {request.print_type}")
    
#     # If printer is idle, start immediately
#     if printer["status"] == PrinterStatus.IDLE:
#         background_tasks.add_task(simulate_printing, printer_id, request.job_id)
#     else:
#         # Add to queue
#         printer["queue"].append(request.job_id)
#         job_data["status"] = JobStatus.QUEUED
#         logger.info(f"Job {request.job_id} queued (position {len(printer['queue'])})")
    
#     return {
#         "message": "Job submitted successfully",
#         "job_id": request.job_id,
#         "printer_id": printer_id,
#         "print_type": request.print_type,
#         "status": job_data["status"],
#         "queue_position": len(printer["queue"]) if job_data["status"] == JobStatus.QUEUED else 0,
#         "webhook_enabled": bool(request.webhook_url)
#     }

# @app.get("/jobs/{job_id}", response_model=JobInfo)
# def get_job_status(job_id: str):
#     """Get status of a specific print job"""
#     if job_id not in JOBS:
#         raise HTTPException(status_code=404, detail="Job not found")
    
#     job = JOBS[job_id]
#     return JobInfo(
#         job_id=job["job_id"],
#         printer_id=job["printer_id"],
#         status=job["status"],
#         pages=job["pages"],
#         copies=job["copies"],
#         print_type=job["print_type"],
#         started_at=job["started_at"],
#         completed_at=job["completed_at"],
#         progress_percent=job["progress_percent"]
#     )

# @app.get("/jobs")
# def list_all_jobs():
#     """List all jobs"""
#     return {
#         "total_jobs": len(JOBS),
#         "jobs": list(JOBS.values())
#     }

# @app.post("/printers/{printer_id}/refill")
# async def manual_refill(printer_id: str):
#     """Manually refill all consumables for a printer"""
#     if printer_id not in PRINTERS:
#         raise HTTPException(status_code=404, detail="Printer not found")
    
#     printer = PRINTERS[printer_id]
#     consumables = printer["consumables"]
    
#     # Refill all consumables
#     consumables["paper"] = 2500
#     if consumables["toner_bw"] is not None:
#         consumables["toner_bw"] = 100
#     if consumables["ink_black"] is not None:
#         consumables["ink_black"] = 100
#         consumables["ink_cyan"] = 100
#         consumables["ink_magenta"] = 100
#         consumables["ink_yellow"] = 100
#     if PrintType.THICK in printer["supported_types"]:
#         consumables["thick_paper"] = 200
#     if PrintType.GLOSSY in printer["supported_types"]:
#         consumables["glossy_paper"] = 150
    
#     logger.info(f"✅ Manual refill completed for {printer_id}")
    
#     return {
#         "message": f"All consumables refilled for {printer_id}",
#         "consumables": consumables
#     }

# @app.delete("/jobs/{job_id}")
# def cancel_job(job_id: str):
#     """Cancel a queued job"""
#     if job_id not in JOBS:
#         raise HTTPException(status_code=404, detail="Job not found")
    
#     job = JOBS[job_id]
#     if job["status"] == JobStatus.PRINTING:
#         raise HTTPException(status_code=400, detail="Cannot cancel job that is already printing")
    
#     printer_id = job["printer_id"]
#     if job_id in PRINTERS[printer_id]["queue"]:
#         PRINTERS[printer_id]["queue"].remove(job_id)
    
#     job["status"] = JobStatus.FAILED
#     logger.info(f"Job {job_id} cancelled")
#     return {"message": f"Job {job_id} cancelled"}

# @app.post("/reset")
# def reset_simulation():
#     """Reset all printers and jobs"""
#     global JOBS
#     JOBS = {}
    
#     for printer in PRINTERS.values():
#         printer["status"] = PrinterStatus.IDLE
#         printer["current_job"] = None
#         printer["queue"] = []
    
#     logger.info("Simulation reset")
#     return {"message": "Simulation reset successfully"}

# @app.get("/stats")
# def get_statistics():
#     """Get overall system statistics"""
#     total_jobs = len(JOBS)
#     completed_jobs = len([j for j in JOBS.values() if j["status"] == JobStatus.COMPLETED])
#     printing_jobs = len([j for j in JOBS.values() if j["status"] == JobStatus.PRINTING])
#     queued_jobs = len([j for j in JOBS.values() if j["status"] == JobStatus.QUEUED])
    
#     idle_printers = len([p for p in PRINTERS.values() if p["status"] == PrinterStatus.IDLE])
#     busy_printers = len([p for p in PRINTERS.values() if p["status"] == PrinterStatus.BUSY])
    
#     # Count printers by capability
#     bw_only = len([p for p in PRINTERS.values() if p["supported_types"] == [PrintType.BW]])
#     color_capable = len([p for p in PRINTERS.values() if PrintType.COLOR in p["supported_types"]])
#     multi_function = len([p for p in PRINTERS.values() if len(p["supported_types"]) >= 3])
    
#     return {
#         "printers": {
#             "total": len(PRINTERS),
#             "idle": idle_printers,
#             "busy": busy_printers,
#             "bw_only": bw_only,
#             "color_capable": color_capable,
#             "multi_function": multi_function
#         },
#         "jobs": {
#             "total": total_jobs,
#             "completed": completed_jobs,
#             "printing": printing_jobs,
#             "queued": queued_jobs,
#             "failed": len([j for j in JOBS.values() if j["status"] == JobStatus.FAILED])
#         },
#         "consumables_summary": {
#             printer_id: {
#                 "paper": printer["consumables"]["paper"],
#                 "toner_bw": printer["consumables"]["toner_bw"],
#                 "ink_levels": {
#                     "black": printer["consumables"]["ink_black"],
#                     "cyan": printer["consumables"]["ink_cyan"],
#                     "magenta": printer["consumables"]["ink_magenta"],
#                     "yellow": printer["consumables"]["ink_yellow"]
#                 } if printer["consumables"]["ink_black"] is not None else None,
#                 "special_paper": {
#                     "thick": printer["consumables"]["thick_paper"],
#                     "glossy": printer["consumables"]["glossy_paper"]
#                 }
#             }
#             for printer_id, printer in PRINTERS.items()
#         }
#     }

# # ==================== Backend Alert Receiver (For Testing) ====================

# @app.post("/api/alerts/printer")
# async def receive_printer_alert(alert: AlertPayload):
#     """
#     Backend endpoint to receive printer alerts
#     This simulates the backend receiving alerts from the printer system
#     """
#     logger.info(f"🔔 BACKEND RECEIVED ALERT: {alert.alert_code} from {alert.printer_id}")
#     logger.info(f"   Description: {alert.description}")
#     logger.info(f"   Severity: {alert.severity}")
#     logger.info(f"   Action: {alert.action_taken}")
    
#     # In a real system, you would:
#     # 1. Store alert in database
#     # 2. Notify administrators
#     # 3. Trigger workflows
#     # 4. Update dashboards
    
#     return {
#         "status": "received",
#         "alert_id": str(uuid.uuid4()),
#         "timestamp": datetime.now(),
#         "message": f"Alert {alert.alert_code} received and processed"
#     }

# @app.get("/api/alerts/history")
# def get_alert_history():
#     """Get alert history (placeholder for real implementation)"""
#     return {
#         "message": "Alert history endpoint",
#         "note": "In production, this would return stored alerts from database"
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)
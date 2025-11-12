"""
Printer Simulation FastAPI Server
Simulates 6 printers (4 BW, 2 Color) with realistic print timing
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

# ==================== Logging Setup ====================

logger = logging.getLogger("printer_simulation")
logger.setLevel(logging.INFO)

# File handler with rotation
file_handler = RotatingFileHandler(
    "logs/printer_simulation.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Create logs directory
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

# ==================== Simulation Logic ====================

async def simulate_printing(printer_id: str, job_id: str):
    """Simulate actual printing process with realistic timing"""
    printer = PRINTERS[printer_id]
    job = JOBS[job_id]
    
    try:
        logger.info(f"[{printer_id}] Starting job {job_id} - {job['pages']} pages, {job['copies']} copies, {job['color_mode']}")
        
        # Mark as printing
        job["status"] = JobStatus.PRINTING
        job["started_at"] = datetime.now()
        printer["status"] = PrinterStatus.BUSY
        printer["current_job"] = job_id
        
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
            job["progress_percent"] = int((i / steps) * 100)
            
            if i == 5:  # Log at 50% progress
                logger.info(f"[{printer_id}] Job {job_id} - 50% complete")
        
        # Mark as completed
        job["status"] = JobStatus.COMPLETED
        job["completed_at"] = datetime.now()
        job["progress_percent"] = 100
        printer["current_job"] = None
        
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
        logger.error(f"[{printer_id}] Job {job_id} failed: {e}")

# ==================== API Endpoints ====================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Printer Simulation API started")

@app.get("/")
def root():
    return {
        "message": "Printer Simulation API",
        "printers": len(PRINTERS),
        "active_jobs": len([j for j in JOBS.values() if j["status"] in [JobStatus.PRINTING, JobStatus.QUEUED]])
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
        "file_url": request.file_url,  # ✅ Store file URL
        "started_at": None,
        "completed_at": None,
        "progress_percent": 0,
        "queued_at": datetime.now()
    }
    
    JOBS[request.job_id] = job_data
    
    # Log with file info
    file_info = f" (with file: {request.file_url})" if request.file_url else ""
    logger.info(f"Job {request.job_id} submitted to {printer_id}{file_info}")
    
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
        "has_file": bool(request.file_url)
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
    """Get overall system statistics (not logged)"""
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
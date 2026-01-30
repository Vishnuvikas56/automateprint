from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import win32print
import win32api
import tempfile
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Print Supervisor Agent")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "printdb",
    "user": "postgres",
    "password": "your_password",
    "port": 5432
}

# Global state
is_monitoring = False
monitor_task = None

# Models
class PrintJob(BaseModel):
    id: int
    printer_id: str
    file_path: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

class PrinterInfo(BaseModel):
    name: str
    status: str
    jobs: int

class SupervisorStatus(BaseModel):
    is_monitoring: bool
    available_printers: List[str]
    pending_jobs: int

# Database connection manager
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

# Printer functions
def get_available_printers():
    """Get list of all available printers in the system"""
    try:
        printers = []
        printer_enum = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        for printer in printer_enum:
            printers.append(printer[2])  # printer[2] is the printer name
        return printers
    except Exception as e:
        logger.error(f"Error getting printers: {e}")
        return []

def get_printer_info(printer_name: str):
    """Get detailed information about a specific printer"""
    try:
        handle = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(handle, 2)
        win32print.ClosePrinter(handle)
        
        return {
            "name": printer_name,
            "status": "Ready" if printer_info["Status"] == 0 else "Busy",
            "jobs": printer_info["cJobs"]
        }
    except Exception as e:
        logger.error(f"Error getting printer info for {printer_name}: {e}")
        return None

def send_to_printer(printer_name: str, file_path: str):
    """Send a file to the specified printer"""
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Print the file using Windows API
        win32api.ShellExecute(
            0,
            "print",
            file_path,
            f'/d:"{printer_name}"',
            ".",
            0
        )
        logger.info(f"Successfully sent {file_path} to {printer_name}")
        return True
    except Exception as e:
        logger.error(f"Error printing to {printer_name}: {e}")
        return False

# Database operations
def get_pending_jobs():
    """Get all pending print jobs from the database"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, printer_id, file_path, status, created_at, completed_at
                FROM jobqueue
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """)
            return cursor.fetchall()

def update_job_status(job_id: int, status: str, error_message: Optional[str] = None):
    """Update the status of a print job"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if status == 'completed':
                cursor.execute("""
                    UPDATE jobqueue
                    SET status = %s, completed_at = NOW()
                    WHERE id = %s
                """, (status, job_id))
            elif status == 'failed':
                cursor.execute("""
                    UPDATE jobqueue
                    SET status = %s, error_message = %s
                    WHERE id = %s
                """, (status, error_message, job_id))
            else:
                cursor.execute("""
                    UPDATE jobqueue
                    SET status = %s
                    WHERE id = %s
                """, (status, job_id))

def update_job_processing(job_id: int):
    """Mark job as processing"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE jobqueue
                SET status = 'processing'
                WHERE id = %s
            """, (job_id,))

# Print job processor
async def process_print_jobs():
    """Main loop to process print jobs"""
    logger.info("Starting print job processor")
    
    while is_monitoring:
        try:
            # Get available printers
            available_printers = get_available_printers()
            logger.info(f"Available printers: {available_printers}")
            
            # Get pending jobs
            pending_jobs = get_pending_jobs()
            
            if pending_jobs:
                logger.info(f"Found {len(pending_jobs)} pending jobs")
            
            for job in pending_jobs:
                job_id = job['id']
                printer_id = job['printer_id']
                file_path = job['file_path']
                
                # Check if printer ID matches any available printer
                if printer_id not in available_printers:
                    logger.warning(f"Job {job_id}: Printer '{printer_id}' not found in system. Skipping.")
                    continue
                
                # Mark job as processing
                logger.info(f"Processing job {job_id} on printer {printer_id}")
                update_job_processing(job_id)
                
                # Send to printer
                success = send_to_printer(printer_id, file_path)
                
                if success:
                    update_job_status(job_id, 'completed')
                    logger.info(f"Job {job_id} completed successfully")
                else:
                    update_job_status(job_id, 'failed', 'Failed to send to printer')
                    logger.error(f"Job {job_id} failed")
                
                # Small delay between jobs
                await asyncio.sleep(2)
            
            # Wait before next iteration
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in process_print_jobs: {e}")
            await asyncio.sleep(10)

# API Endpoints
@app.get("/")
def read_root():
    return {
        "service": "Print Supervisor Agent",
        "status": "running",
        "monitoring": is_monitoring
    }

@app.get("/printers", response_model=List[str])
def list_printers():
    """Get list of all available printers"""
    printers = get_available_printers()
    return printers

@app.get("/printers/{printer_name}")
def get_printer_details(printer_name: str):
    """Get detailed information about a specific printer"""
    info = get_printer_info(printer_name)
    if info is None:
        raise HTTPException(status_code=404, detail="Printer not found")
    return info

@app.get("/jobs/pending")
def list_pending_jobs():
    """Get all pending print jobs"""
    try:
        jobs = get_pending_jobs()
        return {"count": len(jobs), "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=SupervisorStatus)
def get_supervisor_status():
    """Get the current status of the supervisor"""
    try:
        available_printers = get_available_printers()
        pending_jobs = get_pending_jobs()
        
        return SupervisorStatus(
            is_monitoring=is_monitoring,
            available_printers=available_printers,
            pending_jobs=len(pending_jobs)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitoring/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start the print job monitoring service"""
    global is_monitoring, monitor_task
    
    if is_monitoring:
        return {"message": "Monitoring is already running"}
    
    is_monitoring = True
    monitor_task = asyncio.create_task(process_print_jobs())
    
    logger.info("Print monitoring started")
    return {"message": "Print monitoring started successfully"}

@app.post("/monitoring/stop")
async def stop_monitoring():
    """Stop the print job monitoring service"""
    global is_monitoring, monitor_task
    
    if not is_monitoring:
        return {"message": "Monitoring is not running"}
    
    is_monitoring = False
    
    if monitor_task:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Print monitoring stopped")
    return {"message": "Print monitoring stopped successfully"}

@app.post("/jobs/{job_id}/retry")
def retry_job(job_id: int):
    """Manually retry a failed job"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM jobqueue WHERE id = %s
                """, (job_id,))
                job = cursor.fetchone()
                
                if not job:
                    raise HTTPException(status_code=404, detail="Job not found")
                
                if job['status'] not in ['failed', 'completed']:
                    raise HTTPException(status_code=400, detail="Job is not in a retryable state")
                
                cursor.execute("""
                    UPDATE jobqueue
                    SET status = 'pending', error_message = NULL
                    WHERE id = %s
                """, (job_id,))
        
        return {"message": f"Job {job_id} reset to pending"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Start monitoring on server startup"""
    global is_monitoring, monitor_task
    
    logger.info("Print Supervisor Agent starting up")
    
    # Automatically start monitoring
    is_monitoring = True
    monitor_task = asyncio.create_task(process_print_jobs())
    logger.info("Auto-started print monitoring")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    global is_monitoring, monitor_task
    
    logger.info("Print Supervisor Agent shutting down")
    
    is_monitoring = False
    if monitor_task:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
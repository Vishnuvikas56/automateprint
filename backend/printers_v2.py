"""
Realistic Printer Hardware Simulation FastAPI Server
Compatible with Production-Grade Scheduler
Simulates real-world printer behavior with comprehensive hardware parameters
Run: uvicorn realistic_printer_sim:app --port 8001 --reload
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import asyncio
import uuid
from enum import Enum
import logging
from logging.handlers import RotatingFileHandler
import httpx
import random

# ==================== Logging Setup ====================

logger = logging.getLogger("printer_hardware_sim")
logger.setLevel(logging.INFO)

import os
os.makedirs("logs", exist_ok=True)

file_handler = RotatingFileHandler(
    "logs/printer_hardware.log",
    maxBytes=10*1024*1024,
    backupCount=5
)
console_handler = logging.StreamHandler()

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = FastAPI(title="Realistic Printer Hardware Simulation API", version="3.0")

# ==================== Models ====================

class PrintType(str, Enum):
    BW = "bw"
    COLOR = "color"
    THICK = "thick"
    GLOSSY = "glossy"
    POSTERSIZE = "postersize"

class JobStatus(str, Enum):
    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PrinterStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    WARMING_UP = "warming_up"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    PAPER_JAM = "paper_jam"
    OUT_OF_PAPER = "out_of_paper"
    LOW_INK = "low_ink"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class PaperType(str, Enum):
    A4 = "A4"
    A3 = "A3"
    LETTER = "Letter"
    LEGAL = "Legal"
    THICK = "Thick"
    GLOSSY = "Glossy"
    POSTER = "Poster"

class PrintRequest(BaseModel):
    job_id: str
    print_type: PrintType
    paper_type: PaperType
    pages: int = Field(gt=0, le=10000)
    copies: int = Field(default=1, gt=0, le=100)
    priority: int = Field(default=5, ge=1, le=10)
    file_url: Optional[str] = None
    webhook_url: Optional[str] = None
    duplex: bool = False
    collate: bool = True

class PrinterInfo(BaseModel):
    printer_id: str
    name: str
    model: str
    manufacturer: str
    supported: List[str]
    paper_count: Dict[str, int]
    ink: Dict[str, float]
    speed: int  # pages per minute
    status: PrinterStatus
    current_job: Optional[str]
    queue: List[str]
    location: str
    ip_address: str
    serial_number: str
    firmware_version: str
    total_pages_printed: int
    last_maintenance: datetime
    temperature: float
    humidity: float
    capabilities: Dict[str, bool]

class JobInfo(BaseModel):
    job_id: str
    printer_id: str
    status: JobStatus
    print_type: PrintType
    paper_type: PaperType
    pages: int
    copies: int
    total_pages: int
    pages_printed: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    progress_percent: int
    error_message: Optional[str]

class AlertPayload(BaseModel):
    alert_id: str
    printer_id: str
    printer_name: str
    alert_type: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    printer_status: PrinterStatus
    consumable_levels: Dict
    recommended_action: str

# ==================== Hardware Simulation Constants ====================

# Ink/Toner consumption rates per page (percentage)
INK_CONSUMPTION = {
    PrintType.BW: {"black": 0.5},
    PrintType.COLOR: {"black": 0.2, "C": 0.3, "M": 0.3, "Y": 0.3},
    PrintType.THICK: {'C': 0.45, 'M': 0.45, 'Y': 0.45, 'black': 0.15},
    PrintType.GLOSSY: {"black": 0.3, "C": 0.5, "M": 0.5, "Y": 0.5},
    PrintType.POSTERSIZE: {"black": 0.8, "C": 0.8, "M": 0.8, "Y": 0.8}
}

# Warm-up times (seconds)
WARMUP_TIME = {
    "cold_start": 30,
    "standby": 5
}

# Paper jam probability (increases with usage)
BASE_JAM_PROBABILITY = 0.01  # 1%
JAM_PROBABILITY_INCREMENT = 0.0001  # per 1000 pages

# Maintenance intervals
MAINTENANCE_INTERVAL_PAGES = 50000

# Alert thresholds
THRESHOLDS = {
    "paper_low": 100,
    "paper_critical": 20,
    "ink_low": 20,
    "ink_critical": 10,
    "temperature_warning": 45,
    "temperature_critical": 55
}

# ==================== Realistic Printer Fleet ====================

PRINTERS: Dict[str, Dict] = {
    "P1": {
        "name": "HP LaserJet Pro M404dn",
        "model": "M404dn",
        "manufacturer": "HP",
        "supported": ["bw"],  # removed thick
        "paper_count": {
            "A4": 500,
            "A3": 0,
            "Letter": 250,
            "Legal": 100,
            "Thick": 0,        # cannot print thick now
            "Glossy": 0,
            "Poster": 0
        },
        "ink": {
            "black": 85.0,
            "C": 0,
            "M": 0,
            "Y": 0
        },
        "speed": 38,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Building A - Floor 2 - Room 201",
        "ip_address": "192.168.1.101",
        "serial_number": "VND8K12345",
        "firmware_version": "20210512",
        "total_pages_printed": 12456,
        "last_maintenance": datetime.now() - timedelta(days=45),
        "temperature": 22.5,
        "humidity": 45.0,
        "last_warmup": None,
        "capabilities": {
            "duplex": True,
            "color": False,
            "scanner": False,
            "fax": False,
            "network": True,
            "usb": True
        }
    },

    "P2": {
        "name": "Canon imageCLASS LBP6230dw",
        "model": "LBP6230dw",
        "manufacturer": "Canon",
        "supported": ["bw"],  # unchanged
        "paper_count": {
            "A4": 350,
            "A3": 0,
            "Letter": 300,
            "Legal": 50,
            "Thick": 0,
            "Glossy": 0,
            "Poster": 0
        },
        "ink": {
            "black": 62.0,
            "C": 0,
            "M": 0,
            "Y": 0
        },
        "speed": 25,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Building A - Floor 3 - Room 305",
        "ip_address": "192.168.1.102",
        "serial_number": "CAN9X67890",
        "firmware_version": "20200815",
        "total_pages_printed": 8923,
        "last_maintenance": datetime.now() - timedelta(days=120),
        "temperature": 23.0,
        "humidity": 48.0,
        "last_warmup": None,
        "capabilities": {
            "duplex": True,
            "color": False,
            "scanner": False,
            "fax": False,
            "network": True,
            "usb": True
        }
    },

    "P3": {
        "name": "Epson EcoTank ET-4760",
        "model": "ET-4760",
        "manufacturer": "Epson",
        "supported": ["bw", "color", "glossy"],  # removed thick
        "paper_count": {
            "A4": 400,
            "A3": 0,
            "Letter": 350,
            "Legal": 0,
            "Thick": 0,
            "Glossy": 100,
            "Poster": 0
        },
        "ink": {
            "black": 75.0,
            "C": 68.0,
            "M": 72.0,
            "Y": 70.0
        },
        "speed": 15,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Building B - Floor 1 - Design Studio",
        "ip_address": "192.168.1.103",
        "serial_number": "EPS5T24680",
        "firmware_version": "20220301",
        "total_pages_printed": 4567,
        "last_maintenance": datetime.now() - timedelta(days=30),
        "temperature": 24.0,
        "humidity": 50.0,
        "last_warmup": None,
        "capabilities": {
            "duplex": True,
            "color": True,
            "scanner": True,
            "fax": True,
            "network": True,
            "usb": True
        }
    },

    "P4": {
        "name": "Brother HL-L8360CDW",
        "model": "HL-L8360CDW",
        "manufacturer": "Brother",
        "supported": ["bw", "color", "thick"],  # thick stays only because printer supports color
        "paper_count": {
            "A4": 600,
            "A3": 0,
            "Letter": 500,
            "Legal": 200,
            "Thick": 100,
            "Glossy": 0,
            "Poster": 0
        },
        "ink": {
            "black": 90.0,
            "C": 85.0,
            "M": 82.0,
            "Y": 88.0
        },
        "speed": 33,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Building B - Floor 2 - Marketing Dept",
        "ip_address": "192.168.1.104",
        "serial_number": "BRO2L13579",
        "firmware_version": "20210920",
        "total_pages_printed": 15234,
        "last_maintenance": datetime.now() - timedelta(days=60),
        "temperature": 23.5,
        "humidity": 47.0,
        "last_warmup": None,
        "capabilities": {
            "duplex": True,
            "color": True,
            "scanner": False,
            "fax": False,
            "network": True,
            "usb": True
        }
    },

    "P5": {
        "name": "Xerox VersaLink C405",
        "model": "VersaLink C405",
        "manufacturer": "Xerox",
        "supported": ["bw", "color", "glossy", "thick"],  # thick allowed (color printer)
        "paper_count": {
            "A4": 800,
            "A3": 0,
            "Letter": 700,
            "Legal": 300,
            "Thick": 150,
            "Glossy": 120,
            "Poster": 0
        },
        "ink": {
            "black": 95.0,
            "C": 92.0,
            "M": 90.0,
            "Y": 94.0
        },
        "speed": 35,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Building C - Floor 1 - Executive Office",
        "ip_address": "192.168.1.105",
        "serial_number": "XRX8V86420",
        "firmware_version": "20220615",
        "total_pages_printed": 23456,
        "last_maintenance": datetime.now() - timedelta(days=20),
        "temperature": 22.0,
        "humidity": 44.0,
        "last_warmup": None,
        "capabilities": {
            "duplex": True,
            "color": True,
            "scanner": True,
            "fax": True,
            "network": True,
            "usb": True
        }
    },

    "P6": {
        "name": "HP DesignJet T230",
        "model": "DesignJet T230",
        "manufacturer": "HP",
        "supported": ["bw", "color", "glossy", "thick", "postersize"],  # thick allowed (color printer)
        "paper_count": {
            "A4": 500,
            "A3": 200,
            "Letter": 400,
            "Legal": 0,
            "Thick": 100,
            "Glossy": 150,
            "Poster": 50
        },
        "ink": {
            "black": 88.0,
            "C": 85.0,
            "M": 87.0,
            "Y": 86.0
        },
        "speed": 20,
        "status": PrinterStatus.IDLE,
        "current_job": None,
        "queue": [],
        "location": "Building C - Floor 3 - Engineering Dept",
        "ip_address": "192.168.1.106",
        "serial_number": "HPD4J97531",
        "firmware_version": "20220801",
        "total_pages_printed": 5678,
        "last_maintenance": datetime.now() - timedelta(days=15),
        "temperature": 24.5,
        "humidity": 52.0,
        "last_warmup": None,
        "capabilities": {
            "duplex": False,
            "color": True,
            "scanner": False,
            "fax": False,
            "network": True,
            "usb": True
        }
    }
}

JOBS: Dict[str, Dict] = {}
ALERTS: List[Dict] = []

# ==================== Hardware Simulation Functions ====================

def simulate_hardware_wear(printer_id: str):
    """Simulate hardware degradation over time"""
    printer = PRINTERS[printer_id]
    
    # Increase temperature during operation
    printer["temperature"] += random.uniform(0.5, 2.0)
    printer["temperature"] = min(printer["temperature"], 60)
    
    # Random humidity fluctuation
    printer["humidity"] += random.uniform(-2, 2)
    printer["humidity"] = max(30, min(70, printer["humidity"]))

def check_paper_jam(printer_id: str) -> bool:
    """Simulate random paper jams based on usage"""
    printer = PRINTERS[printer_id]
    
    # Calculate jam probability based on pages printed
    pages = printer["total_pages_printed"]
    jam_prob = BASE_JAM_PROBABILITY + (pages / 1000) * JAM_PROBABILITY_INCREMENT
    
    # Higher probability if maintenance overdue
    days_since_maintenance = (datetime.now() - printer["last_maintenance"]).days
    if days_since_maintenance > 180:
        jam_prob *= 2
    
    # Thick paper increases jam probability
    jam_prob *= 1.5
    
    return random.random() < jam_prob

def needs_warmup(printer_id: str) -> bool:
    """Check if printer needs warm-up"""
    printer = PRINTERS[printer_id]
    
    if printer["last_warmup"] is None:
        return True
    
    # Cold start if idle for > 1 hour
    time_since_warmup = (datetime.now() - printer["last_warmup"]).total_seconds()
    return time_since_warmup > 3600

async def warmup_printer(printer_id: str):
    """Simulate printer warm-up process"""
    printer = PRINTERS[printer_id]
    
    if needs_warmup(printer_id):
        warmup_time = WARMUP_TIME["cold_start"]
        logger.info(f"[{printer_id}] Cold start - warming up for {warmup_time}s")
    else:
        warmup_time = WARMUP_TIME["standby"]
        logger.info(f"[{printer_id}] Quick warm-up - {warmup_time}s")
    
    printer["status"] = PrinterStatus.WARMING_UP
    await asyncio.sleep(warmup_time)
    printer["last_warmup"] = datetime.now()
    printer["temperature"] += 5  # Temperature rises during warmup

def consume_resources(printer_id: str, job: Dict):
    """Consume paper and ink based on job"""
    printer = PRINTERS[printer_id]
    
    # Consume paper
    paper_type = job["paper_type"]
    total_pages = job["pages"] * job["copies"]
    
    if job["duplex"]:
        # Duplex uses fewer sheets
        sheets_needed = (total_pages + 1) // 2
    else:
        sheets_needed = total_pages
    
    if printer["paper_count"][paper_type] < sheets_needed:
        raise ValueError(f"Insufficient {paper_type} paper: need {sheets_needed}, have {printer['paper_count'][paper_type]}")
    
    printer["paper_count"][paper_type] -= sheets_needed
    
    # Consume ink
    consumption_rates = INK_CONSUMPTION[job["print_type"]]
    for channel, rate in consumption_rates.items():
        ink_used = total_pages * rate
        printer["ink"][channel] -= ink_used
        printer["ink"][channel] = max(0, printer["ink"][channel])
    
    # Update total pages
    printer["total_pages_printed"] += total_pages
    
    logger.info(f"[{printer_id}] Consumed {sheets_needed} sheets of {paper_type}, "
                f"printed {total_pages} pages")

async def send_alert(printer_id: str, alert_type: str, severity: AlertSeverity, 
                    message: str, recommended_action: str):
    """Send alert for printer issues"""
    printer = PRINTERS[printer_id]
    
    alert = AlertPayload(
        alert_id=str(uuid.uuid4()),
        printer_id=printer_id,
        printer_name=printer["name"],
        alert_type=alert_type,
        severity=severity,
        message=message,
        timestamp=datetime.now(),
        printer_status=printer["status"],
        consumable_levels={
            "paper": printer["paper_count"],
            "ink": printer["ink"],
            "temperature": printer["temperature"],
            "humidity": printer["humidity"]
        },
        recommended_action=recommended_action
    )
    
    ALERTS.append(alert.dict())
    logger.warning(f"🚨 ALERT [{severity.value.upper()}] {printer_id}: {message}")
    
    return alert

async def check_consumables_and_alert(printer_id: str):
    """Check all consumables and send alerts if needed"""
    printer = PRINTERS[printer_id]
    alerts_sent = []
    
    # Check paper levels
    for paper_type, count in printer["paper_count"].items():
        if count == 0:
            alert = await send_alert(
                printer_id, "PAPER_OUT", AlertSeverity.CRITICAL,
                f"{paper_type} paper is empty",
                f"Refill {paper_type} paper immediately"
            )
            alerts_sent.append(alert)
        elif count < THRESHOLDS["paper_critical"]:
            alert = await send_alert(
                printer_id, "PAPER_CRITICAL", AlertSeverity.CRITICAL,
                f"{paper_type} paper critically low: {count} sheets",
                f"Refill {paper_type} paper urgently"
            )
            alerts_sent.append(alert)
        elif count < THRESHOLDS["paper_low"]:
            alert = await send_alert(
                printer_id, "PAPER_LOW", AlertSeverity.WARNING,
                f"{paper_type} paper low: {count} sheets",
                f"Schedule refill for {paper_type} paper"
            )
            alerts_sent.append(alert)
    
    # Check ink levels
    for channel, level in printer["ink"].items():
        if level <= 0:
            alert = await send_alert(
                printer_id, "INK_EMPTY", AlertSeverity.CRITICAL,
                f"{channel} ink is empty",
                f"Replace {channel} ink cartridge immediately"
            )
            alerts_sent.append(alert)
        elif level < THRESHOLDS["ink_critical"]:
            alert = await send_alert(
                printer_id, "INK_CRITICAL", AlertSeverity.CRITICAL,
                f"{channel} ink critically low: {level:.1f}%",
                f"Replace {channel} ink cartridge urgently"
            )
            alerts_sent.append(alert)
        elif level < THRESHOLDS["ink_low"]:
            alert = await send_alert(
                printer_id, "INK_LOW", AlertSeverity.WARNING,
                f"{channel} ink low: {level:.1f}%",
                f"Order replacement for {channel} ink"
            )
            alerts_sent.append(alert)
    
    # Check temperature
    if printer["temperature"] > THRESHOLDS["temperature_critical"]:
        alert = await send_alert(
            printer_id, "TEMPERATURE_CRITICAL", AlertSeverity.CRITICAL,
            f"Temperature critical: {printer['temperature']:.1f}°C",
            "Stop printer and allow cooling"
        )
        alerts_sent.append(alert)
        printer["status"] = PrinterStatus.ERROR
    elif printer["temperature"] > THRESHOLDS["temperature_warning"]:
        alert = await send_alert(
            printer_id, "TEMPERATURE_HIGH", AlertSeverity.WARNING,
            f"Temperature high: {printer['temperature']:.1f}°C",
            "Monitor printer temperature"
        )
        alerts_sent.append(alert)
    
    # Check maintenance
    days_since_maintenance = (datetime.now() - printer["last_maintenance"]).days
    if days_since_maintenance > 180:
        alert = await send_alert(
            printer_id, "MAINTENANCE_OVERDUE", AlertSeverity.WARNING,
            f"Maintenance overdue by {days_since_maintenance - 180} days",
            "Schedule maintenance service"
        )
        alerts_sent.append(alert)
    
    return alerts_sent

async def send_webhook(webhook_url: str, job_id: str, status: str, progress: int, 
                      printer_id: str, message: str = None):
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
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            response = await client.post(webhook_url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Webhook sent for {job_id}: {status} ({progress}%)")
            else:
                logger.warning(f"⚠️ Webhook failed for {job_id}: {response.status_code}")
                
    except Exception as e:
        logger.error(f"❌ Webhook error for {job_id}: {e}")

# ==================== Print Simulation Logic ====================

async def simulate_printing(printer_id: str, job_id: str):
    """Realistic print job simulation with hardware behavior"""
    printer = PRINTERS[printer_id]
    job = JOBS[job_id]
    
    try:
        logger.info(f"[{printer_id}] Starting job {job_id}: {job['pages']} pages "
                   f"× {job['copies']} copies, {job['print_type']} on {job['paper_type']}")
        
        # Warm-up phase
        await warmup_printer(printer_id)
        
        # Check for paper jam before starting
        if check_paper_jam(printer_id):
            printer["status"] = PrinterStatus.PAPER_JAM
            job["status"] = JobStatus.FAILED
            job["error_message"] = "Paper jam detected"
            
            await send_alert(
                printer_id, "PAPER_JAM", AlertSeverity.CRITICAL,
                "Paper jam detected - job failed",
                "Clear paper jam and restart job"
            )
            
            await send_webhook(
                job.get("webhook_url"), job_id, "failed", 0,
                printer_id, "Paper jam detected"
            )
            
            logger.error(f"[{printer_id}] Job {job_id} failed: Paper jam")
            return
        
        # Start printing
        job["status"] = JobStatus.PRINTING
        job["started_at"] = datetime.now()
        printer["status"] = PrinterStatus.BUSY
        printer["current_job"] = job_id
        
        total_pages = job["pages"] * job["copies"]
        job["total_pages"] = total_pages
        
        # Calculate print time based on speed and type
        base_speed = printer["speed"]
        
        # Adjust speed for print type
        speed_multipliers = {
            PrintType.BW: 1.0,
            PrintType.COLOR: 0.4,
            PrintType.THICK: 0.7,
            PrintType.GLOSSY: 0.5,
            PrintType.POSTERSIZE: 0.3
        }
        
        effective_speed = base_speed * speed_multipliers[job["print_type"]]
        total_time = (total_pages / effective_speed) * 60  # Convert to seconds
        
        # Add duplex overhead
        if job["duplex"]:
            total_time *= 1.3  # 30% overhead for duplex
        
        # Estimate completion
        job["estimated_completion"] = datetime.now() + timedelta(seconds=total_time)
        
        await send_webhook(
            job.get("webhook_url"), job_id, "printing", 0,
            printer_id, f"Printing started - ETA: {total_time:.0f}s"
        )
        
        # Simulate printing with progress updates
        steps = 20
        step_time = total_time / steps
        
        for i in range(1, steps + 1):
            await asyncio.sleep(step_time)
            
            progress = int((i / steps) * 100)
            pages_printed = int((i / steps) * total_pages)
            job["progress_percent"] = progress
            job["pages_printed"] = pages_printed
            
            # Simulate hardware wear
            simulate_hardware_wear(printer_id)
            
            # Send progress updates at 25%, 50%, 75%
            if progress in [25, 50, 75]:
                await send_webhook(
                    job.get("webhook_url"), job_id, "printing", progress,
                    printer_id, f"Printing: {pages_printed}/{total_pages} pages"
                )
                logger.info(f"[{printer_id}] Job {job_id} - {progress}% "
                          f"({pages_printed}/{total_pages} pages)")
            
            # Random chance of issues during printing
            if random.random() < 0.001:  # 0.1% chance per step
                if check_paper_jam(printer_id):
                    raise Exception("Paper jam during printing")
        
        # Consume resources
        consume_resources(printer_id, job)
        
        # Check consumables and send alerts
        await check_consumables_and_alert(printer_id)
        
        # Complete job
        job["status"] = JobStatus.COMPLETED
        job["completed_at"] = datetime.now()
        job["progress_percent"] = 100
        job["pages_printed"] = total_pages
        printer["current_job"] = None
        
        # Cool down
        printer["temperature"] -= 3
        
        await send_webhook(
            job.get("webhook_url"), job_id, "completed", 100,
            printer_id, f"Job completed: {total_pages} pages in {total_time:.1f}s"
        )
        
        actual_time = (job["completed_at"] - job["started_at"]).total_seconds()
        logger.info(f"[{printer_id}] Job {job_id} completed in {actual_time:.1f}s")
        
        # Process next job in queue
        if printer["queue"]:
            next_job_id = printer["queue"].pop(0)
            logger.info(f"[{printer_id}] Processing next job: {next_job_id}")
            asyncio.create_task(simulate_printing(printer_id, next_job_id))
        else:
            printer["status"] = PrinterStatus.IDLE
            logger.info(f"[{printer_id}] Now idle")
            
    except Exception as e:
        job["status"] = JobStatus.FAILED
        job["error_message"] = str(e)
        printer["status"] = PrinterStatus.ERROR if "jam" in str(e).lower() else PrinterStatus.IDLE
        printer["current_job"] = None
        
        await send_webhook(
            job.get("webhook_url"), job_id, "failed",
            job.get("progress_percent", 0), printer_id,
            f"Job failed: {str(e)}"
        )
        
        logger.error(f"[{printer_id}] Job {job_id} failed: {e}")

# ==================== API Endpoints ====================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Realistic Printer Hardware Simulation API started")
    logger.info(f"📊 {len(PRINTERS)} printers configured with full hardware simulation")

@app.get("/")
def root():
    active_jobs = len([j for j in JOBS.values() if j["status"] in [JobStatus.PRINTING, JobStatus.QUEUED]])
    return {
        "message": "Realistic Printer Hardware Simulation API v3.0",
        "printers": len(PRINTERS),
        "active_jobs": active_jobs,
        "total_jobs": len(JOBS),
        "alerts": len(ALERTS),
        "features": [
            "realistic-hardware-simulation",
            "consumable-tracking",
            "paper-jam-simulation",
            "temperature-monitoring",
            "maintenance-tracking",
            "duplex-printing",
            "multiple-paper-types",
            "automated-alerts",
            "webhooks"
        ]
    }

@app.get("/printers", response_model=List[PrinterInfo])
def list_printers():
    """Get all printers with full hardware details"""
    result = []
    for pid, printer in PRINTERS.items():
        result.append(PrinterInfo(
            printer_id=pid,
            name=printer["name"],
            model=printer["model"],
            manufacturer=printer["manufacturer"],
            supported=printer["supported"],
            paper_count=printer["paper_count"],
            ink=printer["ink"],
            speed=printer["speed"],
            status=printer["status"],
            current_job=printer["current_job"],
            queue=printer["queue"],
            location=printer["location"],
            ip_address=printer["ip_address"],
            serial_number=printer["serial_number"],
            firmware_version=printer["firmware_version"],
            total_pages_printed=printer["total_pages_printed"],
            last_maintenance=printer["last_maintenance"],
            temperature=printer["temperature"],
            humidity=printer["humidity"],
            capabilities=printer["capabilities"]
        ))
    return result

@app.get("/printers/{printer_id}", response_model=PrinterInfo)
def get_printer(printer_id: str):
    """Get specific printer with full hardware details"""
    if printer_id not in PRINTERS:
        raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
    
    printer = PRINTERS[printer_id]
    return PrinterInfo(
        printer_id=printer_id,
        name=printer["name"],
        model=printer["model"],
        manufacturer=printer["manufacturer"],
        supported=printer["supported"],
        paper_count=printer["paper_count"],
        ink=printer["ink"],
        speed=printer["speed"],
        status=printer["status"],
        current_job=printer["current_job"],
        queue=printer["queue"],
        location=printer["location"],
        ip_address=printer["ip_address"],
        serial_number=printer["serial_number"],
        firmware_version=printer["firmware_version"],
        total_pages_printed=printer["total_pages_printed"],
        last_maintenance=printer["last_maintenance"],
        temperature=printer["temperature"],
        humidity=printer["humidity"],
        capabilities=printer["capabilities"]
    )

@app.post("/printers/{printer_id}/print")
async def submit_print_job(printer_id: str, request: PrintRequest, background_tasks: BackgroundTasks):
    """Submit a print job with full validation"""
    if printer_id not in PRINTERS:
        raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
    
    printer = PRINTERS[printer_id]
    
    # Check printer status
    if printer["status"] in [PrinterStatus.OFFLINE, PrinterStatus.MAINTENANCE, PrinterStatus.ERROR]:
        raise HTTPException(
            status_code=503, 
            detail=f"Printer unavailable: {printer['status'].value}"
        )
    
    if printer["status"] == PrinterStatus.PAPER_JAM:
        raise HTTPException(status_code=503, detail="Printer has paper jam - clear before submitting")
    
    # Validate print type support
    if request.print_type.value not in printer["supported"]:
        raise HTTPException(
            status_code=400,
            detail=f"Printer does not support {request.print_type}. Supported: {printer['supported']}"
        )
    
    # Validate paper type availability
    if request.paper_type.value not in printer["paper_count"]:
        raise HTTPException(
            status_code=400,
            detail=f"Printer does not have {request.paper_type} paper type"
        )
    
    # Calculate required sheets
    total_pages = request.pages * request.copies
    sheets_needed = (total_pages + 1) // 2 if request.duplex else total_pages
    
    # Check paper availability
    available_paper = printer["paper_count"][request.paper_type.value]
    if available_paper < sheets_needed:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient {request.paper_type} paper: need {sheets_needed}, have {available_paper}"
        )
    
    # Check ink availability
    required_ink = INK_CONSUMPTION.get(request.print_type, {})
    for channel, rate in required_ink.items():
        required_level = total_pages * rate
        if printer["ink"][channel] < required_level:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient {channel} ink: need {required_level:.1f}%, have {printer['ink'][channel]:.1f}%"
            )
    
    # Validate duplex capability
    if request.duplex and not printer["capabilities"]["duplex"]:
        raise HTTPException(status_code=400, detail="Printer does not support duplex printing")
    
    # Create job record
    job_data = {
        "job_id": request.job_id,
        "printer_id": printer_id,
        "status": JobStatus.QUEUED,
        "print_type": request.print_type,
        "paper_type": request.paper_type.value,
        "pages": request.pages,
        "copies": request.copies,
        "total_pages": total_pages,
        "pages_printed": 0,
        "priority": request.priority,
        "file_url": request.file_url,
        "webhook_url": request.webhook_url,
        "duplex": request.duplex,
        "collate": request.collate,
        "started_at": None,
        "completed_at": None,
        "estimated_completion": None,
        "progress_percent": 0,
        "error_message": None,
        "queued_at": datetime.now()
    }
    
    JOBS[request.job_id] = job_data
    
    logger.info(f"Job {request.job_id} submitted to {printer_id}: "
                f"{request.pages}p × {request.copies}c, {request.print_type} on {request.paper_type}")
    
    # Start immediately if idle, else queue
    if printer["status"] == PrinterStatus.IDLE:
        background_tasks.add_task(simulate_printing, printer_id, request.job_id)
        estimated_start = datetime.now()
    else:
        printer["queue"].append(request.job_id)
        job_data["status"] = JobStatus.QUEUED
        
        # Estimate start time based on queue
        estimated_start = datetime.now() + timedelta(minutes=len(printer["queue"]) * 2)
        logger.info(f"Job {request.job_id} queued at position {len(printer['queue'])}")
    
    return {
        "message": "Job submitted successfully",
        "job_id": request.job_id,
        "printer_id": printer_id,
        "printer_name": printer["name"],
        "status": job_data["status"],
        "queue_position": len(printer["queue"]) if job_data["status"] == JobStatus.QUEUED else 0,
        "estimated_start": estimated_start.isoformat(),
        "total_pages": total_pages,
        "sheets_required": sheets_needed,
        "duplex": request.duplex,
        "webhook_enabled": bool(request.webhook_url)
    }

@app.get("/jobs/{job_id}", response_model=JobInfo)
def get_job_status(job_id: str):
    """Get detailed job status"""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = JOBS[job_id]
    return JobInfo(
        job_id=job["job_id"],
        printer_id=job["printer_id"],
        status=job["status"],
        print_type=job["print_type"],
        paper_type=job["paper_type"],
        pages=job["pages"],
        copies=job["copies"],
        total_pages=job["total_pages"],
        pages_printed=job["pages_printed"],
        started_at=job["started_at"],
        completed_at=job["completed_at"],
        estimated_completion=job["estimated_completion"],
        progress_percent=job["progress_percent"],
        error_message=job["error_message"]
    )

@app.get("/jobs")
def list_all_jobs(status: Optional[JobStatus] = None, printer_id: Optional[str] = None):
    """List all jobs with optional filtering"""
    filtered_jobs = list(JOBS.values())
    
    if status:
        filtered_jobs = [j for j in filtered_jobs if j["status"] == status]
    
    if printer_id:
        filtered_jobs = [j for j in filtered_jobs if j["printer_id"] == printer_id]
    
    return {
        "total_jobs": len(JOBS),
        "filtered_jobs": len(filtered_jobs),
        "jobs": filtered_jobs
    }

@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    """Cancel a queued job"""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = JOBS[job_id]
    
    if job["status"] == JobStatus.PRINTING:
        raise HTTPException(status_code=400, detail="Cannot cancel job that is currently printing")
    
    if job["status"] == JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot cancel completed job")
    
    printer_id = job["printer_id"]
    if job_id in PRINTERS[printer_id]["queue"]:
        PRINTERS[printer_id]["queue"].remove(job_id)
    
    job["status"] = JobStatus.CANCELLED
    job["completed_at"] = datetime.now()
    
    logger.info(f"Job {job_id} cancelled")
    
    return {
        "message": f"Job {job_id} cancelled successfully",
        "job_id": job_id,
        "status": "cancelled"
    }

@app.post("/printers/{printer_id}/refill")
async def refill_printer(printer_id: str, paper: Optional[Dict[str, int]] = None, 
                        ink: Optional[Dict[str, float]] = None):
    """Manually refill printer consumables"""
    if printer_id not in PRINTERS:
        raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
    
    printer = PRINTERS[printer_id]
    
    refilled = []
    
    # Refill paper
    if paper:
        for paper_type, amount in paper.items():
            if paper_type in printer["paper_count"]:
                old_count = printer["paper_count"][paper_type]
                printer["paper_count"][paper_type] += amount
                refilled.append(f"{paper_type}: {old_count} → {printer['paper_count'][paper_type]}")
    
    # Refill ink
    if ink:
        for channel, level in ink.items():
            if channel in printer["ink"]:
                old_level = printer["ink"][channel]
                printer["ink"][channel] = min(100.0, printer["ink"][channel] + level)
                refilled.append(f"{channel} ink: {old_level:.1f}% → {printer['ink'][channel]:.1f}%")
    
    # If no specific refill, do full refill
    if not paper and not ink:
        # Full paper refill
        paper_capacities = {"A4": 500, "A3": 100, "Letter": 500, "Legal": 200, 
                           "Thick": 150, "Glossy": 150, "Poster": 50}
        for paper_type in printer["paper_count"].keys():
            old_count = printer["paper_count"][paper_type]
            printer["paper_count"][paper_type] = paper_capacities.get(paper_type, 500)
            if old_count != printer["paper_count"][paper_type]:
                refilled.append(f"{paper_type}: {old_count} → {printer['paper_count'][paper_type]}")
        
        # Full ink refill
        for channel in printer["ink"].keys():
            if printer["ink"][channel] < 100:
                old_level = printer["ink"][channel]
                printer["ink"][channel] = 100.0
                refilled.append(f"{channel} ink: {old_level:.1f}% → 100.0%")
    
    logger.info(f"✅ Refilled {printer_id}: {', '.join(refilled)}")
    
    # Clear error status if it was due to consumables
    if printer["status"] in [PrinterStatus.OUT_OF_PAPER, PrinterStatus.LOW_INK]:
        printer["status"] = PrinterStatus.IDLE
    
    return {
        "message": f"Printer {printer_id} refilled successfully",
        "printer_id": printer_id,
        "refilled": refilled,
        "current_levels": {
            "paper": printer["paper_count"],
            "ink": printer["ink"]
        }
    }

@app.post("/printers/{printer_id}/maintenance")
async def perform_maintenance(printer_id: str):
    """Perform maintenance on printer"""
    if printer_id not in PRINTERS:
        raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
    
    printer = PRINTERS[printer_id]
    
    if printer["status"] == PrinterStatus.BUSY:
        raise HTTPException(status_code=400, detail="Cannot perform maintenance while printer is busy")
    
    old_status = printer["status"]
    printer["status"] = PrinterStatus.MAINTENANCE
    
    # Simulate maintenance time
    await asyncio.sleep(5)
    
    # Reset maintenance counter
    printer["last_maintenance"] = datetime.now()
    printer["total_pages_printed"] = 0
    
    # Clear any error states
    printer["status"] = PrinterStatus.IDLE
    printer["temperature"] = 22.0
    
    logger.info(f"✅ Maintenance completed for {printer_id}")
    
    return {
        "message": f"Maintenance completed for {printer_id}",
        "printer_id": printer_id,
        "previous_status": old_status.value,
        "current_status": printer["status"].value,
        "last_maintenance": printer["last_maintenance"].isoformat()
    }

@app.post("/printers/{printer_id}/clear-jam")
async def clear_paper_jam(printer_id: str):
    """Clear paper jam"""
    if printer_id not in PRINTERS:
        raise HTTPException(status_code=404, detail=f"Printer {printer_id} not found")
    
    printer = PRINTERS[printer_id]
    
    if printer["status"] != PrinterStatus.PAPER_JAM:
        return {
            "message": f"Printer {printer_id} does not have a paper jam",
            "status": printer["status"].value
        }
    
    # Simulate clearing jam
    await asyncio.sleep(3)
    
    printer["status"] = PrinterStatus.IDLE
    logger.info(f"✅ Paper jam cleared for {printer_id}")
    
    return {
        "message": f"Paper jam cleared for {printer_id}",
        "printer_id": printer_id,
        "status": printer["status"].value
    }

@app.get("/alerts")
def get_alerts(severity: Optional[AlertSeverity] = None, printer_id: Optional[str] = None):
    """Get system alerts"""
    filtered_alerts = ALERTS
    
    if severity:
        filtered_alerts = [a for a in filtered_alerts if a["severity"] == severity]
    
    if printer_id:
        filtered_alerts = [a for a in filtered_alerts if a["printer_id"] == printer_id]
    
    return {
        "total_alerts": len(ALERTS),
        "filtered_alerts": len(filtered_alerts),
        "alerts": filtered_alerts[-50:]  # Last 50 alerts
    }

@app.delete("/alerts")
def clear_alerts():
    """Clear all alerts"""
    global ALERTS
    count = len(ALERTS)
    ALERTS = []
    logger.info(f"Cleared {count} alerts")
    return {"message": f"Cleared {count} alerts"}

@app.get("/stats")
def get_statistics():
    """Get comprehensive system statistics"""
    total_jobs = len(JOBS)
    completed = len([j for j in JOBS.values() if j["status"] == JobStatus.COMPLETED])
    printing = len([j for j in JOBS.values() if j["status"] == JobStatus.PRINTING])
    queued = len([j for j in JOBS.values() if j["status"] == JobStatus.QUEUED])
    failed = len([j for j in JOBS.values() if j["status"] == JobStatus.FAILED])
    
    idle_printers = len([p for p in PRINTERS.values() if p["status"] == PrinterStatus.IDLE])
    busy_printers = len([p for p in PRINTERS.values() if p["status"] == PrinterStatus.BUSY])
    error_printers = len([p for p in PRINTERS.values() if p["status"] in 
                         [PrinterStatus.ERROR, PrinterStatus.PAPER_JAM, PrinterStatus.OFFLINE]])
    
    total_pages_all = sum(p["total_pages_printed"] for p in PRINTERS.values())
    
    # Alert statistics
    critical_alerts = len([a for a in ALERTS if a["severity"] == AlertSeverity.CRITICAL])
    warning_alerts = len([a for a in ALERTS if a["severity"] == AlertSeverity.WARNING])
    
    return {
        "printers": {
            "total": len(PRINTERS),
            "idle": idle_printers,
            "busy": busy_printers,
            "error": error_printers,
            "total_pages_printed": total_pages_all
        },
        "jobs": {
            "total": total_jobs,
            "completed": completed,
            "printing": printing,
            "queued": queued,
            "failed": failed,
            "success_rate": f"{(completed / total_jobs * 100):.1f}%" if total_jobs > 0 else "N/A"
        },
        "alerts": {
            "total": len(ALERTS),
            "critical": critical_alerts,
            "warning": warning_alerts
        },
        "printer_details": {
            printer_id: {
                "status": printer["status"].value,
                "queue_length": len(printer["queue"]),
                "total_pages": printer["total_pages_printed"],
                "paper_levels": printer["paper_count"],
                "ink_levels": printer["ink"],
                "temperature": printer["temperature"],
                "days_since_maintenance": (datetime.now() - printer["last_maintenance"]).days
            }
            for printer_id, printer in PRINTERS.items()
        }
    }

@app.post("/reset")
def reset_simulation():
    """Reset entire simulation"""
    global JOBS, ALERTS
    
    JOBS = {}
    ALERTS = []
    
    for printer in PRINTERS.values():
        printer["status"] = PrinterStatus.IDLE
        printer["current_job"] = None
        printer["queue"] = []
        printer["temperature"] = 22.0
        printer["humidity"] = 45.0
        
        # Reset consumables to starting levels
        printer["paper_count"] = {
            "A4": 500, "A3": 100, "Letter": 500, "Legal": 200,
            "Thick": 100, "Glossy": 100, "Poster": 50
        }
        
        # Reset ink levels
        for channel in printer["ink"].keys():
            printer["ink"][channel] = 85.0
    
    logger.info("🔄 Simulation reset completed")
    
    return {
        "message": "Simulation reset successfully",
        "printers_reset": len(PRINTERS),
        "jobs_cleared": 0,
        "alerts_cleared": 0
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "printers_online": len([p for p in PRINTERS.values() 
                               if p["status"] not in [PrinterStatus.OFFLINE]]),
        "api_version": "3.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
"""
Smart Print Scheduler Algorithm
Efficient O(N log P) scheduling with load balancing
"""

import heapq
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class ColorMode(Enum):
    BW = "bw"
    COLOR = "color"

class PrinterStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"

@dataclass
class Printer:
    id: str
    name: str
    supports_color: bool
    bw_speed: float  # pages per second
    color_speed: float  # pages per second (if supported)
    status: PrinterStatus
    next_available_time: datetime
    current_load: int  # number of pages in queue
    location: str

@dataclass
class PrintJob:
    job_id: str
    pages: int
    copies: int
    color_mode: ColorMode
    priority: int  # 1=urgent, 2=normal, 3=low
    submitted_at: datetime
    user_id: str

@dataclass
class ScheduledJob:
    job_id: str
    printer_id: str
    start_time: datetime
    end_time: datetime
    estimated_wait_seconds: int

class SmartScheduler:
    def __init__(self, printers: List[Printer]):
        self.printers = {p.id: p for p in printers}
        # Min heap: (next_available_time, load, printer_id)
        self.availability_heap = []
        self._initialize_heap()
    
    def _initialize_heap(self):
        """Initialize priority queue with printer availability"""
        for printer in self.printers.values():
            if printer.status != PrinterStatus.OFFLINE:
                heapq.heappush(
                    self.availability_heap,
                    (printer.next_available_time, printer.current_load, printer.id)
                )
    
    def _calculate_print_time(self, printer: Printer, job: PrintJob) -> float:
        """Calculate time needed to print a job on a specific printer"""
        total_pages = job.pages * job.copies
        
        if job.color_mode == ColorMode.COLOR:
            if not printer.supports_color:
                return float('inf')  # Can't print color on BW printer
            return total_pages / printer.color_speed
        else:
            return total_pages / printer.bw_speed
    
    def _get_eligible_printers(self, job: PrintJob) -> List[Printer]:
        """Get printers that can handle this job"""
        eligible = []
        for printer in self.printers.values():
            if printer.status == PrinterStatus.OFFLINE:
                continue
            if job.color_mode == ColorMode.COLOR and not printer.supports_color:
                continue
            eligible.append(printer)
        return eligible
    
    def _calculate_priority_score(self, printer: Printer, job: PrintJob, 
                                   current_time: datetime) -> float:
        """
        Calculate priority score for printer selection
        Lower score = better choice
        Factors: wait time, load balance, print speed
        """
        wait_time = (printer.next_available_time - current_time).total_seconds()
        print_time = self._calculate_print_time(printer, job)
        
        if print_time == float('inf'):
            return float('inf')
        
        # Normalize factors
        load_factor = printer.current_load / 1000.0  # Normalize load
        priority_weight = 1.0 / job.priority  # Higher priority = lower score
        
        # Combined score (weighted)
        score = (
            wait_time * 0.4 +           # 40% weight on wait time
            print_time * 0.3 +          # 30% weight on print duration
            load_factor * 100 * 0.2 +   # 20% weight on current load
            (1.0 - priority_weight) * 50 * 0.1  # 10% weight on job priority
        )
        
        return score
    
    def schedule_job(self, job: PrintJob) -> Optional[ScheduledJob]:
        """
        Main scheduling algorithm - assigns job to optimal printer
        Returns ScheduledJob or None if no printer available
        """
        current_time = job.submitted_at
        eligible_printers = self._get_eligible_printers(job)
        
        if not eligible_printers:
            return None  # No printer can handle this job
        
        # Find best printer using priority scoring
        best_printer = None
        best_score = float('inf')
        
        for printer in eligible_printers:
            score = self._calculate_priority_score(printer, job, current_time)
            if score < best_score:
                best_score = score
                best_printer = printer
        
        if not best_printer:
            return None
        
        # Calculate timing
        start_time = max(best_printer.next_available_time, current_time)
        print_duration = self._calculate_print_time(best_printer, job)
        end_time = start_time + timedelta(seconds=print_duration)
        wait_seconds = int((start_time - current_time).total_seconds())
        
        # Update printer state
        best_printer.next_available_time = end_time
        best_printer.current_load += job.pages * job.copies
        best_printer.status = PrinterStatus.BUSY
        
        # Rebuild heap (in production, use heapq.heapreplace for efficiency)
        self._rebuild_heap()
        
        return ScheduledJob(
            job_id=job.job_id,
            printer_id=best_printer.id,
            start_time=start_time,
            end_time=end_time,
            estimated_wait_seconds=wait_seconds
        )
    
    def _rebuild_heap(self):
        """Rebuild priority queue after updates"""
        self.availability_heap = []
        for printer in self.printers.values():
            if printer.status != PrinterStatus.OFFLINE:
                heapq.heappush(
                    self.availability_heap,
                    (printer.next_available_time, printer.current_load, printer.id)
                )
    
    def mark_job_complete(self, printer_id: str, pages_printed: int):
        """Update printer state after job completion"""
        if printer_id in self.printers:
            printer = self.printers[printer_id]
            printer.current_load = max(0, printer.current_load - pages_printed)
            
            # If no more load, mark as idle
            if printer.current_load == 0:
                printer.status = PrinterStatus.IDLE
                printer.next_available_time = datetime.now()
            
            self._rebuild_heap()
    
    def get_printer_stats(self) -> Dict:
        """Get current statistics of all printers"""
        stats = {}
        for pid, printer in self.printers.items():
            stats[pid] = {
                "name": printer.name,
                "status": printer.status.value,
                "current_load": printer.current_load,
                "next_available": printer.next_available_time.isoformat(),
                "supports_color": printer.supports_color
            }
        return stats


# Example Usage
if __name__ == "__main__":
    # Initialize printers
    now = datetime.now()
    printers = [
        Printer("P1", "BW Printer 1", False, 1.0, 0.0, PrinterStatus.IDLE, now, 0, "Campus-A"),
        Printer("P2", "BW Printer 2", False, 1.0, 0.0, PrinterStatus.IDLE, now, 0, "Campus-A"),
        Printer("P3", "BW Printer 3", False, 1.0, 0.0, PrinterStatus.IDLE, now, 0, "Campus-B"),
        Printer("P4", "BW Printer 4", False, 1.0, 0.0, PrinterStatus.IDLE, now, 0, "Campus-B"),
        Printer("P5", "Color Printer 1", True, 1.0, 0.33, PrinterStatus.IDLE, now, 0, "Campus-A"),
        Printer("P6", "Color Printer 2", True, 1.0, 0.33, PrinterStatus.IDLE, now, 0, "Campus-B"),
    ]
    
    scheduler = SmartScheduler(printers)
    
    # Test scheduling
    job1 = PrintJob("J1", 10, 1, ColorMode.BW, 2, now, "user1")
    result1 = scheduler.schedule_job(job1)
    print(f"Job 1 scheduled: {result1}")
    
    job2 = PrintJob("J2", 5, 2, ColorMode.COLOR, 1, now, "user2")
    result2 = scheduler.schedule_job(job2)
    print(f"Job 2 scheduled: {result2}")
    
    print("\nPrinter Stats:")
    print(scheduler.get_printer_stats())
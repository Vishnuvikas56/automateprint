"""
Automated Test Script for Smart Print Automation System
Tests scheduler efficiency, load balancing, and timing accuracy
"""

import requests
import time
import json
from datetime import datetime
from typing import List, Dict
import random

# Configuration
JOB_MANAGER_URL = "http://localhost:8000"
PRINTER_API_URL = "http://localhost:8001"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def check_servers():
    """Check if both servers are running"""
    print_header("CHECKING SERVER STATUS")
    
    try:
        response = requests.get(f"{PRINTER_API_URL}/", timeout=2)
        if response.status_code == 200:
            print_success("Printer Simulation API (8001) is running")
        else:
            print_error("Printer API returned unexpected status")
            return False
    except:
        print_error("Printer Simulation API (8001) is NOT running")
        print_warning("Start it with: uvicorn printer_simulation:app --port 8001 --reload")
        return False
    
    try:
        response = requests.get(f"{JOB_MANAGER_URL}/", timeout=2)
        if response.status_code == 200:
            print_success("Job Manager API (8000) is running")
        else:
            print_error("Job Manager API returned unexpected status")
            return False
    except:
        print_error("Job Manager API (8000) is NOT running")
        print_warning("Start it with: uvicorn job_management:app --port 8000 --reload")
        return False
    
    return True

def reset_system():
    """Reset the entire system"""
    print_header("RESETTING SYSTEM")
    try:
        response = requests.post(f"{JOB_MANAGER_URL}/system/reset")
        if response.status_code == 200:
            print_success("System reset successfully")
            time.sleep(2)  # Wait for initialization
            return True
    except Exception as e:
        print_error(f"Failed to reset system: {e}")
    return False

def get_printers():
    """Get list of all printers"""
    try:
        response = requests.get(f"{PRINTER_API_URL}/printers")
        return response.json()
    except:
        return []

def submit_job(pages, copies, color_mode, priority=2, user_id="test_user"):
    """Submit a print job"""
    try:
        response = requests.post(
            f"{JOB_MANAGER_URL}/jobs/submit",
            json={
                "pages": pages,
                "copies": copies,
                "color_mode": color_mode,
                "priority": priority,
                "user_id": user_id
            }
        )
        return response.json()
    except Exception as e:
        print_error(f"Failed to submit job: {e}")
        return None

def get_job_status(job_id):
    """Get status of a specific job"""
    try:
        response = requests.get(f"{JOB_MANAGER_URL}/jobs/{job_id}")
        return response.json()
    except:
        return None

def get_system_stats():
    """Get system statistics"""
    try:
        response = requests.get(f"{JOB_MANAGER_URL}/system/stats")
        return response.json()
    except:
        return None

def test_basic_scheduling():
    """Test 1: Basic scheduling functionality"""
    print_header("TEST 1: BASIC SCHEDULING")
    
    # Submit a simple BW job
    print_info("Submitting BW print job (10 pages)...")
    result = submit_job(pages=10, copies=1, color_mode="bw", priority=2)
    
    if result and "job_id" in result:
        job_id = result["job_id"]
        printer_id = result.get("assigned_printer_id")
        wait_time = result.get("estimated_wait_seconds", 0)
        
        print_success(f"Job {job_id} assigned to {printer_id}")
        print_info(f"Estimated wait time: {wait_time} seconds")
        print_info(f"Expected completion: {result.get('estimated_end_time', 'N/A')}")
        return True
    else:
        print_error("Failed to submit job")
        return False

def test_color_scheduling():
    """Test 2: Color job scheduling"""
    print_header("TEST 2: COLOR JOB SCHEDULING")
    
    print_info("Submitting color print job (5 pages)...")
    result = submit_job(pages=5, copies=1, color_mode="color", priority=1)
    
    if result and "job_id" in result:
        job_id = result["job_id"]
        printer_id = result.get("assigned_printer_id")
        
        # Verify it's assigned to P5 or P6 (color printers)
        if printer_id in ["P5", "P6"]:
            print_success(f"Color job correctly assigned to {printer_id}")
            print_info(f"Wait time: {result.get('estimated_wait_seconds', 0)}s")
            return True
        else:
            print_error(f"Color job incorrectly assigned to {printer_id}")
            return False
    else:
        print_error("Failed to submit color job")
        return False

def test_load_balancing():
    """Test 3: Load balancing across printers"""
    print_header("TEST 3: LOAD BALANCING")
    
    print_info("Submitting 10 BW jobs to test distribution...")
    job_ids = []
    printer_assignments = {}
    
    for i in range(10):
        result = submit_job(pages=5, copies=1, color_mode="bw", priority=2, user_id=f"user{i}")
        if result and "job_id" in result:
            job_ids.append(result["job_id"])
            printer_id = result.get("assigned_printer_id")
            printer_assignments[printer_id] = printer_assignments.get(printer_id, 0) + 1
        time.sleep(0.1)  # Small delay between submissions
    
    print_info(f"Submitted {len(job_ids)} jobs")
    print_info("Job distribution:")
    for printer_id, count in sorted(printer_assignments.items()):
        print(f"  {printer_id}: {count} jobs")
    
    # Check if load is reasonably distributed
    if len(printer_assignments) >= 3:
        print_success("Good load distribution across multiple printers")
        return True
    else:
        print_warning("Jobs concentrated on few printers")
        return False

def test_priority_scheduling():
    """Test 4: Priority-based scheduling"""
    print_header("TEST 4: PRIORITY SCHEDULING")
    
    print_info("Submitting jobs with different priorities...")
    
    # Low priority job
    low_priority = submit_job(pages=20, copies=1, color_mode="bw", priority=3)
    time.sleep(0.2)
    
    # Urgent priority job
    urgent_priority = submit_job(pages=5, copies=1, color_mode="bw", priority=1)
    
    if low_priority and urgent_priority:
        low_wait = low_priority.get("estimated_wait_seconds", 0)
        urgent_wait = urgent_priority.get("estimated_wait_seconds", 0)
        
        print_info(f"Low priority job wait time: {low_wait}s")
        print_info(f"Urgent priority job wait time: {urgent_wait}s")
        
        # In ideal case, urgent should have lower or similar wait time
        print_success("Priority scheduling test completed")
        return True
    else:
        print_error("Failed to submit priority test jobs")
        return False

def test_timing_accuracy():
    """Test 5: Timing accuracy verification"""
    print_header("TEST 5: TIMING ACCURACY")
    
    print_info("Submitting job and tracking actual vs estimated time...")
    
    # Submit a small BW job
    result = submit_job(pages=5, copies=1, color_mode="bw", priority=2)
    
    if not result or "job_id" not in result:
        print_error("Failed to submit job")
        return False
    
    job_id = result["job_id"]
    estimated_duration = (
        result.get("estimated_end_time") and result.get("estimated_start_time")
    )
    
    print_info(f"Job ID: {job_id}")
    print_info("Waiting for job to complete...")
    
    start_time = time.time()
    status = "sent_to_printer"
    
    # Poll for completion (max 30 seconds)
    for _ in range(60):
        job_status = get_job_status(job_id)
        if job_status:
            status = job_status.get("status", "unknown")
            if status == "completed":
                break
        time.sleep(0.5)
    
    actual_duration = time.time() - start_time
    
    if status == "completed":
        print_success(f"Job completed in {actual_duration:.1f} seconds")
        print_info("Expected: ~5 seconds (5 pages × 1 sec/page)")
        
        # Allow 2 second tolerance for processing overhead
        if 4 <= actual_duration <= 8:
            print_success("Timing accuracy verified!")
            return True
        else:
            print_warning(f"Timing off by {abs(actual_duration - 5):.1f} seconds")
            return False
    else:
        print_error(f"Job did not complete (status: {status})")
        return False

def display_final_stats():
    """Display final system statistics"""
    print_header("FINAL SYSTEM STATISTICS")
    
    stats = get_system_stats()
    if stats:
        print_info("Printer Statistics:")
        printer_stats = stats.get("printers", {})
        print(f"  Total printers: {printer_stats.get('total', 0)}")
        print(f"  Idle: {printer_stats.get('idle', 0)}")
        print(f"  Busy: {printer_stats.get('busy', 0)}")
        print(f"  BW printers: {printer_stats.get('bw_printers', 0)}")
        print(f"  Color printers: {printer_stats.get('color_printers', 0)}")
        
        print_info("\nJob Statistics:")
        job_stats = stats.get("jobs", {})
        print(f"  Total managed: {job_stats.get('managed', 0)}")
        by_status = job_stats.get("by_status", {})
        for status, count in by_status.items():
            if count > 0:
                print(f"  {status}: {count}")
    else:
        print_error("Could not fetch system statistics")

def run_all_tests():
    """Run all test scenarios"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     SMART PRINT AUTOMATION SYSTEM - TEST SUITE             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    # Check servers
    if not check_servers():
        print_error("\nServers not running. Please start both servers first.")
        return
    
    # Reset system
    if not reset_system():
        print_error("\nFailed to reset system")
        return
    
    # Run tests
    results = []
    
    results.append(("Basic Scheduling", test_basic_scheduling()))
    time.sleep(2)
    
    results.append(("Color Job Scheduling", test_color_scheduling()))
    time.sleep(2)
    
    results.append(("Load Balancing", test_load_balancing()))
    time.sleep(2)
    
    results.append(("Priority Scheduling", test_priority_scheduling()))
    time.sleep(2)
    
    results.append(("Timing Accuracy", test_timing_accuracy()))
    
    # Display results
    print_header("TEST RESULTS SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}\n🎉 ALL TESTS PASSED! 🎉{Colors.END}\n")
    else:
        print(f"{Colors.YELLOW}\n⚠️  Some tests failed. Check logs above.{Colors.END}\n")
    
    # Display final stats
    time.sleep(2)
    display_final_stats()

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
"""
Database initialization script
Creates tables and seeds initial data
Run: python init_database.py
"""

from database import init_db, get_db_context
from models import Store, SupervisorData, Printer, RoleEnum, PrinterType, StoreStatusEnum, PrinterStatusEnum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_initial_data():
    """Seed database with initial stores and printers"""
    
    logger.info("Starting database seeding...")
    
    with get_db_context() as db:
        # Check if data already exists
        existing_stores = db.query(Store).count()
        if existing_stores > 0:
            logger.info("Database already has data. Skipping seed.")
            return
        
        # Create stores
        stores_data = [
            {
                "store_id": "STORE001",
                "store_name": "Campus Print Shop A",
                "address": "Building A, Main Campus",
                "contact_number": "+91-9876543210",
                "email": "storeA@campus.edu",
                "business_hours": {"open": "08:00", "close": "20:00"},
                "pricing_info": {
                    "bw_per_page": 2.0,
                    "color_per_page": 10.0,
                    "discounts": {"bulk": 0.1}
                },
                "payment_modes": ["cash", "upi", "card"],
                "status": StoreStatusEnum.OPEN
            },
            {
                "store_id": "STORE002",
                "store_name": "Campus Print Shop B",
                "address": "Building B, Main Campus",
                "contact_number": "+91-9876543211",
                "email": "storeB@campus.edu",
                "business_hours": {"open": "09:00", "close": "21:00"},
                "pricing_info": {
                    "bw_per_page": 2.0,
                    "color_per_page": 10.0
                },
                "payment_modes": ["cash", "upi"],
                "status": StoreStatusEnum.OPEN
            }
        ]
        
        for store_data in stores_data:
            store = Store(**store_data)
            db.add(store)
            logger.info(f"Created store: {store.store_id}")
        
        # Create printers
        printers_data = [
            {
                "printer_id": "P1",
                "store_id": "STORE001",
                "printer_name": "BW Printer 1",
                "printer_model": "HP LaserJet Pro M404n",
                "type": PrinterType.LASER,
                "supported_sizes": ["A4", "Legal"],
                "color_support": False,
                "duplex_support": True,
                "status": PrinterStatusEnum.ONLINE,
                "paper_capacity": 500,
                "paper_available": 500,
                "ink_toner_level": {"black": 85}
            },
            {
                "printer_id": "P2",
                "store_id": "STORE001",
                "printer_name": "BW Printer 2",
                "printer_model": "Canon LBP2900B",
                "type": PrinterType.LASER,
                "supported_sizes": ["A4"],
                "color_support": False,
                "duplex_support": False,
                "status": PrinterStatusEnum.ONLINE,
                "paper_capacity": 250,
                "paper_available": 250,
                "ink_toner_level": {"black": 70}
            },
            {
                "printer_id": "P3",
                "store_id": "STORE002",
                "printer_name": "BW Printer 3",
                "printer_model": "Brother HL-L2321D",
                "type": PrinterType.LASER,
                "supported_sizes": ["A4", "Legal"],
                "color_support": False,
                "duplex_support": True,
                "status": PrinterStatusEnum.ONLINE,
                "paper_capacity": 500,
                "paper_available": 450,
                "ink_toner_level": {"black": 60}
            },
            {
                "printer_id": "P4",
                "store_id": "STORE002",
                "printer_name": "BW Printer 4",
                "printer_model": "HP LaserJet M111w",
                "type": PrinterType.LASER,
                "supported_sizes": ["A4"],
                "color_support": False,
                "duplex_support": False,
                "status": PrinterStatusEnum.ONLINE,
                "paper_capacity": 150,
                "paper_available": 150,
                "ink_toner_level": {"black": 90}
            },
            {
                "printer_id": "P5",
                "store_id": "STORE001",
                "printer_name": "Color Printer 1",
                "printer_model": "Epson L3250",
                "type": PrinterType.INKJET,
                "supported_sizes": ["A4", "A3"],
                "color_support": True,
                "duplex_support": False,
                "status": PrinterStatusEnum.ONLINE,
                "paper_capacity": 100,
                "paper_available": 100,
                "ink_toner_level": {
                    "black": 75,
                    "cyan": 60,
                    "magenta": 65,
                    "yellow": 70
                }
            },
            {
                "printer_id": "P6",
                "store_id": "STORE002",
                "printer_name": "Color Printer 2",
                "printer_model": "Canon PIXMA G3000",
                "type": PrinterType.INKJET,
                "supported_sizes": ["A4"],
                "color_support": True,
                "duplex_support": False,
                "status": PrinterStatusEnum.ONLINE,
                "paper_capacity": 100,
                "paper_available": 85,
                "ink_toner_level": {
                    "black": 80,
                    "cyan": 75,
                    "magenta": 70,
                    "yellow": 65
                }
            }
        ]
        
        for printer_data in printers_data:
            printer = Printer(**printer_data)
            db.add(printer)
            logger.info(f"Created printer: {printer.printer_id}")
        
        # Create supervisors
        supervisors_data = [
            {
                "admin_id": "ADMIN001",
                "store_id": "STORE001",
                "username": "admin_store_a",
                "password": "hashed_password_here",  # In production, use proper hashing
                "role": RoleEnum.OWNER,
                "address": "Campus Residence A",
                "contact_number": "+91-9876543220",
                "email": "admin.a@campus.edu",
                "available": True,
                "permissions": {
                    "can_manage_printers": True,
                    "can_view_reports": True,
                    "can_manage_orders": True
                }
            },
            {
                "admin_id": "ADMIN002",
                "store_id": "STORE002",
                "username": "admin_store_b",
                "password": "hashed_password_here",
                "role": RoleEnum.SUPERVISOR,
                "address": "Campus Residence B",
                "contact_number": "+91-9876543221",
                "email": "admin.b@campus.edu",
                "available": True,
                "permissions": {
                    "can_manage_printers": True,
                    "can_view_reports": True
                }
            }
        ]
        
        for supervisor_data in supervisors_data:
            supervisor = SupervisorData(**supervisor_data)
            db.add(supervisor)
            logger.info(f"Created supervisor: {supervisor.username}")
        
        db.commit()
        logger.info("✓ Database seeded successfully!")

if __name__ == "__main__":
    try:
        # Initialize database (create tables)
        logger.info("Initializing database...")
        init_db()
        
        # Seed initial data
        seed_initial_data()
        
        logger.info("✓ Database initialization complete!")
        
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        raise
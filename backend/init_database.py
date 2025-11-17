"""
Database Initialization Script
Creates tables and seeds initial data for testing
"""

import sys
from datetime import datetime
from database import engine, SessionLocal, Base, init_db
from models import (
    User, Store, Printer, StoreStatusEnum, PrinterStatusEnum,
    PrinterType, PrinterConnectionType
)
from auth import hash_password, generate_user_id
from sqlalchemy import text

def create_tables():
    """Create all database tables"""
    print("📊 Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def seed_test_data():
    """Seed database with test data"""
    print("\n🌱 Seeding test data...")
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_store = db.query(Store).filter(Store.store_id == "STORE001").first()
        if existing_store:
            print("⚠️  Test data already exists. Skipping...")
            return True
        
        # Create test store
        store = Store(
            store_id="STORE001",
            store_name="Main Print Shop",
            address="123 Main Street, City, State 12345",
            contact_number="+1234567890",
            email="store@printshop.com",
            business_hours={"open": "09:00", "close": "21:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]},
            pricing_info={"bw_per_page": 2.0, "color_per_page": 10.0},
            payment_modes=["cash", "upi", "card", "razorpay"],
            status=StoreStatusEnum.OPEN
        )
        db.add(store)
        db.commit()
        print("✅ Store created: STORE001")
        
        # Create test user
        test_user = User(
            user_id=generate_user_id(),
            email="test@example.com",
            username="testuser",
            password_hash=hash_password("password123"),
            full_name="Test User",
            phone="+1234567890",
            balance=1000.0,
            is_active=True,
            is_verified=True
        )
        db.add(test_user)
        db.commit()
        print(f"✅ Test user created: testuser (password: password123)")
        
        # Note: Printers will be synced from simulator on backend startup
        print("ℹ️  Printers will be synced from simulator on first backend startup")
        
        print("✅ Test data seeded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to seed data: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def check_database_connection():
    """Verify database connection"""
    print("🔍 Checking database connection...")
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))

        db.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("ℹ️  Make sure PostgreSQL is running and DATABASE_URL in .env is correct")
        return False

def reset_database():
    """Drop all tables (USE WITH CAUTION)"""
    print("⚠️  WARNING: This will delete ALL data!")
    confirmation = input("Type 'DELETE ALL DATA' to confirm: ")
    
    if confirmation == "DELETE ALL DATA":
        print("🗑️  Dropping all tables...")
        try:
            Base.metadata.drop_all(bind=engine)
            print("✅ All tables dropped")
            return True
        except Exception as e:
            print(f"❌ Failed to drop tables: {e}")
            return False
    else:
        print("❌ Confirmation failed. Aborting.")
        return False

def main():
    """Main initialization flow"""
    print("=" * 60)
    print("  Database Initialization")
    print("=" * 60)
    print()
    
    # Check for --reset flag
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        if not reset_database():
            sys.exit(1)
        print()
    
    # Check connection
    if not check_database_connection():
        sys.exit(1)
    
    print()
    
    # Create tables
    if not create_tables():
        sys.exit(1)
    
    print()
    
    # Seed data
    if not seed_test_data():
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("  ✨ Database initialization complete!")
    print("=" * 60)
    print()
    print("Test Credentials:")
    print("  Username: testuser")
    print("  Password: password123")
    print()
    print("Next steps:")
    print("  1. Start services: ./quick_start.sh")
    print("  2. Run tests: python3 test_integration.py")
    print("  3. Access API docs: http://localhost:8000/docs")
    print()

if __name__ == "__main__":
    main()
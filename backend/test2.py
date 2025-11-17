# fixed_init.py
from database import engine, Base
from models import Store, StoreStatusEnum
from sqlalchemy.orm import sessionmaker
from datetime import datetime

def init_database():
    """Initialize database tables and default data"""
    try:
        print("🔄 Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
        
        # Create session
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Check if store already exists
        existing_store = db.query(Store).filter(Store.store_id == "STORE001").first()
        if existing_store:
            print("✅ Store already exists")
            db.close()
            return
        
        # Create default store with correct enum value
        print("🏪 Creating default store...")
        
        default_store = Store(
            store_id="STORE001",
            store_name="Main Store",
            address="123 Main Street, City, State",
            contact_number="+91-9876543210",
            email="store@example.com",
            business_hours={"open": "09:00", "close": "21:00"},
            pricing_info={
                "bw_per_page": 2.0,
                "color_per_page": 10.0,
                "thick_per_page": 5.0,
                "glossy_per_page": 15.0,
                "poster_per_page": 50.0
            },
            payment_modes=["cash", "upi", "card"],
            status=StoreStatusEnum.OPEN  # Use the correct enum value
        )
        
        db.add(default_store)
        db.commit()
        print("✅ Default store created")
        
        db.close()
        print("🎉 Database initialization complete!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_database()
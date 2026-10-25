# backend/app/database.py
import os
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Database configuration
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./bhashaops.db")
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Database Models ---

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, index=True)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    brand = Column(String)
    variant = Column(String)
    pack_size = Column(String)
    base_unit = Column(String, nullable=False)
    unit_price_minor = Column(Integer, nullable=False) # Price in paise (e.g., ₹50 = 5000)
    stock_quantity = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=5)
    active = Column(Integer, default=1)

class ProductAlias(Base):
    __tablename__ = "product_aliases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    alias_normalized = Column(String, nullable=False) # Lowercased, stripped
    __table_args__ = (UniqueConstraint('product_id', 'alias_normalized', name='uq_product_alias'),)

class StockLedger(Base):
    __tablename__ = "stock_ledger"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String, nullable=False) # SALE, RECEIPT, ADJUSTMENT
    quantity_delta = Column(Integer, nullable=False) # Negative for SALE
    reference_type = Column(String) # e.g., 'order'
    reference_id = Column(String) # e.g., order_id
    idempotency_key = Column(String, unique=True, nullable=False) # CRITICAL: Prevents double deduction
    reason = Column(Text)
    created_by = Column(String, default="system")
    created_at = Column(String) # ISO format string

# --- Helper Functions ---

def init_db():
    """Initialize the database and create tables."""
    # Enable foreign keys for SQLite (must be done per connection)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for FastAPI to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
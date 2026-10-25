from pathlib import Path

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    inspect,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.config import settings


def _database_url():
    url = make_url(settings.DATABASE_URL)
    if url.drivername.startswith("sqlite") and url.database not in (None, "", ":memory:"):
        database_path = Path(url.database)
        if not database_path.is_absolute():
            backend_dir = Path(__file__).resolve().parents[1]
            database_path = backend_dir / database_path
        url = url.set(database=str(database_path.resolve()))
    return url


DATABASE_URL = _database_url()
engine_options = {}
if DATABASE_URL.drivername.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    brand = Column(String)
    variant = Column(String)
    pack_size = Column(String)
    base_unit = Column(String, nullable=False)
    unit_price_minor = Column(Integer, nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=5)
    active = Column(Integer, default=1)
    aliases = relationship("ProductAlias", back_populates="product")


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    alias_normalized = Column(String, nullable=False)
    product = relationship("Product", back_populates="aliases")
    __table_args__ = (
        UniqueConstraint("product_id", "alias_normalized", name="uq_product_alias"),
    )


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String, nullable=False)
    quantity_delta = Column(Integer, nullable=False)
    reference_type = Column(String)
    reference_id = Column(String)
    idempotency_key = Column(String, unique=True, nullable=False)
    reason = Column(Text)
    created_by = Column(String, default="system")
    created_at = Column(String)


class InboundMessage(Base):
    __tablename__ = "inbound_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    external_message_id = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    __table_args__ = (
        UniqueConstraint("source", "external_message_id", name="uq_inbound_message"),
    )


class StoredOrder(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    inbound_message_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    order_data = Column(JSON, nullable=False)
    result_data = Column(JSON)
    created_at = Column(DateTime, nullable=False)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(connection, _):
    if DATABASE_URL.drivername.startswith("sqlite"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_existing_schema(engine)


def _migrate_existing_schema(database_engine):
    if not inspect(database_engine).has_table("orders"):
        return
    columns = {column["name"] for column in inspect(database_engine).get_columns("orders")}
    if "source" not in columns:
        with database_engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE orders "
                    "ADD COLUMN source VARCHAR NOT NULL DEFAULT 'simulator'"
                )
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

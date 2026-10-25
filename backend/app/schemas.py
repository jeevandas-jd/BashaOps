# backend/app/schemas.py
from pydantic import BaseModel
from typing import List, Optional

# --- Catalogue Contracts ---
class CatalogueProduct(BaseModel):
    id: str
    sku: str
    name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    pack_size: Optional[str] = None
    base_unit: str
    unit_price_minor: int  # Integer paise
    stock_quantity: int

    class Config:
        from_attributes = True  # Allows converting from SQLAlchemy models

# --- Inventory & Order Contracts ---
class OrderItemToDeduct(BaseModel):
    product_id: str
    order_item_id: str
    quantity: int

class StockDeductionResult(BaseModel):
    success: bool
    ledger_entries: List[str] = []      # List of created idempotency keys
    low_stock_alerts: List[str] = []    # List of product IDs that crossed threshold
    error_message: Optional[str] = None
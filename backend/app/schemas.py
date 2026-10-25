# backend/app/schemas.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

# ==========================================================
# DEVELOPER B: Catalogue & Inventory Contracts
# ==========================================================

class CatalogueProduct(BaseModel):
    """Represents a product from the shop's catalogue."""
    id: str
    sku: str
    name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    pack_size: Optional[str] = None
    base_unit: str
    unit_price_minor: int  # Integer paise (e.g., 1000 = ₹10.00)
    stock_quantity: int

    model_config = ConfigDict(from_attributes=True)

class OrderItemToDeduct(BaseModel):
    """Payload for requesting stock deduction."""
    product_id: str
    order_item_id: str
    quantity: int

class StockDeductionResult(BaseModel):
    """Result of an atomic stock deduction transaction."""
    success: bool
    ledger_entries: List[str] = []      
    low_stock_alerts: List[str] = []    
    error_message: Optional[str] = None


# ==========================================================
# DEVELOPER A: Messaging, Gemma & Order Contracts
# ==========================================================

class ExtractedItem(BaseModel):
    """A single item extracted by the Gemma model."""
    product_mention: str
    quantity: float = Field(gt=0)
    unit: Optional[str] = None  # Allow null from model
    variant: Optional[str] = None
    pack_size_hint: Optional[str] = None
    source_text: str
    needs_review: bool = False
    clarification_question: Optional[str] = None

    @field_validator('unit')
    @classmethod
    def ensure_unit_string(cls, v):
        # Gracefully handle null or empty strings from the LLM
        if v is None or str(v).strip() == "":
            return "piece"
        return str(v).strip()

class GemmaExtractionResponse(BaseModel):
    """The validated JSON output from the Gemma model."""
    schema_version: str = "1.0"
    intent: Literal["PLACE_ORDER", "CORRECTION", "CANCEL", "GENERAL_CHAT"]
    language: str
    items: List[ExtractedItem]
    general_notes: List[str] = []

class InboundMessageEvent(BaseModel):
    """Normalized message event from WhatsApp or Simulator."""
    source: Literal["simulator", "whatsapp"] = "simulator"
    external_message_id: str
    conversation_id: str
    sender_id: str
    text: str
    received_at: datetime = Field(default_factory=datetime.utcnow)

class OrderStatus(str, Enum):
    """Lifecycle states of an order."""
    RECEIVED = "RECEIVED"
    PARSED = "PARSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class OrderItemDraft(BaseModel):
    """An item in a draft order, awaiting catalogue resolution."""
    product_mention: str
    source_text: str
    resolved_product_id: Optional[str] = None 
    requested_quantity: float
    requested_unit: str
    resolution_status: Literal["EXACT", "CANDIDATES", "UNKNOWN", "INCOMPATIBLE_UNIT"] = "UNKNOWN"
    needs_review: bool = False

class OrderDraft(BaseModel):
    """The complete draft order."""
    id: str
    inbound_message_id: str
    status: OrderStatus = OrderStatus.PARSED
    items: List[OrderItemDraft]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class APIResponse(BaseModel):
    """Standardized API response wrapper."""
    success: bool
    message: str
    data: Optional[dict] = None
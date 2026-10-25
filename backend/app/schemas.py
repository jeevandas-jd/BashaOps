# backend/app/schemas.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone
from enum import Enum

# --- DEVELOPER B: Catalogue & Inventory Contracts ---
class CatalogueProduct(BaseModel):
    id: str
    sku: str
    name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    pack_size: Optional[str] = None
    base_unit: str
    unit_price_minor: int
    stock_quantity: int
    model_config = ConfigDict(from_attributes=True)

class OrderItemToDeduct(BaseModel):
    product_id: str
    order_item_id: str
    quantity: int = Field(gt=0)

class StockDeductionResult(BaseModel):
    success: bool
    ledger_entries: List[str] = Field(default_factory=list)
    low_stock_alerts: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

# --- DEVELOPER A: Messaging, Gemma & Order Contracts ---
class ExtractedItem(BaseModel):
    product_mention: str
    quantity: float = Field(gt=0)
    unit: Optional[str] = None
    variant: Optional[str] = None
    pack_size_hint: Optional[str] = None
    source_text: str
    needs_review: bool = False
    clarification_question: Optional[str] = None

    @field_validator('unit')
    @classmethod
    def ensure_unit_string(cls, v):
        if v is None or str(v).strip() == "": return "piece"
        return str(v).strip()

class GemmaExtractionResponse(BaseModel):
    schema_version: str = "1.0"
    intent: Literal["PLACE_ORDER", "CORRECTION", "CANCEL", "GENERAL_CHAT"]
    language: str
    items: List[ExtractedItem]
    general_notes: List[str] = Field(default_factory=list)

class InboundMessageEvent(BaseModel):
    source: Literal["simulator", "whatsapp"] = "simulator"
    external_message_id: str
    conversation_id: str
    sender_id: str
    text: str
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PARSED = "PARSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class OrderItemDraft(BaseModel):
    product_mention: str
    source_text: str
    resolved_product_id: Optional[str] = None
    requested_quantity: float
    requested_unit: str
    resolution_status: Literal["EXACT", "CANDIDATES", "UNKNOWN", "INCOMPATIBLE_UNIT"] = "UNKNOWN"
    needs_review: bool = False

class OrderDraft(BaseModel):
    id: str
    inbound_message_id: str
    status: OrderStatus = OrderStatus.PARSED
    items: List[OrderItemDraft]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- SHARED API RESPONSE (Dev A's version for frontend compatibility) ---
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
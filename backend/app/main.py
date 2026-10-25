# backend/app/main.py
"""BhashaOps FastAPI application entry point.

Run from the repository root:
    cd backend
    python -m uvicorn app.main:app --reload
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import logging

from app.config import settings
from app.schemas import (
    InboundMessageEvent, APIResponse, GemmaExtractionResponse, 
    OrderDraft, OrderItemDraft, OrderStatus
)
from app.gemma_service import call_gemma
from app.pricing_service import calculate_order_totals
from app.catalogue_service import find_product_candidates, confirm_stock_deduction

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BhashaOps API",
    description="Turn multilingual shop conversations into reviewable business actions.",
    version="0.1.0",
)

# Allow local frontend (and broad origins for hackathon demo ease)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================================
# TEMPORARY IN-MEMORY STORE 
# TODO (Dev A & Dev B): Replace these dicts with SQLite DB calls once 
# Dev B's database.py and models.py are fully wired up.
# ======================================================================
INBOUND_MESSAGES_DB = {}
ORDERS_DB = {}
DEDUP_CHECK = set() 
# ======================================================================


@app.get("/api/health", tags=["health"])
def health() -> dict:
    """Basic health check; does not require Gemma or the database to be running."""
    return {
        "status": "ok", 
        "service": "bhashaops-api", 
        "mode": "development" if settings.DEMO_MODE else "production",
        "model_configured": bool(settings.GEMMA_MODEL)
    }


# ======================================================================
# DEVELOPER A: Messaging & Order Flow Endpoints
# ======================================================================

@app.post("/api/messages", response_model=APIResponse, tags=["messages"])
async def ingest_message(event: InboundMessageEvent):
    """
    Message Ingestion & Deduplication.
    Receives a message, checks for duplicates, calls Gemma, and creates a draft order.
    """
    dedup_key = f"{event.source}:{event.external_message_id}"
    
    # 1. Deduplication Check (Idempotency)
    if dedup_key in DEDUP_CHECK:
        return APIResponse(
            success=True, 
            message="Duplicate message ignored. Returning existing state.",
            data={"message_id": event.external_message_id, "status": "DUPLICATE"}
        )
    
    DEDUP_CHECK.add(dedup_key)
    INBOUND_MESSAGES_DB[event.external_message_id] = event

    # 2. Call Gemma for Interpretation
    try:
        extraction: GemmaExtractionResponse = await call_gemma(event.text)
    except ValueError as e:
        logger.error(f"Gemma failed for message {event.external_message_id}: {e}")
        extraction = None

    # 3. Map to Order Draft with Hackathon Auto-Resolve
    order_id = str(uuid.uuid4())
    order_items = []
    needs_review = False

    if extraction and extraction.intent == "PLACE_ORDER":
        for item in extraction.items:
            if item.needs_review:
                needs_review = True
            
            # 🚀 HACKATHON AUTO-RESOLVE: Automatically match obvious items
            resolved_id = None
            res_status = "UNKNOWN"
            
            if not item.needs_review:
                mention = item.product_mention.lower()
                if "atta" in mention:
                    resolved_id = "prod_001"
                    res_status = "EXACT"
                elif "butter" in mention:
                    resolved_id = "prod_002"
                    res_status = "EXACT"
                elif "ande" in mention or "egg" in mention:
                    resolved_id = "prod_003"
                    res_status = "EXACT"
            
            order_items.append(OrderItemDraft(
                product_mention=item.product_mention,
                source_text=item.source_text,
                resolved_product_id=resolved_id,
                requested_quantity=item.quantity,
                requested_unit=item.unit,
                needs_review=item.needs_review,
                resolution_status=res_status
            ))
    else:
        needs_review = True # If model failed or wasn't an order

    order_status = OrderStatus.NEEDS_REVIEW if needs_review else OrderStatus.READY_FOR_CONFIRMATION
    
    draft_order = OrderDraft(
        id=order_id,
        inbound_message_id=event.external_message_id,
        status=order_status,
        items=order_items
    )
    
    ORDERS_DB[order_id] = draft_order
    
    return APIResponse(
        success=True,
        message="Message processed successfully",
        data={
            "order_id": order_id, 
            "status": order_status, 
            "extraction": extraction.model_dump() if extraction else None
        }
    )

@app.get("/api/orders", response_model=APIResponse, tags=["orders"])
async def list_orders():
    """List all draft and confirmed orders."""
    return APIResponse(
        success=True, 
        message="Orders retrieved", 
        data={"orders": [o.model_dump() for o in ORDERS_DB.values()]}
    )

@app.get("/api/orders/{order_id}", response_model=APIResponse, tags=["orders"])
async def get_order(order_id: str):
    """Get specific order details."""
    if order_id not in ORDERS_DB:
        raise HTTPException(status_code=404, detail="Order not found")
    return APIResponse(
        success=True, 
        message="Order retrieved", 
        data=ORDERS_DB[order_id].model_dump()
    )

@app.post("/api/orders/{order_id}/resolve", response_model=APIResponse, tags=["orders"])
async def resolve_order_item(order_id: str, item_index: int, resolved_product_id: str):
    """
    Developer A: Allows the operator to manually map an ambiguous item to a catalogue product.
    """
    if order_id not in ORDERS_DB:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = ORDERS_DB[order_id]
    if item_index < 0 or item_index >= len(order.items):
        raise HTTPException(status_code=400, detail="Invalid item index")
    
    # Update the specific item
    item = order.items[item_index]
    item.resolved_product_id = resolved_product_id
    item.resolution_status = "EXACT"
    item.needs_review = False
    
    # Check if all items are now resolved
    if not any(i.needs_review or i.resolution_status != "EXACT" for i in order.items):
        order.status = OrderStatus.READY_FOR_CONFIRMATION
        
    return APIResponse(
        success=True,
        message="Item resolved successfully",
        data=order.model_dump()
    )

@app.post("/api/orders/{order_id}/confirm", response_model=APIResponse, tags=["orders"])
async def confirm_order(order_id: str):
    """
    Developer A & B Integration: 
    1. Calculates deterministic pricing.
    2. Calls inventory service to deduct stock atomically.
    3. Updates order status to CONFIRMED.
    """
    if order_id not in ORDERS_DB:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = ORDERS_DB[order_id]
    
    if order.status not in [OrderStatus.READY_FOR_CONFIRMATION, OrderStatus.PARSED]:
        raise HTTPException(status_code=400, detail="Order is not ready for confirmation")
    
    # 1. Deterministic Pricing
    subtotal, discount, total = calculate_order_totals(order)
    
    # 2. Atomic Stock Deduction (Calls Dev B's contract)
    deduction_items = [
        {"product_id": item.resolved_product_id, "order_item_id": f"{order_id}_item_{i}"}
        for i, item in enumerate(order.items) if item.resolved_product_id
    ]
    
    stock_result = confirm_stock_deduction(order_id, deduction_items)
    
    if not stock_result["success"]:
        raise HTTPException(status_code=400, detail=f"Stock deduction failed: {stock_result.get('error_message')}")
    
    # 3. Update Order State
    order.status = OrderStatus.CONFIRMED
    
    # Attach pricing snapshot to the order object for the bill
    order_data = order.model_dump()
    order_data["subtotal_minor"] = subtotal
    order_data["discount_minor"] = discount
    order_data["total_minor"] = total
    order_data["ledger_entries"] = stock_result["ledger_entries"]
    
    return APIResponse(
        success=True,
        message="Order confirmed and stock deducted successfully",
        data=order_data
    )

@app.get("/api/products", response_model=APIResponse, tags=["products"])
async def list_products():
    """Helper endpoint for the frontend to show catalogue options during resolution."""
    from app.catalogue_service import MOCK_CATALOGUE
    return APIResponse(
        success=True,
        message="Catalogue retrieved",
        data={"products": [p.model_dump() for p in MOCK_CATALOGUE]}
    )
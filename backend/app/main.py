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

    # 3. Map to Order Draft
    order_id = str(uuid.uuid4())
    order_items = []
    needs_review = False

    if extraction and extraction.intent == "PLACE_ORDER":
        for item in extraction.items:
            if item.needs_review:
                needs_review = True
            
            order_items.append(OrderItemDraft(
                product_mention=item.product_mention,
                source_text=item.source_text,
                requested_quantity=item.quantity,
                requested_unit=item.unit,
                needs_review=item.needs_review,
                # Dev B's catalogue matcher will update this status later
                resolution_status="CANDIDATES" if item.needs_review else "UNKNOWN" 
            ))
    else:
        needs_review = True # If model failed or wasn't an order

    order_status = OrderStatus.NEEDS_REVIEW if needs_review else OrderStatus.PARSED
    
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
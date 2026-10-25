# backend/app/main.py
"""BhashaOps FastAPI application entry point.
Run from the repository root:
    cd backend
    python -m uvicorn app.main:app --reload
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import uuid
from typing import List
import logging

from app.config import settings
from app.database import get_db
from app.schemas import (
    InboundMessageEvent, APIResponse, GemmaExtractionResponse,
    OrderDraft, OrderItemDraft, OrderStatus, CatalogueProduct, OrderItemToDeduct
)
from app.gemma_service import call_gemma
from app.pricing_service import calculate_order_totals
from app.catalogue_service import find_product_candidates, confirm_stock_deduction
from app.bill_service import generate_html_bill

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

# ================= DEV B: INVENTORY & CATALOGUE ENDPOINTS =================
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "bhashaops-api", "mode": "development" if settings.DEMO_MODE else "production"}

@app.get("/api/products", response_model=List[CatalogueProduct])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.active == 1).all()

@app.get("/api/inventory")
def get_inventory_status(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.active == 1).all()
    inventory_data, low_stock_alerts = [], []
    for p in products:
        threshold = getattr(p, 'low_stock_threshold', 0)
        is_low = p.stock_quantity <= threshold
        inventory_data.append({"id": p.id, "name": p.name, "sku": p.sku, "stock_quantity": p.stock_quantity, "low_stock_threshold": threshold, "is_low_stock": is_low})
        if is_low: low_stock_alerts.append({"product_id": p.id, "name": p.name, "current_stock": p.stock_quantity, "threshold": threshold})
    return {"inventory": inventory_data, "low_stock_alerts": low_stock_alerts}

@app.get("/api/inventory/ledger")
def get_stock_ledger(db: Session = Depends(get_db)):
    movements = db.query(StockLedger).order_by(StockLedger.created_at.desc()).limit(50).all()
    return [{"id": m.id, "product_id": m.product_id, "movement_type": m.movement_type, "quantity_delta": m.quantity_delta, "reference_id": m.reference_id, "idempotency_key": m.idempotency_key, "created_at": m.created_at} for m in movements]

# ================= DEV A: MESSAGING & ORDER ENDPOINTS =================
@app.post("/api/messages", response_model=APIResponse, tags=["messages"])
async def ingest_message(event: InboundMessageEvent, db: Session = Depends(get_db)):
    dedup_key = f"{event.source}:{event.external_message_id}"
    if dedup_key in DEDUP_CHECK:
        return APIResponse(success=True, message="Duplicate message ignored.", data={"message_id": event.external_message_id, "status": "DUPLICATE"})
    
    DEDUP_CHECK.add(dedup_key)
    INBOUND_MESSAGES_DB[event.external_message_id] = event

    try:
        extraction: GemmaExtractionResponse = await call_gemma(event.text)
    except ValueError as e:
        logger.error(f"Gemma failed: {e}")
        extraction = None

    order_id = str(uuid.uuid4())
    order_items = []
    needs_review = False

    if extraction and extraction.intent == "PLACE_ORDER":
        for item in extraction.items:
            if item.needs_review:
                needs_review = True
            
            resolved_id = None
            res_status = "UNKNOWN"
            
            # Use Dev B's DB catalogue matcher
            candidates = find_product_candidates(item.product_mention, db)
            if len(candidates) == 1:
                resolved_id = candidates[0].id
                res_status = "EXACT"
            elif len(candidates) > 1:
                needs_review = True
                res_status = "CANDIDATES"
            
            # Hackathon fallback if DB is empty or no match found
            if not resolved_id and not item.needs_review:
                mention = item.product_mention.lower()
                if "atta" in mention: resolved_id, res_status = "prod_001", "EXACT"
                elif "butter" in mention: resolved_id, res_status = "prod_002", "EXACT"
                elif "ande" in mention or "egg" in mention: resolved_id, res_status = "prod_003", "EXACT"

            order_items.append(OrderItemDraft(
                product_mention=item.product_mention, source_text=item.source_text,
                resolved_product_id=resolved_id, requested_quantity=item.quantity,
                requested_unit=item.unit, needs_review=item.needs_review, resolution_status=res_status
            ))
    else:
        needs_review = True

    order_status = OrderStatus.NEEDS_REVIEW if needs_review else OrderStatus.READY_FOR_CONFIRMATION
    ORDERS_DB[order_id] = OrderDraft(id=order_id, inbound_message_id=event.external_message_id, status=order_status, items=order_items)

    return APIResponse(success=True, message="Message processed", data={"order_id": order_id, "status": order_status, "extraction": extraction.model_dump() if extraction else None})

@app.get("/api/orders", response_model=APIResponse)
async def list_orders():
    return APIResponse(success=True, message="Orders retrieved", data={"orders": [o.model_dump() for o in ORDERS_DB.values()]})

@app.get("/api/orders/{order_id}", response_model=APIResponse)
async def get_order(order_id: str):
    if order_id not in ORDERS_DB: raise HTTPException(status_code=404, detail="Order not found")
    return APIResponse(success=True, message="Order retrieved", data=ORDERS_DB[order_id].model_dump())

@app.post("/api/orders/{order_id}/resolve", response_model=APIResponse)
async def resolve_order_item(order_id: str, item_index: int, resolved_product_id: str):
    if order_id not in ORDERS_DB: raise HTTPException(status_code=404, detail="Order not found")
    order = ORDERS_DB[order_id]
    if item_index < 0 or item_index >= len(order.items): raise HTTPException(status_code=400, detail="Invalid item index")
    
    item = order.items[item_index]
    item.resolved_product_id = resolved_product_id
    item.resolution_status = "EXACT"
    item.needs_review = False
    
    if not any(i.needs_review or i.resolution_status != "EXACT" for i in order.items):
        order.status = OrderStatus.READY_FOR_CONFIRMATION
    return APIResponse(success=True, message="Item resolved", data=order.model_dump())

@app.post("/api/orders/{order_id}/confirm", response_model=APIResponse, tags=["orders"])
async def confirm_order(order_id: str, db: Session = Depends(get_db)):
    if order_id not in ORDERS_DB:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = ORDERS_DB[order_id]
    
    if order.status not in [OrderStatus.READY_FOR_CONFIRMATION, OrderStatus.PARSED]:
        raise HTTPException(status_code=400, detail="Order is not ready for confirmation")
    
    # 1. Deterministic Pricing
    subtotal, discount, total = calculate_order_totals(order, db)
    
    # 2. Atomic Stock Deduction (Using Pydantic OrderItemToDeduct objects)
    deduction_items = [
        OrderItemToDeduct(
            product_id=item.resolved_product_id, 
            order_item_id=f"{order_id}_item_{i}",
            quantity=int(item.requested_quantity)
        )
        for i, item in enumerate(order.items) if item.resolved_product_id
    ]
    
    stock_result = confirm_stock_deduction(order_id, deduction_items, db)
    
    # 🛡️ SAFE ACCESS: Handle both dict and Pydantic model returns
    if isinstance(stock_result, dict):
        is_success = stock_result.get("success")
        error_msg = stock_result.get("error_message")
        ledger_entries = stock_result.get("ledger_entries", [])
    else:
        is_success = getattr(stock_result, 'success', False)
        error_msg = getattr(stock_result, 'error_message', 'Unknown error')
        ledger_entries = getattr(stock_result, 'ledger_entries', [])

    if not is_success:
        raise HTTPException(status_code=400, detail=f"Stock deduction failed: {error_msg}")
    
    # 3. Update Order State
    order.status = OrderStatus.CONFIRMED
    
    # Attach pricing snapshot to the order object for the bill
    order_data = order.model_dump()
    order_data["subtotal_minor"] = subtotal
    order_data["discount_minor"] = discount
    order_data["total_minor"] = total
    order_data["ledger_entries"] = ledger_entries
    
    return APIResponse(
        success=True,
        message="Order confirmed and stock deducted successfully",
        data=order_data
    )

@app.get("/api/orders/{order_id}/bill", response_class=HTMLResponse, tags=["orders"])
async def get_order_bill(order_id: str, db: Session = Depends(get_db)):
    """
    Developer A: Generates a print-friendly HTML bill for a confirmed order.
    """
    if order_id not in ORDERS_DB:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = ORDERS_DB[order_id]
    order_data = order.model_dump()
    
    # Attach pricing if it was confirmed (fallback calculation if somehow missing)
    if order.status == OrderStatus.CONFIRMED and "subtotal_minor" not in order_data:
        subtotal, discount, total = calculate_order_totals(order, db)
        order_data["subtotal_minor"] = subtotal
        order_data["discount_minor"] = discount
        order_data["total_minor"] = total

    # Pass db to the bill generator so it can look up product names
    html_bill = generate_html_bill(order_data, db)
    return HTMLResponse(content=html_bill)
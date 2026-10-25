"""BhashaOps FastAPI application entry point."""
import logging
import uuid
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.bill_service import generate_html_bill
from app.catalogue_service import find_product_candidates, get_product
from app.database import (
    InboundMessage,
    Product,
    StockLedger,
    StoredOrder,
    get_db,
    init_db,
)
from app.gemma_service import call_gemma
from app.inventory_service import confirm_stock_deduction
from app.pricing_service import calculate_order_totals
from app.schemas import (
    APIResponse,
    CatalogueProduct,
    GemmaExtractionResponse,
    InboundMessageEvent,
    OrderDraft,
    OrderItemDraft,
    OrderItemToDeduct,
    OrderStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="BhashaOps API",
    description="From Conversations to Verified Actions",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _load_order(db: Session, order_id: str) -> tuple[StoredOrder, OrderDraft]:
    stored_order = db.query(StoredOrder).filter(StoredOrder.id == order_id).first()
    if stored_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return stored_order, OrderDraft.model_validate(stored_order.order_data)


def _save_order(stored_order: StoredOrder, order: OrderDraft):
    stored_order.status = order.status.value
    stored_order.order_data = order.model_dump(mode="json")
    stored_order.result_data = None


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ok", "service": "bhashaops-api", "db_connected": True}


@app.get("/api/products", response_model=List[CatalogueProduct])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.active == 1).order_by(Product.name).all()


@app.get("/api/inventory")
def get_inventory_status(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.active == 1).order_by(Product.name).all()
    inventory_data = []
    low_stock_alerts = []
    for product in products:
        is_low = product.stock_quantity <= product.low_stock_threshold
        inventory_data.append(
            {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "stock_quantity": product.stock_quantity,
                "low_stock_threshold": product.low_stock_threshold,
                "is_low_stock": is_low,
            }
        )
        if is_low:
            low_stock_alerts.append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "current_stock": product.stock_quantity,
                    "threshold": product.low_stock_threshold,
                }
            )
    return {"inventory": inventory_data, "low_stock_alerts": low_stock_alerts}


@app.get("/api/inventory/ledger")
def get_stock_ledger(db: Session = Depends(get_db)):
    movements = (
        db.query(StockLedger)
        .order_by(StockLedger.created_at.desc(), StockLedger.id.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": movement.id,
            "product_id": movement.product_id,
            "movement_type": movement.movement_type,
            "quantity_delta": movement.quantity_delta,
            "reference_id": movement.reference_id,
            "idempotency_key": movement.idempotency_key,
            "created_at": movement.created_at,
        }
        for movement in movements
    ]


@app.post("/api/messages", response_model=APIResponse)
async def ingest_message(event: InboundMessageEvent, db: Session = Depends(get_db)):
    existing_message = (
        db.query(InboundMessage)
        .filter(
            InboundMessage.source == event.source,
            InboundMessage.external_message_id == event.external_message_id,
        )
        .first()
    )
    if existing_message:
        existing_order = (
            db.query(StoredOrder)
            .filter(
                StoredOrder.source == event.source,
                StoredOrder.inbound_message_id == event.external_message_id,
            )
            .first()
        )
        return APIResponse(
            success=True,
            message="Duplicate message ignored.",
            data={
                "message_id": event.external_message_id,
                "status": "DUPLICATE",
                "order_id": existing_order.id if existing_order else None,
            },
        )

    try:
        extraction: GemmaExtractionResponse = await call_gemma(event.text)
    except Exception as exc:
        logger.exception("Gemma extraction failed for message %s", event.external_message_id)
        raise HTTPException(status_code=503, detail="Message extraction service is unavailable") from exc

    order_items = []
    if extraction.intent != "PLACE_ORDER":
        raise HTTPException(status_code=422, detail="Message did not contain an order")
    if not extraction.items:
        raise HTTPException(status_code=422, detail="No order items could be extracted")

    needs_review = False
    for extracted_item in extraction.items:
        candidates = find_product_candidates(extracted_item.product_mention, db)
        resolved_product_id = None
        resolution_status = "UNKNOWN"
        item_needs_review = extracted_item.needs_review
        if len(candidates) == 1 and not item_needs_review:
            resolved_product_id = candidates[0].id
            resolution_status = "EXACT"
        elif len(candidates) > 1:
            resolution_status = "CANDIDATES"
            item_needs_review = True
        else:
            item_needs_review = True
        needs_review = needs_review or item_needs_review
        order_items.append(
            OrderItemDraft(
                product_mention=extracted_item.product_mention,
                source_text=extracted_item.source_text,
                resolved_product_id=resolved_product_id,
                requested_quantity=extracted_item.quantity,
                requested_unit=extracted_item.unit or "piece",
                needs_review=item_needs_review,
                resolution_status=resolution_status,
            )
        )

    order = OrderDraft(
        id=str(uuid.uuid4()),
        inbound_message_id=event.external_message_id,
        status=(
            OrderStatus.NEEDS_REVIEW
            if needs_review
            else OrderStatus.READY_FOR_CONFIRMATION
        ),
        items=order_items,
    )
    try:
        db.add(
            InboundMessage(
                source=event.source,
                external_message_id=event.external_message_id,
                payload=event.model_dump(mode="json"),
                created_at=event.received_at,
            )
        )
        db.add(
            StoredOrder(
                id=order.id,
                source=event.source,
                inbound_message_id=event.external_message_id,
                status=order.status.value,
                order_data=order.model_dump(mode="json"),
                created_at=order.created_at,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_order = (
            db.query(StoredOrder)
            .filter(
                StoredOrder.source == event.source,
                StoredOrder.inbound_message_id == event.external_message_id,
            )
            .first()
        )
        if existing_order is None:
            raise
        return APIResponse(
            success=True,
            message="Duplicate message ignored.",
            data={
                "message_id": event.external_message_id,
                "status": "DUPLICATE",
                "order_id": existing_order.id,
            },
        )

    return APIResponse(
        success=True,
        message="Message processed",
        data={
            "order_id": order.id,
            "status": order.status,
            "extraction": extraction.model_dump(mode="json"),
        },
    )


@app.get("/api/orders", response_model=APIResponse)
def list_orders(db: Session = Depends(get_db)):
    orders = (
        db.query(StoredOrder)
        .order_by(StoredOrder.created_at.desc())
        .all()
    )
    return APIResponse(
        success=True,
        message="Orders retrieved",
        data={
            "orders": [
                order.result_data or order.order_data
                for order in orders
            ]
        },
    )


@app.post("/api/orders/{order_id}/resolve", response_model=APIResponse)
def resolve_order_item(
    order_id: str,
    item_index: int,
    resolved_product_id: str,
    db: Session = Depends(get_db),
):
    stored_order, order = _load_order(db, order_id)
    if order.status == OrderStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Confirmed orders cannot be changed")
    if item_index < 0 or item_index >= len(order.items):
        raise HTTPException(status_code=400, detail="Invalid item index")
    if get_product(resolved_product_id, db) is None:
        raise HTTPException(status_code=404, detail="Active product not found")

    item = order.items[item_index]
    item.resolved_product_id = resolved_product_id
    item.resolution_status = "EXACT"
    item.needs_review = False
    order.status = (
        OrderStatus.READY_FOR_CONFIRMATION
        if all(
            not order_item.needs_review
            and order_item.resolution_status == "EXACT"
            for order_item in order.items
        )
        else OrderStatus.NEEDS_REVIEW
    )
    _save_order(stored_order, order)
    db.commit()
    return APIResponse(success=True, message="Item resolved", data=order.model_dump(mode="json"))


@app.post("/api/orders/{order_id}/confirm", response_model=APIResponse)
def confirm_order(order_id: str, db: Session = Depends(get_db)):
    stored_order, order = _load_order(db, order_id)
    if stored_order.result_data:
        return APIResponse(
            success=True,
            message="Order already confirmed",
            data=stored_order.result_data,
        )
    if order.status != OrderStatus.READY_FOR_CONFIRMATION or not order.items:
        raise HTTPException(status_code=400, detail="Order is not ready for confirmation")
    if any(
        item.needs_review
        or item.resolution_status != "EXACT"
        or not item.resolved_product_id
        for item in order.items
    ):
        raise HTTPException(status_code=400, detail="Resolve all order items before confirmation")

    deduction_items = []
    for index, item in enumerate(order.items):
        if not item.requested_quantity.is_integer():
            raise HTTPException(
                status_code=400,
                detail="Fractional quantities cannot be deducted from integer stock.",
            )
        deduction_items.append(
            OrderItemToDeduct(
                product_id=item.resolved_product_id,
                order_item_id=f"{order.id}_item_{index}",
                quantity=int(item.requested_quantity),
            )
        )

    subtotal, discount, total = calculate_order_totals(order, db)
    if any(get_product(item.product_id, db) is None for item in deduction_items):
        raise HTTPException(status_code=400, detail="An order product is no longer active")

    stock_result = confirm_stock_deduction(order.id, deduction_items, db)
    if not stock_result.success:
        raise HTTPException(status_code=409, detail=stock_result.error_message or "Stock deduction failed")

    order.status = OrderStatus.CONFIRMED
    result_data = order.model_dump(mode="json")
    result_data.update(
        {
            "subtotal_minor": subtotal,
            "discount_minor": discount,
            "total_minor": total,
            "ledger_entries": stock_result.ledger_entries,
        }
    )
    stored_order.status = order.status.value
    stored_order.order_data = order.model_dump(mode="json")
    stored_order.result_data = result_data
    db.commit()
    return APIResponse(success=True, message="Order confirmed", data=result_data)


@app.get("/api/orders/{order_id}/bill", response_class=HTMLResponse)
def get_order_bill(order_id: str, db: Session = Depends(get_db)):
    stored_order, order = _load_order(db, order_id)
    order_data = stored_order.result_data or order.model_dump(mode="json")
    if order.status == OrderStatus.CONFIRMED and "subtotal_minor" not in order_data:
        subtotal, discount, total = calculate_order_totals(order, db)
        order_data.update(
            {
                "subtotal_minor": subtotal,
                "discount_minor": discount,
                "total_minor": total,
            }
        )
    return HTMLResponse(content=generate_html_bill(order_data, db))

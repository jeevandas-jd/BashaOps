# backend/app/inventory_service.py
from collections import defaultdict
from datetime import datetime, timezone
from typing import List

from sqlalchemy import update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import Product, StockLedger
from .schemas import OrderItemToDeduct, StockDeductionResult


def confirm_stock_deduction(order_id: str, items: List[OrderItemToDeduct], db: Session) -> StockDeductionResult:
    ledger_entries = []
    quantities_by_product = defaultdict(int)
    new_items = []

    try:
        for item in items:
            idempotency_key = f"order:{order_id}:item:{item.order_item_id}:sale"
            existing_ledger = db.query(StockLedger).filter(
                StockLedger.idempotency_key == idempotency_key
            ).first()
            if existing_ledger:
                if (
                    existing_ledger.product_id != item.product_id
                    or existing_ledger.quantity_delta != -item.quantity
                ):
                    db.rollback()
                    return StockDeductionResult(
                        success=False,
                        error_message="An idempotency key already exists for different order data.",
                    )
                ledger_entries.append(idempotency_key)
                continue

            new_items.append((item, idempotency_key))
            quantities_by_product[item.product_id] += item.quantity

        for product_id, quantity in quantities_by_product.items():
            product = db.query(Product).filter(Product.id == product_id, Product.active == 1).first()
            if not product:
                db.rollback()
                return StockDeductionResult(
                    success=False,
                    error_message=f"Product {product_id} not found or inactive.",
                )

            result = db.execute(
                update(Product)
                .where(
                    Product.id == product_id,
                    Product.active == 1,
                    Product.stock_quantity >= quantity,
                )
                .values(stock_quantity=Product.stock_quantity - quantity)
            )
            if result.rowcount != 1:
                db.rollback()
                return StockDeductionResult(
                    success=False,
                    error_message=(
                        f"Insufficient stock for {product.name}. "
                        f"Available: {product.stock_quantity}, Requested: {quantity}"
                    ),
                )

        now = datetime.now(timezone.utc).isoformat()
        for item, idempotency_key in new_items:
            ledger_entry = StockLedger(
                product_id=item.product_id,
                movement_type="SALE",
                quantity_delta=-item.quantity,
                reference_type="order",
                reference_id=order_id,
                idempotency_key=idempotency_key,
                reason=f"Order {order_id} confirmed",
                created_at=now,
            )
            db.add(ledger_entry)
            ledger_entries.append(idempotency_key)

        db.commit()

        low_stock_alerts = [
            product.id
            for product in db.query(Product)
            .filter(
                Product.id.in_(quantities_by_product),
                Product.stock_quantity <= Product.low_stock_threshold,
            )
            .all()
        ]

        return StockDeductionResult(
            success=True,
            ledger_entries=ledger_entries,
            low_stock_alerts=low_stock_alerts
        )
    except IntegrityError:
        db.rollback()
        return StockDeductionResult(
            success=False,
            error_message="Duplicate transaction detected or database constraint violated.",
        )
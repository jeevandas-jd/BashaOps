# backend/app/inventory_service.py
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import Product, StockLedger
from .schemas import OrderItemToDeduct, StockDeductionResult

def confirm_stock_deduction(order_id: str, items: List[OrderItemToDeduct], db: Session) -> StockDeductionResult:
    """
    ATOMIC TRANSACTION:
    1. Checks if stock is sufficient for all items.
    2. Generates idempotency keys.
    3. Inserts into stock_ledger.
    4. Updates materialized stock_quantity in products table.
    5. Returns low stock alerts.
    If any item fails, the ENTIRE transaction rolls back.
    """
    ledger_entries = []
    low_stock_alerts = []
    
    try:
        # --- PHASE 1: Validate stock availability for ALL items first ---
        # We do this before touching anything to ensure we don't deduct half an order.
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                return StockDeductionResult(
                    success=False, 
                    error_message=f"Product {item.product_id} not found."
                )
            if product.stock_quantity < item.quantity:
                return StockDeductionResult(
                    success=False, 
                    error_message=f"Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {item.quantity}"
                )

        # --- PHASE 2: Process deductions and create ledger entries ---
        for item in items:
            # CRITICAL: The idempotency key prevents double deduction
            idempotency_key = f"order:{order_id}:item:{item.order_item_id}:sale"
            
            # Check if this exact deduction already happened
            existing_ledger = db.query(StockLedger).filter(
                StockLedger.idempotency_key == idempotency_key
            ).first()
            
            if existing_ledger:
                # Already processed! Skip deduction, but record the key so the caller knows it succeeded.
                ledger_entries.append(idempotency_key)
                continue

            # Create the immutable ledger entry
            ledger_entry = StockLedger(
                product_id=item.product_id,
                movement_type="SALE",
                quantity_delta=-item.quantity, # Negative because it's a sale
                reference_type="order",
                reference_id=order_id,
                idempotency_key=idempotency_key,
                reason=f"Order {order_id} confirmed"
            )
            db.add(ledger_entry)
            ledger_entries.append(idempotency_key)

            # Update the materialized stock quantity on the product
            product = db.query(Product).filter(Product.id == item.product_id).first()
            product.stock_quantity -= item.quantity

        # --- PHASE 3: Commit the entire transaction at once ---
        # If anything fails before this line, nothing is saved to the database.
        db.commit()

        # --- PHASE 4: Check for low stock alerts after successful deduction ---
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product.stock_quantity <= product.low_stock_threshold:
                low_stock_alerts.append(product.id)

        return StockDeductionResult(
            success=True,
            ledger_entries=ledger_entries,
            low_stock_alerts=low_stock_alerts
        )

    except IntegrityError:
        # This catches race conditions where two requests try to use the same idempotency key simultaneously
        db.rollback()
        return StockDeductionResult(
            success=False,
            error_message="Duplicate transaction detected or database constraint violated."
        )
    except Exception as e:
        # Catch-all for any other unexpected errors
        db.rollback()
        return StockDeductionResult(
            success=False,
            error_message=f"An unexpected error occurred: {str(e)}"
        )
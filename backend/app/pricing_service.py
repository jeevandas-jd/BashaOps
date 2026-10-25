# backend/app/pricing_service.py
from app.schemas import OrderDraft
from app.catalogue_service import get_product
from sqlalchemy.orm import Session

def calculate_order_totals(order: OrderDraft, db: Session) -> tuple:
    """Calculates deterministic pricing using the database catalogue."""
    subtotal_minor = 0
    for item in order.items:
        if item.resolved_product_id and item.resolution_status == "EXACT":
            product = get_product(item.resolved_product_id, db)
            if product:
                line_total = int(product.unit_price_minor * item.requested_quantity)
                subtotal_minor += line_total
                
    discount_minor = 0
    total_minor = subtotal_minor - discount_minor
    
    return subtotal_minor, discount_minor, total_minor
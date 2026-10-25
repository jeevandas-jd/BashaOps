# backend/app/pricing_service.py
from app.schemas import OrderDraft, CatalogueProduct
from typing import List, Tuple
from app.catalogue_service import get_product

def calculate_order_totals(order: OrderDraft) -> Tuple[int, int, int]:
    """
    Calculates subtotal and total in integer paise.
    Returns: (subtotal_minor, discount_minor, total_minor)
    """
    subtotal_minor = 0
    
    for item in order.items:
        # Only calculate for items that have been exactly resolved
        if item.resolved_product_id and item.resolution_status == "EXACT":
            product = get_product(item.resolved_product_id)
            if product:
                # MVP Assumption: requested_unit matches base_unit for exact matches.
                # line_total = unit_price_minor * requested_quantity
                line_total = int(product.unit_price_minor * item.requested_quantity)
                subtotal_minor += line_total
    
    discount_minor = 0
    total_minor = subtotal_minor - discount_minor
    
    return subtotal_minor, discount_minor, total_minor
# backend/app/catalogue_service.py
from app.schemas import CatalogueProduct
from typing import List, Optional

# MOCK CATALOGUE (Developer B will replace this with DB queries)
# Prices are in integer paise (e.g., 25000 = ₹250.00)
MOCK_CATALOGUE = [
    CatalogueProduct(
        id="prod_001", sku="ATTA-5KG", name="Atta", brand="Aashirvaad", 
        variant=None, pack_size="5kg", base_unit="kg", unit_price_minor=25000, stock_quantity=50
    ),
    CatalogueProduct(
        id="prod_002", sku="BUTTER-100G", name="Amul Butter", brand="Amul", 
        variant="small", pack_size="100g", base_unit="piece", unit_price_minor=5500, stock_quantity=100
    ),
    CatalogueProduct(
        id="prod_003", sku="EGG-DOZ", name="Eggs", brand="Local", 
        variant=None, pack_size="12 pieces", base_unit="piece", unit_price_minor=700, stock_quantity=200
    )
]

def find_product_candidates(mention: str) -> List[CatalogueProduct]:
    """Finds products matching the mention. MVP uses simple substring matching."""
    mention_lower = mention.lower()
    candidates = []
    for p in MOCK_CATALOGUE:
        if p.name.lower() in mention_lower or (p.brand and p.brand.lower() in mention_lower):
            candidates.append(p)
    
    # Fallback for demo: if no match, return all so the UI has something to show
    return candidates if candidates else MOCK_CATALOGUE

def get_product(product_id: str) -> Optional[CatalogueProduct]:
    """Fetches a single product by ID."""
    for p in MOCK_CATALOGUE:
        if p.id == product_id:
            return p
    return None

def confirm_stock_deduction(order_id: str, items: list) -> dict:
    """
    Mock atomic stock deduction. 
    Developer B will implement the real DB transaction with idempotency keys here.
    """
    # In a real app, this checks stock and deducts atomically.
    return {
        "success": True, 
        "ledger_entries": [f"ledger_{order_id}_sale"], 
        "low_stock_alerts": []
    }
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
import re
from typing import List, Optional
from sqlalchemy.orm import Session

from .database import Product, ProductAlias
from .schemas import CatalogueProduct

def normalize_text(text: str) -> str:
    """Lowercases and removes punctuation for safe matching."""
    return re.sub(r'[^\w\s]', '', text.lower()).strip()

def find_product_candidates(mention: str, db: Session) -> List[CatalogueProduct]:
    """
    Matches a raw text mention against product names and aliases.
    Returns a list of candidate products for Developer A to review.
    """
    normalized_mention = normalize_text(mention)
    tokens = set(normalized_mention.split())
    
    candidates = []
    seen_ids = set()

    # 1. Exact match on alias (Highest confidence)
    exact_aliases = db.query(ProductAlias).filter(
        ProductAlias.alias_normalized == normalized_mention
    ).all()
    for alias in exact_aliases:
        if alias.product_id not in seen_ids:
            candidates.append(alias.product)
            seen_ids.add(alias.product_id)

    # 2. Token match on alias (e.g., mention is "amul venna", tokens are "amul", "venna")
    if not candidates and tokens:
        token_aliases = db.query(ProductAlias).filter(
            ProductAlias.alias_normalized.in_(tokens)
        ).all()
        for alias in token_aliases:
            if alias.product_id not in seen_ids:
                candidates.append(alias.product)
                seen_ids.add(alias.product_id)

    # 3. Fallback: Partial match on product name
    if not candidates:
        name_matches = db.query(Product).filter(
            Product.name.ilike(f"%{normalized_mention}%")
        ).all()
        for prod in name_matches:
            if prod.id not in seen_ids:
                candidates.append(prod)
                seen_ids.add(prod.id)

    # Convert SQLAlchemy models to Pydantic schemas
    return [CatalogueProduct.model_validate(p) for p in candidates if p.active]

def get_product(product_id: str, db: Session) -> Optional[CatalogueProduct]:
    """Fetches a single product by ID for pricing and validation."""
    product = db.query(Product).filter(Product.id == product_id, Product.active == 1).first()
    if not product:
        return None
    return CatalogueProduct.model_validate(product)

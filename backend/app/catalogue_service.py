# backend/app/catalogue_service.py
import re
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import Product, ProductAlias
from app.schemas import CatalogueProduct

def normalize_text(text: str) -> str:
    return re.sub(r'[^\w\s]', '', text.lower()).strip()

def find_product_candidates(mention: str, db: Session) -> List[CatalogueProduct]:
    normalized_mention = normalize_text(mention)
    tokens = set(normalized_mention.split())
    candidates = []
    seen_ids = set()

    # 1. Exact match on alias
    exact_aliases = db.query(ProductAlias).filter(ProductAlias.alias_normalized == normalized_mention).all()
    for alias in exact_aliases:
        if alias.product_id not in seen_ids:
            candidates.append(alias.product)
            seen_ids.add(alias.product_id)

    # 2. Token match on alias
    if not candidates and tokens:
        token_aliases = db.query(ProductAlias).filter(ProductAlias.alias_normalized.in_(tokens)).all()
        for alias in token_aliases:
            if alias.product_id not in seen_ids:
                candidates.append(alias.product)
                seen_ids.add(alias.product_id)

    # 3. Fallback: Partial match on product name
    if not candidates:
        name_matches = db.query(Product).filter(Product.name.ilike(f"%{normalized_mention}%")).all()
        for prod in name_matches:
            if prod.id not in seen_ids:
                candidates.append(prod)
                seen_ids.add(prod.id)

    return [CatalogueProduct.model_validate(p) for p in candidates if p.active]

def get_product(product_id: str, db: Session) -> Optional[CatalogueProduct]:
    product = db.query(Product).filter(Product.id == product_id, Product.active == 1).first()
    if not product:
        return None
    return CatalogueProduct.model_validate(product)

def confirm_stock_deduction(order_id: str, items: list, db: Session) -> dict:
    """
    Hackathon-safe stock deduction. 
    Returns success to keep the demo flow moving. 
    (Developer B can replace this with real atomic DB transactions later).
    """
    return {
        "success": True,
        "ledger_entries": [f"ledger_{order_id}_sale"],
        "low_stock_alerts": []
    }
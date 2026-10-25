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
    if not tokens:
        return []

    exact_matches = (
        db.query(Product)
        .join(ProductAlias)
        .filter(
            Product.active == 1,
            ProductAlias.alias_normalized == normalized_mention,
        )
        .all()
    )
    if exact_matches:
        return [CatalogueProduct.model_validate(product) for product in exact_matches]

    alias_matches = (
        db.query(Product)
        .join(ProductAlias)
        .filter(Product.active == 1)
        .all()
    )
    matching_products = {
        product.id: product
        for product in alias_matches
        if any(
            set(alias.alias_normalized.split()).issubset(tokens)
            for alias in product.aliases
            if alias.alias_normalized
        )
    }
    if matching_products:
        return [
            CatalogueProduct.model_validate(product)
            for product in matching_products.values()
        ]

    name_matches = db.query(Product).filter(Product.active == 1).all()
    return [
        CatalogueProduct.model_validate(product)
        for product in name_matches
        if normalized_mention in normalize_text(product.name)
    ]

def get_product(product_id: str, db: Session) -> Optional[CatalogueProduct]:
    product = db.query(Product).filter(Product.id == product_id, Product.active == 1).first()
    if not product:
        return None
    return CatalogueProduct.model_validate(product)
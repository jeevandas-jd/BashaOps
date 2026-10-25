# scripts/seed_demo.py
import sys
import re
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_dir))

from app.database import Product, ProductAlias, SessionLocal, init_db

def seed():
    print("Initializing database...")
    init_db()
    db = SessionLocal()

    products_data = [
        {
            "id": "prod_001", "sku": "ATTA-01", "name": "Wheat Flour (Atta)", "brand": "Aashirvaad",
            "base_unit": "kg", "unit_price_minor": 4500, "stock_quantity": 50, "low_stock_threshold": 10,
            "aliases": ["atta", "wheat flour", "godhumba powder", "godhumba"]
        },
        {
            "id": "prod_002", "sku": "BUTTER-AMUL-S", "name": "Amul Butter Small", "brand": "Amul",
            "variant": "small", "base_unit": "pack", "unit_price_minor": 5500, "stock_quantity": 20, "low_stock_threshold": 5,
            "aliases": ["amul butter", "venna", "butter cheruth", "cheruth butter"]
        },
        {
            "id": "prod_003", "sku": "EGG-01", "name": "Eggs", "brand": "Local Farm",
            "base_unit": "piece", "unit_price_minor": 700, "stock_quantity": 100, "low_stock_threshold": 20,
            "aliases": ["egg", "eggs", "ande", "mutta"]
        },
        {
            "id": "prod_004", "sku": "MAGGI-10", "name": "Maggi Rs 10 Pack", "brand": "Nestle",
            "variant": "10rs", "base_unit": "pack", "unit_price_minor": 1000, "stock_quantity": 8, "low_stock_threshold": 10, # Intentionally low for demo!
            "aliases": ["maggi", "noodles", "10rs maggi", "10 rupee maggi"]
        }
    ]

    print("Seeding products and aliases...")
    for p_data in products_data:
        aliases = p_data.pop("aliases")
        
        # Idempotency: Check if product already exists
        existing = db.query(Product).filter(Product.id == p_data["id"]).first()
        if not existing:
            product = Product(**p_data)
            db.add(product)
            db.commit()
            db.refresh(product)
            
            for alias in aliases:
                norm_alias = re.sub(r'[^\w\s]', '', alias.lower()).strip()
                db.add(ProductAlias(product_id=product.id, alias_normalized=norm_alias))
            db.commit()
            print(f"Seeded: {product.name} (Stock: {product.stock_quantity})")
        else:
            print(f"Skipped: {existing.name} (already exists)")

    db.close()
    print("\nSeeding complete! You can now start the backend.")

if __name__ == "__main__":
    seed()
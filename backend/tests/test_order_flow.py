import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.catalogue_service import find_product_candidates
from app.database import (
    Base,
    Product,
    ProductAlias,
    StockLedger,
    _migrate_existing_schema,
    get_db,
)
from app.schemas import (
    ExtractedItem,
    GemmaExtractionResponse,
    OrderItemToDeduct,
)
from app.inventory_service import confirm_stock_deduction


@pytest.fixture
def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with testing_session() as db:
        db.add(
            Product(
                id="prod_test",
                sku="TEST-01",
                name="Amul Butter Small",
                brand="Amul",
                variant="small",
                base_unit="pack",
                unit_price_minor=5500,
                stock_quantity=10,
                low_stock_threshold=2,
                active=1,
            )
        )
        db.add(
            ProductAlias(
                product_id="prod_test",
                alias_normalized="amul butter",
            )
        )
        db.add(
            ProductAlias(
                product_id="prod_test",
                alias_normalized="butter cheruth",
            )
        )
        db.commit()

    yield testing_session
    main.app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_catalogue_matches_multiword_alias(database):
    with database() as db:
        candidates = find_product_candidates("Amul butter cheruth", db)
    assert [candidate.id for candidate in candidates] == ["prod_test"]


def test_existing_order_table_gets_source_migration():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE orders ("
                "id VARCHAR PRIMARY KEY, inbound_message_id VARCHAR NOT NULL, "
                "status VARCHAR NOT NULL, order_data JSON NOT NULL, "
                "result_data JSON, created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO orders "
                "(id, inbound_message_id, status, order_data, created_at) "
                "VALUES ('legacy', 'legacy-message', 'READY_FOR_CONFIRMATION', '{}', '2026-10-25')"
            )
        )
    _migrate_existing_schema(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("orders")}
    assert "source" in columns
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT source FROM orders WHERE id = 'legacy'")
        ).scalar_one() == "simulator"
    engine.dispose()


def test_api_persists_order_and_confirmation_updates_inventory(database, monkeypatch):
    async def fake_gemma(_):
        return GemmaExtractionResponse(
            intent="PLACE_ORDER",
            language="en",
            items=[
                ExtractedItem(
                    product_mention="Amul butter",
                    quantity=2,
                    unit="pack",
                    source_text="2 Amul butter",
                )
            ],
        )

    monkeypatch.setattr(main, "call_gemma", fake_gemma)
    client = TestClient(main.app)
    message = {
        "source": "simulator",
        "external_message_id": "message-test-1",
        "conversation_id": "conversation-test",
        "sender_id": "tester",
        "text": "2 Amul butter",
    }

    response = client.post("/api/messages", json=message)
    assert response.status_code == 200
    order_id = response.json()["data"]["order_id"]
    assert response.json()["data"]["status"] == "READY_FOR_CONFIRMATION"

    duplicate = client.post("/api/messages", json=message)
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["status"] == "DUPLICATE"
    assert duplicate.json()["data"]["order_id"] == order_id

    persisted_orders = client.get("/api/orders").json()["data"]["orders"]
    assert [order["id"] for order in persisted_orders] == [order_id]

    confirmed = client.post(f"/api/orders/{order_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["total_minor"] == 11000

    with database() as db:
        product = db.query(Product).filter(Product.id == "prod_test").one()
        ledger = db.query(StockLedger).all()
        assert product.stock_quantity == 8
        assert len(ledger) == 1
        assert ledger[0].quantity_delta == -2

    repeated_confirmation = client.post(f"/api/orders/{order_id}/confirm")
    assert repeated_confirmation.status_code == 200
    with database() as db:
        assert db.query(StockLedger).count() == 1
        assert db.query(Product).filter(Product.id == "prod_test").one().stock_quantity == 8


def test_stock_deduction_is_atomic_for_repeated_product(database):
    with database() as db:
        result = confirm_stock_deduction(
            "insufficient-order",
            [
                OrderItemToDeduct(
                    product_id="prod_test",
                    order_item_id="item-1",
                    quantity=6,
                ),
                OrderItemToDeduct(
                    product_id="prod_test",
                    order_item_id="item-2",
                    quantity=6,
                ),
            ],
            db,
        )
        assert not result.success
        assert "Insufficient stock" in result.error_message
        assert db.query(Product).filter(Product.id == "prod_test").one().stock_quantity == 10
        assert db.query(StockLedger).count() == 0


def test_fractional_stock_quantity_is_rejected_without_deduction(database, monkeypatch):
    async def fake_gemma(_):
        return GemmaExtractionResponse(
            intent="PLACE_ORDER",
            language="en",
            items=[
                ExtractedItem(
                    product_mention="Amul butter",
                    quantity=1.5,
                    unit="pack",
                    source_text="1.5 Amul butter",
                )
            ],
        )

    monkeypatch.setattr(main, "call_gemma", fake_gemma)
    client = TestClient(main.app)
    response = client.post(
        "/api/messages",
        json={
            "source": "simulator",
            "external_message_id": "message-fractional",
            "conversation_id": "conversation-test",
            "sender_id": "tester",
            "text": "1.5 Amul butter",
        },
    )
    order_id = response.json()["data"]["order_id"]
    confirmation = client.post(f"/api/orders/{order_id}/confirm")
    assert confirmation.status_code == 400
    assert "Fractional quantities" in confirmation.json()["detail"]

    with database() as db:
        assert db.query(Product).filter(Product.id == "prod_test").one().stock_quantity == 10
        assert db.query(StockLedger).count() == 0

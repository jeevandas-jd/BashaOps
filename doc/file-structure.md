# BhashaOps — File Structure and Developer Handoff Guide

**Purpose:** This document defines the proposed repository layout, the responsibility of each file, the ownership split for two developers, and the contracts they must agree on before coding.

**Project goal:** Turn informal Malayalam, Manglish, and English kirana-store messages into reviewable orders, calculate bills using deterministic code, and update inventory exactly once after confirmation.

**Primary demo flow:** Message → Gemma 4 extraction → schema validation → catalogue matching → operator review → bill → order confirmation → one stock deduction → stock ledger / low-stock alert.

> Keep the first version small and runnable. A working simulator-based end-to-end flow is more valuable than several incomplete integrations.

---

## 1. Repository Structure

Use this as the target structure. It is a design contract, not a requirement to create every file immediately. Create files when the corresponding feature is implemented.

```text
bhashaops/
├── README.md
├── architecture-design-doc.md
├── idea-plan.md
├── workload-split.md
├── file-structure.md
├── .gitignore
├── .env.example
├── .gitkeep
│
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── messages.py
│   │   │   ├── products.py
│   │   │   ├── orders.py
│   │   │   └── inventory.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── errors.py
│   │   │   ├── logging_config.py
│   │   │   └── idempotency.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── repositories.py
│   │   │   └── init_db.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── messages.py
│   │   │   ├── interpretation.py
│   │   │   ├── products.py
│   │   │   ├── orders.py
│   │   │   └── inventory.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── message_service.py
│   │   │   ├── gemma_service.py
│   │   │   ├── interpretation_service.py
│   │   │   ├── catalogue_service.py
│   │   │   ├── order_service.py
│   │   │   ├── pricing_service.py
│   │   │   ├── inventory_service.py
│   │   │   ├── bill_service.py
│   │   │   └── alert_service.py
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── simulator.py
│   │   │   └── whatsapp_web.py
│   │   ├── prompts/
│   │   │   └── order_extraction.txt
│   │   └── seed/
│   │       ├── products.json
│   │       └── demo_messages.json
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_gemma_service.py
│       ├── test_interpretation.py
│       ├── test_catalogue.py
│       ├── test_pricing.py
│       ├── test_order_flow.py
│       ├── test_inventory_idempotency.py
│       └── test_message_deduplication.py
│
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── api.js
│   └── README.md
│
├── scripts/
│   ├── setup.sh
│   ├── run_demo.sh
│   ├── seed_demo.py
│   └── reset_demo.py
│
├── docs/
│   ├── api-contract.md
│   ├── demo-script.md
│   └── test-cases.md
│
└── .github/
    └── pull_request_template.md
```

### Simplify if the clock is running

For a four-hour build, you may start with fewer modules:

```text
backend/app/
├── main.py
├── config.py
├── database.py
├── models.py
├── schemas.py
├── gemma_service.py
├── catalogue_service.py
├── order_service.py
├── inventory_service.py
└── api.py
```

Split files into the fuller layout only when it makes parallel work or debugging easier. Do not spend 30 minutes moving files around before the first working request.

---

## 2. Root-Level Files

| File | Purpose | Owner |
|---|---|---|
| `README.md` | Project overview, features, setup, demo instructions, limitations | Shared; Developer A coordinates |
| `architecture-design-doc.md` | System components, data model, API and safety decisions | Shared |
| `idea-plan.md` | Product idea and scope | Shared |
| `workload-split.md` | Time plan and work ownership | Shared |
| `file-structure.md` | This handoff guide | Shared |
| `.gitignore` | Ignore secrets, sessions, local DBs, caches and generated files | Developer A creates; both review |
| `.env.example` | Documents required configuration without real secrets | Shared |
| `backend/requirements.txt` | Python dependencies for a fast setup | Developer A |
| `backend/pyproject.toml` | Optional project/tool configuration; avoid maintaining duplicate dependency lists inconsistently | Developer A |
| `docs/api-contract.md` | Exact request/response examples both developers implement against | Both; agree before parallel API work |
| `docs/demo-script.md` | Short repeatable presentation flow | Shared; finalize near the end |

**Dependency-file rule:** To avoid conflicting dependency lists, choose one source of truth. Under time pressure, use `requirements.txt`; keep `pyproject.toml` only for project/tool settings unless the team intentionally switches to a single Poetry/uv workflow.

---

## 3. Backend File Responsibilities

### 3.1 Application entry and configuration

#### `backend/app/main.py` — Developer A
- Create the FastAPI app.
- Register routers from `api/`.
- Configure startup initialization if needed.
- Expose `/api/health`.
- Configure CORS for the local frontend only.
- Do not put the full order-processing or inventory logic in this file.

**Acceptance:** `uvicorn app.main:app --reload` starts without a model server being available.

#### `backend/app/config.py` — Developer A
- Read environment variables.
- Configure database path, model base URL, model identifier, request timeout, and demo mode.
- Provide safe defaults for local development where possible.
- Never place API keys or personal credentials directly in source code.

Suggested variables:

```dotenv
APP_ENV=development
DATABASE_URL=sqlite:///./bhashaops.db
GEMMA_BASE_URL=http://localhost:11434
GEMMA_MODEL=replace-with-verified-model-tag
DEMO_MODE=true
```

The model tag above is deliberately a placeholder. Verify the exact model identifier and runtime support on the demo machine.

### 3.2 API routers

Each router should be thin: parse input, call a service, return a schema. Do not duplicate business logic inside endpoints.

#### `backend/app/api/health.py` — Developer A
- `GET /api/health`
- Return service status and whether configuration is present.
- Do not leak secrets or full environment values.

#### `backend/app/api/messages.py` — Developer A
- `POST /api/messages` — ingest a normalized message event.
- `GET /api/messages` — list recent inbox messages.
- `GET /api/messages/{message_id}` — show status and interpretation.
- Optional: `POST /api/messages/{message_id}/interpret` — retry processing.
- Call `message_service.py`.
- Handle duplicate message IDs as idempotent requests.

#### `backend/app/api/products.py` — Developer B
- `GET /api/products` — list/search products.
- `POST /api/products` — create a product if required.
- `PATCH /api/products/{product_id}` — update allowed fields.
- Call `catalogue_service.py`.
- Validate price, unit, pack size, stock and threshold.
- Do not accept model-generated product names as trusted product IDs.

#### `backend/app/api/orders.py` — Developer A owns endpoints; both agree on contract
- `GET /api/orders` — list orders.
- `GET /api/orders/{order_id}` — order details.
- `POST /api/orders/{order_id}/resolve` — resolve ambiguous items.
- `POST /api/orders/{order_id}/confirm` — confirm order and trigger the inventory transaction.
- `POST /api/orders/{order_id}/cancel` — apply legal cancellation rules.
- Call `order_service.py`; never deduct stock directly in the router.

#### `backend/app/api/inventory.py` — Developer B
- `GET /api/inventory` — current stock and low-stock status.
- `GET /api/inventory/ledger` — stock movement history.
- `POST /api/inventory/receipts` — record a verified receipt.
- Call `inventory_service.py`.
- Do not increase stock for a supplier message that has not been verified.

### 3.3 Database layer

#### `backend/app/db/database.py` — Developer B
- Create and configure the SQLite connection/session.
- Provide a request-scoped session or clear transaction helper.
- Enable foreign keys for SQLite.
- Make transaction boundaries explicit.
- Keep database access separate from API handlers.

#### `backend/app/db/models.py` — Developer B
Define the persistence models/tables:
- `InboundMessage`
- `Interpretation`
- `Product`
- `ProductAlias`
- `Order`
- `OrderItem`
- `StockLedger`
- Optional `Task` only if Chat2Ops is attempted.

Minimum constraints:
- Unique `(source, external_message_id)` on inbound messages.
- Unique SKU for products.
- Unique idempotency key on stock ledger.
- Foreign keys for order items, interpretations and ledger references.
- Store currency amounts as integer minor units (INR paise) to avoid floating-point money errors.

#### `backend/app/db/repositories.py` — Developer B
- Provide small database operations such as get product, search aliases, insert message, fetch order, and list ledger entries.
- If time is short, repositories can be functions in service modules, but use one consistent pattern.
- Do not let Developer A and Developer B invent different table or field names independently.

#### `backend/app/db/init_db.py` — Developer B
- Initialize tables or run the chosen migration setup.
- Seed a fresh local demo database when requested.
- Never silently reset a database containing data.
- Keep reset behavior in an explicit demo script.

### 3.4 Schemas / request-response contracts

Use Pydantic schemas so both developers agree on names and types.

#### `backend/app/schemas/messages.py` — Developer A
Normalized message input:

```json
{
  "source": "simulator",
  "external_message_id": "demo-msg-0001",
  "conversation_id": "demo-customer-01",
  "sender_id": "customer-demo-01",
  "text": "chetta 2 kilo atta, 6 ande"
}
```

Rules:
- `source`, `external_message_id`, and `text` are required.
- Bound message length.
- Treat identifiers as strings.
- Do not use the message text as a SQL fragment or HTML.

#### `backend/app/schemas/interpretation.py` — Developer A
Represent the validated Gemma result. The model proposes product mentions and quantities, not catalogue IDs, prices, totals, or stock movements.

```json
{
  "schema_version": "1.0",
  "intent": "PLACE_ORDER",
  "language": "ml-en-mixed",
  "items": [
    {
      "product_mention": "atta",
      "quantity": 2,
      "unit": "kg",
      "variant": null,
      "pack_size_hint": null,
      "source_text": "2 kilo atta",
      "needs_review": false,
      "clarification_question": null
    }
  ],
  "general_notes": []
}
```

#### `backend/app/schemas/products.py` — Developer B
Suggested product fields:
- `sku`
- `name`
- `brand`
- `variant`
- `pack_size`
- `base_unit`
- `unit_price_minor`
- `stock_quantity`
- `low_stock_threshold`
- `aliases`

Decide how fractional units work. For the MVP, integer quantities and clearly defined units are simpler; support fractional quantities only if the service validates conversions correctly.

#### `backend/app/schemas/orders.py` — Both
Order response should include:
- `id`
- `status`
- `items`
- `subtotal_minor`
- `discount_minor`
- `total_minor`
- `currency`
- `needs_review`
- `created_at`
- `confirmed_at`

Each order item should include the resolved product ID/name, requested quantity/unit, stored price snapshot, line total, and resolution status.

#### `backend/app/schemas/inventory.py` — Developer B
- Inventory response: product ID, name, current stock, threshold, low-stock boolean.
- Ledger response: movement ID, product ID, movement type, quantity delta, reference, reason and timestamp.
- Receipt input must identify the product, received quantity, and operator confirmation.

### 3.5 Services

#### `backend/app/services/message_service.py` — Developer A
- Accept a normalized message event.
- Insert the message with the unique provider ID.
- If duplicate, return the existing message/result.
- Call the interpretation pipeline for a new message.
- Persist processing status and safe error details.
- Create a draft order only when parsing and matching produce enough information to do so.

#### `backend/app/services/gemma_service.py` — Developer A
- Communicate with the configured local Gemma runtime.
- Load the prompt from `prompts/order_extraction.txt`.
- Send only the information required for extraction.
- Parse the returned JSON and enforce timeouts.
- Handle runtime errors, empty output and invalid JSON.
- Do not let the model call database mutations or invoke shell commands.
- Provide a clear manual-review fallback.

**Must be tested early:** Before building the full workflow, make one real model call with a sample Malayalam/Manglish message and confirm the model returns usable JSON within demo time limits.

#### `backend/app/services/interpretation_service.py` — Developer A
- Validate the Gemma response using Pydantic.
- Normalize known unit spellings.
- Pass product mentions to the catalogue matcher.
- Mark unknown or ambiguous items as requiring review.
- Preserve the original source text for operator inspection.
- Never trust model confidence alone to approve a product match.

#### `backend/app/services/catalogue_service.py` — Developer B
- Search canonical product names and aliases.
- Normalize case, whitespace and common spelling variations.
- Return a structured match result: `EXACT`, `CANDIDATES`, `UNKNOWN`, or `INCOMPATIBLE_UNIT`.
- Keep product ID assignment deterministic.
- Provide stock and price data to the order service.
- Avoid automatically selecting among multiple pack sizes.

#### `backend/app/services/pricing_service.py` — Developer A; catalogue contract agreed with B
- Calculate all prices in integer paise.
- Use the price snapshot stored on the order item.
- Validate quantity and unit conversion.
- Compute line totals and grand total in code.
- Do not use totals generated by Gemma.
- If a conversion is unclear, stop and request review.

#### `backend/app/services/order_service.py` — Developer A, inventory integration co-owned
- Create draft orders and order items.
- Resolve order items using verified catalogue product IDs.
- Enforce valid order state transitions.
- Call pricing service to calculate totals.
- Call inventory confirmation operation when confirming.
- Ensure confirmation and stock deduction are one atomic operation, or use a clearly defined transaction helper shared with inventory service.
- Return the already-confirmed order on repeated confirmation rather than deducting stock again.

#### `backend/app/services/inventory_service.py` — Developer B
- Read current stock.
- Recheck stock at confirmation time.
- Create stock ledger movements with unique idempotency keys.
- Update current stock in the same transaction as ledger insertion.
- Reject insufficient stock unless an explicit partial-order feature is implemented.
- Record verified receipts and adjustments with reasons.
- Trigger low-stock evaluation.
- Never directly trust a model result as an inventory command.

**Critical integration rule:** Developer A must not implement a second stock-deduction path. Developer B must expose one documented confirmation function or transaction operation for `order_service.py` to use.

#### `backend/app/services/bill_service.py` — Developer A
- Generate bill/packing data from the saved order.
- Render HTML or a simple printable page.
- Use stored price snapshots.
- Do not generate a bill for an unresolved or unconfirmed order as if it were final.
- Label drafts clearly.

#### `backend/app/services/alert_service.py` — Developer B
- Check whether stock is at or below the configured threshold.
- Avoid repeated duplicate alert records for an unchanged condition.
- Return alert data to the dashboard.

### 3.6 Adapters

#### `backend/app/adapters/base.py` — Developer A
Define a small adapter interface with a normalized event format. Both live messaging and the simulator must use the same message ingestion path.

#### `backend/app/adapters/simulator.py` — Developer A
- Accept text through the frontend or a demo script.
- Generate a unique demo message ID for each new submitted message.
- Allow a test to intentionally replay the same ID to verify deduplication.
- This is required even if WhatsApp is planned.

#### `backend/app/adapters/whatsapp_web.py` — Developer A; optional
- Only implement after simulator-to-order-to-stock works.
- Convert incoming WhatsApp events to the normalized event.
- Do not put business logic in the adapter.
- Keep authentication/session files out of Git.
- Use only with a dedicated test account and after checking event rules and risks; `whatsapp-web.js` is unofficial and can break.
- If integration is unstable, disable it and demo with the simulator.

### 3.7 Prompt and seed data

#### `backend/app/prompts/order_extraction.txt` — Developer A
Include:
- A clear extraction-only role.
- The exact schema.
- Examples in Malayalam script, Manglish, English, and mixed language.
- Instructions to preserve ambiguity rather than guess.
- Instructions to output JSON only.
- A reminder that prices, stock, catalogue IDs and order confirmation are outside the model's authority.

#### `backend/app/seed/products.json` — Developer B
Use a small but useful catalogue (around 10–20 items). Include:
- Canonical product name and SKU.
- Brand and variant.
- Pack size and base unit.
- Unit price in paise.
- Initial stock and low-stock threshold.
- Malayalam/Manglish/English aliases where appropriate.

Keep aliases explicit and testable. Avoid adding a product with ambiguous pack sizes unless the demo intentionally demonstrates clarification.

#### `backend/app/seed/demo_messages.json` — Shared
Include a small fixed set of demo inputs:
- Clear order.
- Mixed-language order.
- Malayalam-script order.
- Ambiguous pack size.
- Unknown product.
- Out-of-stock product.
- Duplicate message replay.
- Correction/cancellation request.

Use fictional customer identifiers and synthetic data.

---

## 4. Frontend File Responsibilities

Keep the frontend intentionally simple. It is an operator dashboard, not a full e-commerce storefront.

### `frontend/index.html` — Developer B
Create the dashboard structure:
- Header with BhashaOps name and demo-mode status.
- Message submission form.
- Inbox list.
- Order review panel.
- Product/stock summary.
- Low-stock alerts.
- Bill/packing summary.

Do not place API logic inline in large script blocks.

### `frontend/styles.css` — Developer B
- Responsive layout suitable for laptop presentation.
- Clear distinction between draft, needs review, confirmed, cancelled and failed.
- Highlight ambiguous items and low stock.
- Use readable text and obvious confirm/cancel actions.
- Avoid excessive animation; prioritize demo reliability.

### `frontend/api.js` — Developer B
- Centralize `fetch()` calls.
- Set the API base URL in one place.
- Parse errors consistently.
- Provide functions such as `submitMessage`, `getInbox`, `getProducts`, `getOrders`, `resolveOrder`, `confirmOrder`, and `getInventory`.
- Never store secrets in frontend JavaScript.

### `frontend/app.js` — Developer B
- Submit demo messages.
- Refresh and render inbox/order/inventory state.
- Display the model's extracted items alongside catalogue matches.
- Allow the operator to resolve an ambiguous product.
- Require a deliberate confirmation click before finalizing an order.
- Display the returned bill and stock update.
- Show loading and error states.
- Escape or safely render user/model text; do not inject untrusted text through `innerHTML` without sanitization.

**Integration requirement:** The frontend calls documented backend endpoints only. It must not calculate the final price or mutate stock locally.

---

## 5. Scripts and Documentation

### `scripts/setup.sh` — Developer A
- Create or use a virtual environment.
- Install backend dependencies.
- Print clear next steps.
- Do not overwrite user configuration or delete databases.

### `scripts/run_demo.sh` — Shared
- Start the backend using the documented command.
- Optionally open/print the local dashboard URL.
- Do not assume the local Gemma runtime is already running without checking or explaining it.

### `scripts/seed_demo.py` — Developer B
- Add demo products to a fresh database.
- Be idempotent: rerunning the seed should not duplicate products.
- Use stable SKUs.

### `scripts/reset_demo.py` — Developer B
- Reset only an explicitly identified demo database.
- Require an obvious confirmation flag or print a warning.
- Never point at a real production database.

### `docs/api-contract.md` — Both
Before parallel implementation, write down:
- Request fields and types.
- Response fields and types.
- Error response shape.
- Order statuses.
- Product match statuses.
- The exact confirm-order transaction boundary.
- Example curl requests and responses.

### `docs/test-cases.md` — Shared
Record test inputs and expected behavior. Include:
- Correct extraction.
- Ambiguous pack size.
- Unknown item.
- Duplicate inbound message.
- Duplicate confirmation.
- Out-of-stock item.
- Failed transaction rollback.
- Supplier receipt pending versus confirmed.

### `docs/demo-script.md` — Shared
Prepare a 60–90 second demo:
1. Submit a mixed-language order.
2. Show extracted product mentions and catalogue matches.
3. Resolve one deliberately ambiguous item, if useful.
4. Show code-calculated bill.
5. Confirm the order.
6. Show stock deducted once and ledger entry.
7. Show a low-stock warning.
8. Explain that Chat2Ops is a stretch goal if it was not implemented.

---

## 6. Shared Data Contracts — Agree Before Coding

The developers should spend the first 10–15 minutes agreeing on these items and then avoid renaming them independently.

### Order statuses

Use one enum consistently:

- `RECEIVED`
- `PARSING`
- `NEEDS_REVIEW`
- `READY_FOR_CONFIRMATION`
- `CONFIRMED`
- `FULFILLED`
- `CANCELLED`
- `FAILED`

Do not invent different spellings in the API and database.

### Product match statuses

- `EXACT`
- `CANDIDATES`
- `UNKNOWN`
- `INCOMPATIBLE_UNIT`

### Message deduplication

- Unique key: `(source, external_message_id)`.
- Duplicate ingestion returns the original message ID and current status.
- Duplicate ingestion must not create another order.

### Stock ledger idempotency

Suggested key:

```text
order:<order_id>:item:<order_item_id>:sale
```

A database uniqueness constraint is mandatory. An in-memory Python set is not sufficient.

### Money

Use integer minor units:
- ₹10.00 = `1000` paise.
- Store price snapshots on order items.
- Do not use binary floating point for money.

### API error shape

Use a consistent response, for example:

```json
{
  "error": {
    "code": "PRODUCT_MATCH_AMBIGUOUS",
    "message": "Please select the correct product.",
    "details": {
      "order_item_id": "item-demo-01"
    }
  }
}
```

Never return stack traces, secrets, or raw runtime environment values to the browser.

---

## 7. Developer Ownership

### Developer A — Messaging, Gemma, and Order Workflow

**Primary files**
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/api/health.py`
- `backend/app/api/messages.py`
- `backend/app/api/orders.py`
- `backend/app/schemas/messages.py`
- `backend/app/schemas/interpretation.py`
- `backend/app/schemas/orders.py`
- `backend/app/services/message_service.py`
- `backend/app/services/gemma_service.py`
- `backend/app/services/interpretation_service.py`
- `backend/app/services/pricing_service.py`
- `backend/app/services/order_service.py`
- `backend/app/services/bill_service.py`
- `backend/app/adapters/*`
- `backend/app/prompts/order_extraction.txt`
- `backend/tests/test_gemma_service.py`
- `backend/tests/test_interpretation.py`
- `backend/tests/test_pricing.py`
- `backend/tests/test_order_flow.py`

**Deliverables**
1. A model call returns valid, schema-constrained extraction—or a clean manual-review state.
2. The message can be submitted through the simulator.
3. The backend creates a draft order and shows review state.
4. Product matches can be resolved.
5. Totals are calculated by code.
6. The order can be confirmed through one documented inventory transaction.
7. A bill/packing summary can be displayed or printed.

**Do not**
- Change database model names or fields without telling Developer B.
- Implement an independent stock deduction.
- Assume model output includes valid product IDs or correct prices.
- Spend the first hour trying to perfect live WhatsApp.

### Developer B — Catalogue, Database, Inventory, and Dashboard

**Primary files**
- `backend/app/db/*`
- `backend/app/api/products.py`
- `backend/app/api/inventory.py`
- `backend/app/schemas/products.py`
- `backend/app/schemas/inventory.py`
- `backend/app/services/catalogue_service.py`
- `backend/app/services/inventory_service.py`
- `backend/app/services/alert_service.py`
- `backend/app/seed/*`
- `frontend/*`
- `scripts/seed_demo.py`
- `scripts/reset_demo.py`
- `backend/tests/test_catalogue.py`
- `backend/tests/test_inventory_idempotency.py`
- `backend/tests/test_message_deduplication.py`

**Deliverables**
1. SQLite initializes with agreed schema and seeded products.
2. Catalogue lookup handles aliases and ambiguous variants.
3. Inventory reads and stock ledger are available.
4. Confirmation operation can atomically deduct stock once.
5. Low-stock state is visible.
6. Dashboard can submit messages and display inbox, review, bill, and inventory data.
7. The demo can be reset safely.

**Do not**
- Assume Developer A's model extraction is always correct.
- Update stock from an unconfirmed draft.
- change API response fields without coordinating.
- Build a complicated frontend before the API contract is stable.

### Shared integration ownership

Both developers own:
- `docs/api-contract.md`
- End-to-end tests.
- README accuracy.
- Demo script and final presentation.
- Review of each other's high-risk logic.

---

## 8. Four-Hour Execution Plan

### Minute 0–15: Contract and risk check
- Agree on schema, order statuses, API routes, and who owns which files.
- Verify that Gemma 4 is available through the chosen runtime and get one real response.
- If the model is not available, build against a mocked extractor while keeping a clear label that it is a fallback.

### Minute 15–45: Parallel foundations
- A: Implement message input, model call, prompt, and validated extraction.
- B: Implement database schema, seed catalogue, alias matching, and stock read.
- Both: Keep `main` runnable and communicate any contract change immediately.

### Minute 45–90: Order and inventory integration
- A: Build draft order, item resolution, pricing, and confirmation endpoint integration.
- B: Build atomic stock ledger operation and idempotency tests.
- Together: Prove duplicate confirmation does not deduct stock twice.

### Minute 90–130: Dashboard and bill
- A: Finish bill/packing summary and error handling.
- B: Connect the dashboard to inbox, order review, products, and inventory APIs.
- Together: Complete one end-to-end simulator test.

### Minute 130–165: Reliability
- Test Malayalam/Manglish examples, unknown items, ambiguity, out-of-stock, and duplicate messages.
- Fix integration bugs.
- Add WhatsApp only if all core checks already pass.

### Minute 165–200: Demo polish
- Improve status labels and low-stock visibility.
- Add a reset/seed workflow and concise setup instructions.
- Chat2Ops only if the core flow is stable.

### Minute 200–225: Freeze and rehearse
- Stop adding features.
- Run tests from a clean database.
- Rehearse the exact demo twice.
- Confirm the project works without a live WhatsApp account.

### Minute 225–240: Final check
- Check `git status`, secrets, README, startup commands, and demo data.
- Ensure `main` runs and both developers know the demo narrative.

---

## 9. Git Workflow for Two Developers

Use a shared repository with small, reviewable commits.

```bash
# One-time: clone the repository
git clone <YOUR_REPOSITORY_URL>
cd bhashaops

# Developer A
git switch -c feat/gemma-order-flow

# Developer B (in their own clone)
git switch -c feat/catalogue-inventory-dashboard
```

Push branches:

```bash
git add <specific-files>
git commit -m "feat: add Gemma order extraction"
git push -u origin feat/gemma-order-flow
```

Developer B should use their own feature branch and push it similarly. Open pull requests or merge only after reviewing the diff and running tests.

### Conflict prevention
- Do not have both developers edit `db/models.py`, the API contract, or shared schemas simultaneously.
- Developer B proposes database fields; Developer A confirms required fields before implementation.
- Merge the schema/contract first, then parallelize.
- Avoid broad `git add .` until `git status` has been inspected.
- Never force-push over a teammate's work.
- Keep `main` runnable after each integration.

### Before every commit

```bash
git status
git diff --check
git diff --stat
```

Then add only intended files and commit.

---

## 10. Minimum End-to-End Definition of Done

The MVP is not done merely because the model returns JSON. It is done when all of the following work:

- [ ] Start backend with documented command.
- [ ] Submit a sample order through the simulator.
- [ ] Persist the inbound message.
- [ ] Deduplicate a repeated message.
- [ ] Call Gemma or clearly use the documented fallback.
- [ ] Validate the extraction schema.
- [ ] Match products or mark ambiguity.
- [ ] Show the operator the draft order.
- [ ] Calculate prices and totals in backend code.
- [ ] Reject or review insufficient stock.
- [ ] Confirm the order.
- [ ] Write one stock-ledger sale movement per order item.
- [ ] Confirm the same order again and prove no extra deduction occurs.
- [ ] Show updated stock and low-stock alert.
- [ ] Display or print a bill.
- [ ] Run the demo from a clean seeded database.
- [ ] Ensure `.env`, database files, WhatsApp sessions, and customer data are not committed.

If time is short, do not implement Chat2Ops, live WhatsApp sending, supplier automation, or UPI integration until this checklist passes.

---

## 11. Final Team Agreement

1. **One shared schema.** Both developers implement the same field names and status enums.
2. **One stock confirmation path.** All confirmed orders call the same transaction-safe inventory operation.
3. **No model-controlled side effects.** Gemma output cannot directly update prices, confirm orders, or mutate stock.
4. **Review ambiguity.** Unknown products and pack-size uncertainty are surfaced, not guessed.
5. **Simulator first.** The core demo must work without WhatsApp credentials.
6. **Keep `main` runnable.** Integrate early, commit small, and rehearse before the deadline.
7. **Truthful demo claims.** State which parts use Gemma, which parts are deterministic, and which integrations are simulated.

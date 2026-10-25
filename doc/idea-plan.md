# BhashaOps --- Idea & Project Plan

> **Tagline:** From Conversations to Verified Actions\
> **Track:** Best Use of Gemma 4\
> **Project type:** Local-first, multilingual conversational operations
> assistant\
> **Primary users:** Neighbourhood kirana stores and small teams\
> **Core languages:** Malayalam, Manglish (Malayalam written in Latin
> script), and English

------------------------------------------------------------------------

## 1. Executive Summary

BhashaOps turns informal chat messages into structured, reviewable
actions. Small businesses and community teams already coordinate through
messaging apps, but important details are buried in conversations:
customer orders need to become bills, supplier messages need to update
stock, and group discussions need to become assigned tasks.

BhashaOps uses **Gemma 4** to interpret natural, multilingual messages.
Conventional application code then validates the interpretation and
performs deterministic operations such as catalogue matching, price
calculation, inventory transactions, deadline storage, and
change-history updates.

The product has three connected modules:

1.  **OrderOps** --- automatically interpret incoming WhatsApp orders
    and prepare bills and packing slips.
2.  **StockSathi** --- track stock changes from confirmed sales and
    supplier deliveries, and flag low inventory.
3.  **Chat2Ops** --- turn authorized team conversations into tasks,
    deadlines, dependencies, budgets, and auditable updates.

For the hackathon, the priority is one polished end-to-end shop
workflow, with inventory connected to it. Chat2Ops is a smaller
demonstration of how the same message-to-action engine can support a
second use case.

## 2. Problem Statement

Informal messages are easy for people to send but difficult for
businesses and teams to operationalize reliably.

### Neighbourhood shops

-   Customers send orders in Malayalam, Manglish, English,
    abbreviations, and mixed-language text.
-   Staff manually read messages, identify products, calculate prices,
    check stock, and reply.
-   Similar product names, pack sizes, and unclear quantities cause
    mistakes.
-   Stock records become inaccurate when orders are missed or deducted
    more than once.
-   Shopkeepers need a simple workflow that does not require customers
    to learn a new application.

### Small teams and student organizations

-   Decisions, assignments, budgets, and deadlines are scattered across
    group chats.
-   Ownership and dependencies are easily forgotten.
-   Later messages may change earlier decisions without an explicit
    record of the change.

### The opportunity

Create a reliable bridge between **human conversation and structured
operations**, with language understanding handled by Gemma and critical
business rules handled by normal code.

## 3. Product Vision

**BhashaOps is a local-first AI operations layer that converts
multilingual conversations into verified business actions.**

It should: - Accept natural Malayalam, Manglish, and English messages. -
Extract structured intent without forcing users to follow a rigid
command format. - Ground product and business decisions in the user's
own catalogue and records. - Ask for clarification when a message is
ambiguous. - Keep a traceable record of what was interpreted, confirmed,
and changed. - Minimize data leaving the local machine, while clearly
documenting any external services involved.

### Design principles

1.  **AI interprets; code validates and executes.**
2.  **No silent assumptions** about prices, product variants,
    quantities, dates, or stock.
3.  **Human approval for consequential actions**, especially order
    confirmation, stock corrections, and outbound messages.
4.  **Idempotent processing:** the same incoming message must not create
    duplicate orders or stock deductions.
5.  **Evidence and auditability:** preserve the original message and
    show how extracted fields were interpreted.
6.  **Graceful fallback:** if the model or WhatsApp connection fails,
    the shopkeeper can still review and enter an order manually.

## 4. Target Users and Primary Use Case

### Primary persona: neighbourhood kirana shopkeeper

A shopkeeper receives orders from familiar customers through WhatsApp
and wants to process them quickly without repeatedly typing product
details into a billing system.

### Example incoming order

> "chetta 2 kilo atta, 1 amul butter cheruth, 6 ande, 10nte oru maggi"

BhashaOps should propose a structured order such as:

  ------------------------------------------------------------------------
  Product candidate                         Quantity Notes
  --------------------- ---------------------------- ---------------------
  Atta / wheat flour                            2 kg Match against the
                                                     shop catalogue

  Amul butter, small                          1 pack Confirm the exact
  pack                                               pack if multiple
                                                     variants exist

  Eggs                                      6 pieces Normalize local
                                                     wording

  Maggi ₹10 pack                              1 pack Treat the
                                                     price/variant
                                                     interpretation as a
                                                     candidate
  ------------------------------------------------------------------------

The system must not assume a product match is certain just because the
model returns it. Catalogue matching and confidence thresholds determine
whether a field can be accepted automatically or needs shopkeeper
review.

### Expected result

After review and confirmation, the system: - Calculates the total using
the shop's current catalogue prices. - Checks availability. - Saves the
order. - Deducts stock exactly once according to the chosen fulfilment
policy. - Generates a printable packing slip or bill. - Prepares a
customer reply. - Generates a UPI QR from the verified amount and
configured merchant details, if supported. - Records the order and stock
movements for later inspection.

## 5. Core Modules

### Module A --- OrderOps: WhatsApp order automation

**Goal:** Turn incoming customer messages into validated orders without
copy-pasting.

**Features** - Receive incoming messages through a WhatsApp connector. -
Preserve chat ID, message ID, sender, timestamp, and original text. -
Detect whether a message is a new order, correction, cancellation,
question, or unrelated chat. - Use Gemma 4 to extract product mentions,
quantities, units, variants, and ambiguity. - Match extracted product
candidates to the shop's product catalogue and aliases. - Calculate
prices with deterministic code using decimal arithmetic. - Flag
unavailable products, uncertain pack sizes, and ambiguous quantities. -
Provide a review/confirmation screen. - Generate a bill, packing slip,
and proposed customer reply. - Generate a UPI QR only after the final
total and merchant configuration are validated.

**Order lifecycle**
`received → parsed → needs_review / ready_to_confirm → confirmed → fulfilled / cancelled`

Do not mark an order as confirmed solely because Gemma extracted it. A
shopkeeper approval or an explicitly configured safe rule is required.

### Module B --- StockSathi: inventory linked to orders

**Goal:** Keep inventory consistent with confirmed sales and verified
deliveries.

**Features** - Product catalogue with SKU, display name, aliases, unit,
pack size, price, and stock quantity. - Stock ledger with reason,
quantity delta, source event, timestamp, and actor. - Deduct inventory
once for a confirmed order at the selected business event (for example,
order confirmation or fulfilment); document which policy is used. -
Record supplier delivery increases only after the delivery is
confirmed. - Low-stock thresholds and restock suggestions. - Product
alias support for local names, transliterations, brands, and common
misspellings. - Manual stock correction with a reason and audit trail.

**Example** - Opening stock: 12 packs of Maggi. - Confirmed sale: 3
packs. - Expected stock: 9 packs. - Duplicate webhook for the same
order: no second deduction. - Supplier message: "naale 2 box maggi
konduvaram." - The system proposes a delivery, but does not increase
stock until receipt is confirmed and the number of packs per box is
known.

### Module C --- Chat2Ops: group conversations into action plans

**Goal:** Convert authorized team conversations into a persistent
project state.

**Features** - Process messages only from explicitly configured and
authorized groups. - Extract tasks, owners, deadlines, budget
constraints, dependencies, decisions, and unresolved questions. - Link
each extracted item to the source message. - Ask for clarification when
the owner or date is uncertain. - Update existing tasks rather than
duplicating them. - Preserve change history: previous value, new value,
source message, timestamp, and actor. - Provide a concise summary of
open tasks and blockers.

**Example message**

> "stage set cheyyan Arjun nokkam, lights sponsor confirm aayittilla,
> Friday munne poster venam, budget 15k cross aavaruth"

Possible extraction: - Task: Set up the stage. Candidate owner: Arjun. -
Task: Confirm lighting sponsor. Status: unresolved. - Task: Prepare
poster. Deadline: before Friday; exact date depends on the message
timestamp and local timezone. - Budget ceiling: ₹15,000. - Blocker:
lighting sponsorship remains unconfirmed.

The system must not silently assign an uncertain owner or overwrite a
deadline without a traceable source.

## 6. Gemma 4's Role

Gemma 4 is the natural-language interpretation layer, not the source of
truth for business data.

### Use Gemma for

-   Understanding Malayalam, Manglish, English, and mixed-language
    messages.
-   Recognizing order intent, corrections, cancellations, and supplier
    updates.
-   Extracting products, quantities, units, variants, task owners,
    dates, constraints, and dependencies.
-   Interpreting informal wording and proposing normalized catalogue
    matches.
-   Identifying ambiguity and generating clarification questions.
-   Summarizing conversation changes in readable language.

### Use deterministic application code for

-   Catalogue lookup and final product selection.
-   Price calculations, tax/discount rules if applicable, and totals.
-   Stock availability and stock ledger transactions.
-   Duplicate detection and idempotency.
-   Date validation and deadline persistence.
-   Permissions, approvals, and outbound-message policy.
-   UPI URI/QR construction from verified merchant details and totals.
-   Audit logging and data persistence.

### Suggested structured extraction contract

The model should return schema-constrained JSON where supported, with
fields such as: - `intent` - `language` - `items[]` -
`product_mention` - `quantity` - `unit` - `variant` -
`candidate_price_tier` - `ambiguity` - `source_text` - `corrections[]` -
`confidence_or_review_reason` - `clarification_question`

Treat model output as untrusted input. Validate it against a schema,
reject malformed responses, and never execute arbitrary model-generated
code or commands.

### Local inference and privacy

The intended prototype uses Gemma 4 through Ollama where a compatible
model build and adequate hardware are available. Verify the exact model
identifier, license/usage conditions, memory requirements, and inference
performance before the event. Do not claim the whole system is local if
WhatsApp, a cloud API, or another external service processes data.

## 7. Architecture

### Proposed hackathon stack

  -----------------------------------------------------------------------
  Layer                   Choice                  Responsibility
  ----------------------- ----------------------- -----------------------
  Messaging adapter       `whatsapp-web.js` for a Receive incoming
                          controlled prototype    WhatsApp Web messages

  AI inference            Gemma 4 through Ollama  Interpret multilingual
                                                  messages

  Backend                 Python + FastAPI        Business logic and APIs

  Database                SQLite                  Catalogue, orders,
                                                  stock ledger, tasks,
                                                  audit events

  Frontend                HTML/CSS/JavaScript     Review queue, orders,
                                                  inventory, task view

  Documents               HTML print stylesheet;  Bill and packing slip
                          optional PDF            

  QR generation           UPI URI plus QR library Payment QR after total
                                                  verification
  -----------------------------------------------------------------------

### High-level flow

1.  A WhatsApp message arrives.
2.  The adapter deduplicates it using the message ID and records the
    original.
3.  The backend sends relevant text to Gemma.
4.  The response is schema-validated and normalized.
5.  The catalogue and business rules resolve products, prices, and
    stock.
6.  Ambiguous or risky fields enter the review queue.
7.  An authorized user confirms the order or task update.
8.  The database commits the operation and associated audit event.
9.  The UI shows the result; any outbound WhatsApp reply follows the
    configured approval policy.

### Important WhatsApp note

`whatsapp-web.js` is an unofficial WhatsApp Web automation library. It
may be appropriate for a controlled hackathon prototype, but it carries
compatibility and account risks and should not be assumed suitable for
production. Use a dedicated test account and authorized test
conversations. For production, assess the official WhatsApp Business
Platform and its current rules.

## 8. Data Model

Keep the MVP schema small and auditable.

### `Product`

-   `id`
-   `sku`
-   `name`
-   `aliases[]`
-   `base_unit`
-   `pack_size`
-   `price`
-   `stock_quantity`
-   `low_stock_threshold`
-   `active`

### `IncomingMessage`

-   `id`
-   `provider_message_id` (unique)
-   `chat_id`
-   `sender_id`
-   `timestamp`
-   `original_text`
-   `processing_status`

### `Order`

-   `id`
-   `source_message_id`
-   `customer_reference`
-   `status`
-   `subtotal`
-   `total`
-   `created_at`
-   `confirmed_at`

### `OrderItem`

-   `id`
-   `order_id`
-   `product_id`
-   `quantity`
-   `unit`
-   `unit_price_snapshot`
-   `line_total`
-   `match_status`

### `StockMovement`

-   `id`
-   `product_id`
-   `quantity_delta`
-   `reason`
-   `source_event_id` (unique where appropriate)
-   `created_at`
-   `actor`

### `Task` and `TaskChange`

-   Task: `id`, `title`, `owner`, `deadline`, `status`, `budget_limit`,
    `source_message_id`
-   Change: `task_id`, `field`, `old_value`, `new_value`,
    `source_message_id`, `timestamp`, `actor`

## 9. Hackathon Scope and Priorities

The goal is a complete, reliable vertical slice---not three unfinished
products.

### P0 --- Must work

-   Incoming message handling or a dependable local simulator fallback.
-   Gemma-powered Malayalam/Manglish/English extraction.
-   Catalogue matching and deterministic pricing.
-   Human review for ambiguity.
-   Order persistence and duplicate-message protection.
-   Stock ledger updated exactly once.
-   A clear UI demonstrating the flow.

### P1 --- Should work

-   Printable bill or packing slip.
-   Customer reply draft and approval before sending.
-   UPI QR generated from verified merchant details and exact total.
-   Low-stock warning.
-   Several prepared test cases and an evaluation summary.

### P2 --- Stretch goal

-   Supplier message → proposed stock receipt.
-   Chat2Ops task extraction and change history.
-   Voice-note transcription, only if the text workflow is already
    stable.
-   Multiple shops, authentication, cloud synchronization, or complex
    analytics.

### Explicitly out of scope for the first prototype

-   A complete POS replacement.
-   Automatic purchasing without approval.
-   Full accounting, tax compliance, or payment processing.
-   Unrestricted monitoring of personal group chats.
-   Production-grade multi-tenant security and deployment.
-   Guaranteed support for every Malayalam dialect or spelling variant.

## 10. Two-Person Team Plan

### Person A --- AI and backend

-   Configure Gemma 4 and verify inference performance.
-   Design the extraction schema and prompts.
-   Implement validation, catalogue matching, pricing, stock
    transactions, and deduplication.
-   Test mixed-language messages and ambiguity handling.

### Person B --- Integration and product UI

-   Set up the WhatsApp connector and a reliable fallback input.
-   Build the order review, bill, stock, and task views.
-   Create the seeded catalogue and test conversations.
-   Prepare the README, architecture diagram, and demo script.

Both teammates should test the full flow together early; do not leave
integration until the end.

## 11. Build Schedule

### Preparation day

1.  Verify event rules, model availability, inference speed, and
    hardware requirements.
2.  Create the repository and a minimal runnable application.
3.  Prepare a small catalogue with product names, Malayalam/Manglish
    aliases, pack sizes, prices, and stock.
4.  Collect representative test messages and manually label the expected
    products and quantities.
5.  Test the WhatsApp connector on a dedicated account, with a
    manual/local simulator fallback.
6.  Freeze scope and rehearse the intended demo once.

### 120-minute implementation window

  Time           Goal
  -------------- ---------------------------------------------------------
  0--15 min      Freeze schema, start the app, confirm model call
  15--35 min     Connect message input to structured Gemma output
  35--60 min     Add catalogue matching, pricing, and ambiguity review
  60--80 min     Persist orders and add idempotent stock transactions
  80--95 min     Generate packing slip, reply draft, and optional UPI QR
  95--108 min    Run tests and fix the highest-impact failure
  108--120 min   Rehearse demo, prepare fallback, finalize submission

If live WhatsApp integration is not working by the early checkpoint,
switch to a local message simulator and finish the core workflow. A
dependable end-to-end prototype is more valuable than an unreliable live
integration.

## 12. Evaluation Plan

Prepare a small test set before the hackathon. Do not claim accuracy
without measuring it.

### Test categories

-   Malayalam script.
-   Manglish with spelling variation.
-   English and mixed-language messages.
-   Product aliases and brand names.
-   Pack-size ambiguity.
-   Quantity and unit variations.
-   Corrections and cancellations.
-   Unknown products and out-of-stock items.
-   Duplicate messages.
-   Supplier delivery statements that are proposed but not yet
    confirmed.
-   Group-chat deadline changes and conflicting instructions.

### Metrics

-   **Item extraction accuracy:** correct product and quantity pairs.
-   **Catalogue match accuracy:** correct final SKU among accepted
    matches.
-   **Ambiguity handling:** uncertain cases correctly sent for review.
-   **Price correctness:** total matches deterministic calculation for
    the confirmed order.
-   **Stock integrity:** no duplicate deductions across repeated message
    events.
-   **Latency:** measure time from message receipt to proposed order on
    the demo hardware.
-   **Task fidelity:** correct owner, deadline, budget, and
    change-history extraction on labelled examples.

Report the test-set size and results honestly. Keep price correctness
and stock integrity separate from language-model accuracy.

## 13. Demo Script

The demo should show one complete workflow in under two minutes.

1.  Send a Manglish order to the test shop's WhatsApp account.
2.  Show that it arrives without copy-pasting.
3.  Show Gemma's structured interpretation and highlight one ambiguous
    item.
4.  Confirm the item and display the bill with catalogue-derived prices.
5.  Generate a packing slip and UPI QR using configured merchant
    details.
6.  Show stock reducing exactly once, even if the same webhook is
    replayed.
7.  Show a low-stock alert.
8.  If time permits, switch to Chat2Ops and demonstrate a task deadline
    changing with a recorded history.

### Suggested opening pitch

"Small shops and teams already run on conversations, but conversations
don't automatically become reliable operations. BhashaOps uses Gemma 4
to understand Malayalam, Manglish, and English, then uses ordinary code
to validate the result, update records, and create actions people can
trust."

## 14. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Gemma misreads local wording        Curated aliases, representative
                                      tests, and human review

  Wrong product or pack size          Catalogue-grounded matching; ask
                                      when uncertain

  Incorrect bill total                Deterministic decimal arithmetic,
                                      never model-generated totals

  Duplicate webhook                   Unique message IDs and idempotent
                                      transactions

  Stock race or overselling           Transactional stock checks and
                                      atomic updates

  Incorrect UPI QR                    Validate merchant details and
                                      amount; test the encoded URI

  WhatsApp session fails              Local simulator and prepared sample
                                      messages

  Slow local inference                Benchmark early, use a compatible
                                      smaller model configuration if
                                      permitted, reduce scope

  Privacy overclaim                   Document WhatsApp/external service
                                      boundaries and keep model inference
                                      local where configured

  Chat2Ops scope creep                Make it a stretch goal after the
                                      shop workflow is complete
  -----------------------------------------------------------------------

## 15. Open-Source Deliverables

The public repository should include: - A clear README with the problem,
demo flow, setup steps, and screenshots. - Architecture diagram. -
Example catalogue and synthetic test conversations. - `.env.example`
without secrets. - Setup and troubleshooting instructions. - A
model/configuration note describing exactly which Gemma 4 build was
tested. - Evaluation script and labelled sample cases. - License
appropriate to the project and all dependencies. - Known limitations,
privacy notes, and contribution instructions.

Do not commit WhatsApp session files, API keys, customer messages,
personal information, or merchant secrets.

## 16. Success Criteria

BhashaOps is ready for a hackathon demo when: - A new incoming message
can be processed without copy-pasting. - A representative
Malayalam/Manglish order becomes a structured proposal. - The catalogue
determines the final product and price. - Uncertain matches are visible
and can be corrected. - A confirmed order creates a bill and updates
stock once. - Replaying the same message does not duplicate the order or
stock movement. - The demo can run from a clean setup or has a reliable
fallback. - The team can explain exactly what Gemma does, what ordinary
code does, and where the system still needs human review.

## 17. Final Recommendation

Build **BhashaOps as one conversation-to-action platform**, but
demonstrate its value through the kirana workflow first. OrderOps and
StockSathi should share the same product catalogue, event history, and
validation layer. Chat2Ops should reuse the message extraction and audit
patterns as a secondary module.

The strongest claim is not that the system is fully autonomous. It is
that it makes multilingual conversations operationally useful while
keeping prices, inventory, permissions, and consequential actions under
deterministic control.

> **BhashaOps --- From Conversations to Verified Actions.**

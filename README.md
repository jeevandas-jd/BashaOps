# BhashaOps

> **From Conversations to Verified Actions**\
> A local-first, multilingual operations assistant powered by Gemma 4.

BhashaOps turns everyday conversations into structured, reviewable
actions. It is designed for neighbourhood businesses and small teams
that coordinate work through informal messages in **Malayalam, Manglish,
English, and mixed-language text**.

The initial use case is WhatsApp orders for kirana stores: interpret a
message, match products against the shop's own catalogue, calculate a
verified bill, and update inventory safely. The same message-to-action
approach can also support supplier stock updates and team task tracking.

> **Hackathon prototype:** Features and integrations described below are
> planned or under development unless explicitly marked as implemented.
> Update this README to match the actual state of the repository before
> submission.

## The Problem

Small shops receive orders in informal messages such as:

> `chetta 2 kilo atta, 1 amul butter cheruth, 6 ande, 10nte oru maggi`

Manually processing these messages takes time and can lead to mistakes
in product selection, pack sizes, totals, and stock records. Meanwhile,
supplier updates and team decisions are buried in chats and may never
become reliable records.

BhashaOps aims to bridge that gap: **Gemma interprets the conversation;
ordinary code validates the result and performs business operations.**

## Product Modules

### 1. OrderOps --- WhatsApp order automation

-   Receive incoming WhatsApp messages without manual copy-pasting.
-   Interpret Malayalam, Manglish, English, and mixed-language orders
    using Gemma 4.
-   Extract product mentions, quantities, units, and possible variants
    into structured data.
-   Match candidate items against the shop's catalogue and aliases.
-   Ask the shopkeeper to review ambiguous products or pack sizes.
-   Calculate totals using catalogue prices and deterministic code.
-   Generate an order summary, printable bill/packing slip, and customer
    reply draft.
-   Optionally generate a UPI QR from validated merchant details and the
    confirmed amount.

### 2. StockSathi --- Inventory connected to orders

-   Maintain a product catalogue with SKU, aliases, unit, pack size,
    price, and stock.
-   Update stock when an order reaches the configured confirmation or
    fulfilment state.
-   Prevent duplicate deductions when the same message or event is
    processed more than once.
-   Track stock movements with their source and timestamp.
-   Flag low stock and propose replenishment.
-   Treat supplier messages as proposed deliveries; increase stock only
    after receipt is confirmed.

### 3. Chat2Ops --- Group conversations into action plans

A stretch module that turns authorized team messages into structured
tasks, owners, deadlines, budgets, dependencies, and decisions.

-   Link extracted tasks to their source messages.
-   Update existing tasks rather than creating duplicates.
-   Keep a history when deadlines, owners, or budgets change.
-   Ask for clarification when a message is ambiguous.

## How It Works

``` text
Incoming WhatsApp message
          |
          v
Message receiver and duplicate check
          |
          v
Gemma 4: interpret Malayalam / Manglish / English
          |
          v
Schema validation and catalogue matching
          |
          v
Review queue for ambiguous fields
          |
          v
Shopkeeper confirms the order
          |
          +-------------------+
          |                   |
          v                   v
  Bill / packing slip    Stock ledger update
          |
          v
  Customer reply draft
```

The model does not determine final prices or directly mutate inventory.
Those operations are handled by validated application code.

## Technology Stack

The proposed hackathon stack is:

  -----------------------------------------------------------------------
  Component               Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Language model          Gemma 4                 Multilingual message
                                                  interpretation

  Local inference         Ollama, subject to      Run inference locally
                          compatible model        
                          availability            

  WhatsApp integration    `whatsapp-web.js` for a Receive and handle
                          controlled prototype    messages

  Backend                 Python + FastAPI        APIs and business logic

  Database                SQLite                  Catalogue, orders,
                                                  stock ledger, and tasks

  Frontend                HTML, CSS, JavaScript   Review and operations
                                                  dashboard

  Bill output             HTML print stylesheet   Printable bill/packing
                          or PDF                  slip

  Payment QR              UPI URI + QR library    Encode validated
                                                  payment details
  -----------------------------------------------------------------------

The final stack may change during implementation. Document the exact
Gemma 4 model identifier and versions actually tested.

## Local Development

### Prerequisites

Install or prepare:

-   Python 3.11+ (use the version selected by the project).
-   Git.
-   Ollama, if using local model inference.
-   A compatible Gemma 4 model available in your Ollama environment.
-   Node.js and npm if the chosen WhatsApp connector setup requires
    them.
-   A dedicated test WhatsApp account for a controlled demo.

### 1. Clone the repository

``` bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_DIRECTORY>
```

Replace the placeholders with the actual repository URL and directory.

### 2. Create and activate a Python environment

``` bash
python -m venv .venv
```

Linux/macOS:

``` bash
source .venv/bin/activate
```

Windows PowerShell:

``` powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

If the repository contains a `requirements.txt`:

``` bash
pip install -r requirements.txt
```

If dependency files are not yet present, create them from the project's
actual imports and tested versions before asking contributors to install
the application.

### 4. Configure environment variables

Create a local `.env` based on `.env.example` if provided. For example:

``` env
OLLAMA_BASE_URL=http://localhost:11434
GEMMA_MODEL=<YOUR_VERIFIED_GEMMA_4_MODEL_ID>
DATABASE_URL=sqlite:///./bhashaops.db
```

These are illustrative settings. The application must be configured to
read the variables it actually uses. Never commit `.env`, API keys,
WhatsApp session files, or real customer data.

### 5. Verify local model access

Start Ollama and confirm the selected Gemma 4 model is available using
the model identifier documented for your environment. Model names and
availability may differ, so do not assume a model tag without verifying
it.

### 6. Run the backend

If the application entry point is `app.main:app`, for example:

``` bash
uvicorn app.main:app --reload
```

Use the actual module path from the repository. The entry point may
change during development.

### 7. Start the WhatsApp connector

Follow the instructions in the WhatsApp integration directory. Pair only
a dedicated test account, and ensure the local simulator can be used if
the live connection is unavailable.

## Example Order

Input:

``` text
chetta 2 kilo atta, 1 amul butter cheruth, 6 ande, 10nte oru maggi
```

Illustrative extraction:

``` json
{
  "intent": "new_order",
  "language": "ml-manglish",
  "items": [
    {
      "product_mention": "atta",
      "quantity": 2,
      "unit": "kg",
      "needs_review": false
    },
    {
      "product_mention": "Amul butter",
      "quantity": 1,
      "unit": "pack",
      "variant": "small",
      "needs_review": true
    },
    {
      "product_mention": "eggs",
      "quantity": 6,
      "unit": "piece",
      "needs_review": false
    },
    {
      "product_mention": "Maggi",
      "quantity": 1,
      "unit": "pack",
      "candidate_price_tier": 10,
      "needs_review": true
    }
  ]
}
```

This is an example of the intended output, not a guarantee that every
input will be interpreted correctly. Product matches, pack sizes, and
prices must be validated against the shop's catalogue. The final total
is calculated by application code.

## Reliability and Safety Principles

-   **Human review:** uncertain products, pack sizes, corrections,
    cancellations, and consequential actions are reviewed.
-   **Deterministic billing:** totals come from catalogue prices and
    application code, never from model-generated arithmetic.
-   **Idempotency:** duplicate incoming messages or repeated
    confirmations must not duplicate orders or stock deductions.
-   **Auditability:** preserve source message references and record
    stock movements and task changes.
-   **Least privilege:** process only authorized chats and groups.
-   **Privacy:** use synthetic data in development and keep secrets out
    of version control.
-   **Graceful fallback:** provide a manual/local simulator path if
    WhatsApp or the model is unavailable.

## Privacy and WhatsApp Notes

Ollama can keep model inference on the local machine when configured
that way, but that does **not** mean every part of the system is local:
WhatsApp messages still pass through WhatsApp's infrastructure, and
other enabled services may process data externally.

`whatsapp-web.js` is an unofficial WhatsApp Web automation library. It
may be useful for a controlled hackathon prototype, but it carries
compatibility and account risks. Do not assume it is appropriate for
production. For commercial deployment, evaluate the official WhatsApp
Business Platform and its current policies.

Do not use the prototype for automated high-stakes decisions. Keep order
confirmation and outbound replies under user control.

## Testing

Test with synthetic messages that cover:

-   Malayalam script.
-   Manglish and spelling variations.
-   English and mixed-language orders.
-   Product aliases and brand names.
-   Ambiguous pack sizes and quantities.
-   Unknown products and out-of-stock items.
-   Corrections and cancellations.
-   Duplicate messages and repeated confirmations.
-   Supplier delivery proposals that must not update stock before
    confirmation.
-   Team messages that change deadlines or budgets.

Track actual results for: - Item and quantity extraction accuracy. -
Catalogue match accuracy. - Ambiguity detection. - Correct totals. -
Duplicate-order and duplicate-stock prevention. - Model latency on the
demo machine.

Do not claim a metric until it has been measured on a documented test
set.

## Team and Contribution Workflow

BhashaOps is being developed by a two-person team.

-   **Developer A:** WhatsApp receiver, Gemma extraction, order
    workflow, review UI, bill and reply draft.
-   **Developer B:** catalogue, stock ledger, idempotent inventory
    transactions, low-stock warnings, and Chat2Ops stretch module.
-   **Both:** API contracts, integration, tests, security review, and
    demo.

Suggested branch names:

``` text
main
feat/orderops
feat/stock-chatops
```

Use small commits and pull requests. Keep `main` runnable. Do not have
both developers edit the same shared file simultaneously without
coordinating.

## Roadmap

### P0 --- Core demo

-   [ ] Receive or simulate an incoming message.
-   [ ] Interpret Malayalam/Manglish/English with Gemma 4.
-   [ ] Validate structured output and match catalogue items.
-   [ ] Review ambiguous items.
-   [ ] Calculate a correct bill.
-   [ ] Save a confirmed order and deduct stock exactly once.
-   [ ] Demonstrate the workflow from a clean start.

### P1 --- Useful additions

-   [ ] Printable bill/packing slip.
-   [ ] Approved customer reply.
-   [ ] UPI QR using validated merchant details.
-   [ ] Low-stock alert.
-   [ ] Labelled evaluation set and measured results.

### P2 --- Stretch goals

-   [ ] Supplier message to proposed stock receipt.
-   [ ] Chat2Ops task extraction and change history.
-   [ ] Voice-note support.
-   [ ] Multi-shop support and production deployment.

## Project Status

This repository is a hackathon project. Update this section as features
are implemented, and distinguish tested functionality from planned work.

## License

Choose and add an appropriate open-source license before public release.
Ensure the license is compatible with the code and dependencies included
in the repository.

------------------------------------------------------------------------

**BhashaOps --- From Conversations to Verified Actions.**

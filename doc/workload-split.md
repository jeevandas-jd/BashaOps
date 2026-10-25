# BhashaOps --- Workload Split & GitHub Collaboration Plan

> **Team:** 2 developers with equivalent skills\
> **Time remaining:** 4 hours\
> **Goal:** Ship a working, demonstrable Gemma 4-powered prototype\
> **Primary workflow:** WhatsApp message → Malayalam/Manglish
> interpretation → validated order → bill → stock update\
> **Stretch goal:** Chat2Ops task extraction

------------------------------------------------------------------------

## 1. Four-Hour Strategy

With only four hours left, do not attempt to complete three independent
products. Build one end-to-end workflow first, connect inventory second,
and demonstrate Chat2Ops only if the core path is stable.

### Definition of done

A judge can send or replay a Malayalam/Manglish order and see: 1. The
message received without copy-pasting, or a reliable simulator fallback.
2. Gemma 4 extracting product mentions and quantities into structured
data. 3. Product matching against a seeded shop catalogue. 4. A review
step for uncertain matches. 5. A correct total calculated by normal
code. 6. A saved order and exactly one stock deduction after
confirmation. 7. A bill/packing slip and a ready-to-send customer reply.
8. A repeat message that does not create a duplicate order or stock
deduction.

**Do not sacrifice this working path for extra features.**

## 2. Workload Split

Both developers should own complete, testable modules rather than
separating frontend and backend work.

### Developer A --- Messaging, Gemma interpretation, and order flow

**Primary ownership** - WhatsApp connection using `whatsapp-web.js`,
with a simulator fallback. - Incoming-message handler and message ID
deduplication. - Shared Gemma client integration and structured
extraction prompt for Malayalam, Manglish, English, and mixed-language
orders. - JSON/schema validation for model output. - Product candidate
matching against catalogue aliases. - Order review and confirmation
flow. - Bill/packing slip generation. - Customer reply draft; sending
requires shopkeeper approval. - UPI QR generation only after amount and
merchant details are validated.

**Deliverables** - A message can be submitted and parsed. - Extracted
items and uncertain fields are visible. - A confirmed order is stored
and produces a bill. - The original message and processing status can be
traced.

**Must not own** - Independent stock deduction logic. - A separate
catalogue or duplicate inventory database. - Arbitrary model-generated
price calculations.

### Developer B --- Catalogue, inventory, transactional integrity, and Chat2Ops

**Primary ownership** - Shared SQLite schema and catalogue seed data. -
Product records: SKU, aliases, unit, pack size, price, stock, low-stock
threshold. - Catalogue API/helper used by Developer A. - Stock ledger
and transactional stock updates. - Idempotency so the same confirmed
order cannot deduct stock twice. - Low-stock warnings and supplier
receipt proposals. - Minimal Chat2Ops extraction and task-change
history, only after the main flow works. - Inventory/status UI or API
needed for the demo.

**Deliverables** - Seeded catalogue and stock data. - Deterministic
product lookup and price retrieval. - Stock ledger with source
order/event ID. - Atomic, idempotent stock deduction. - A small task
extraction example if time permits.

**Must not own** - A second Gemma client with a different
configuration. - A second source of truth for products or orders. -
Automatic stock increases from unconfirmed supplier messages.

### Shared responsibilities

-   Agree on schema and API contracts before parallel coding.
-   Use the same repository and shared Gemma client.
-   Integrate every 30--45 minutes, not only at the end.
-   Run end-to-end tests together.
-   Prepare demo data, README, and fallback path.

------------------------------------------------------------------------

## 3. Four-Hour Execution Schedule

Use a strict timer. Times below are elapsed time from the start.

  --------------------------------------------------------------------------------
  Elapsed time      Developer A                Developer B       Shared checkpoint
  ----------------- -------------------------- ----------------- -----------------
  0--15 min         Verify model call;         Create database   Agree on JSON
                    implement message-to-Gemma schema, catalogue schema, module
                    path                       seed, stock       interfaces, and
                                               helpers           demo message

  15--45 min        Extract                    Implement product A can send sample
                    intent/items/quantities;   lookup and        extraction to B's
                    validate response          price/stock APIs  catalogue helper

  45--90 min        Order matching, ambiguity  Stock ledger,     End-to-end order
                    review, order save         atomic deduction, data contract
                                               idempotency tests works

  90--130 min       Bill/packing slip and      Connect confirmed A confirmed order
                    customer reply draft       order to stock;   updates stock
                                               low-stock display exactly once

  130--165 min      Fix multilingual edge      Integration       Full workflow
                    cases; WhatsApp            tests; add        passes from clean
                    integration or fallback    Chat2Ops only if  start
                                               stable            

  165--200 min      Polish order screen and    Polish stock      Freeze new
                    demo sequence              screen, README    features
                                               and setup         

  200--225 min      Test live message and      Test duplicate,   Record actual
                    backup scenario            ambiguous and     results and fix
                                               out-of-stock      critical failures
                                               cases             

  225--240 min      Joint rehearsal and        Joint rehearsal   No new features
                    submission                 and submission    in final 15
                                                                 minutes
  --------------------------------------------------------------------------------

### Hard cut-off rules

-   By minute 15, a working Gemma request must exist.
-   By minute 45, structured extraction and catalogue lookup must work
    independently.
-   By minute 90, the order must be saved and stock logic testable.
-   By minute 165, the core end-to-end path must work.
-   Chat2Ops is optional; skip it if the core path is not reliable.
-   Keep a simulator fallback even if live WhatsApp works.

------------------------------------------------------------------------

## 4. Shared Contract --- Agree Before Coding

Use one JSON structure for the interpretation output. Example:

``` json
{
  "intent": "new_order",
  "language": "ml-manglish",
  "items": [
    {
      "product_mention": "2 kilo atta",
      "quantity": 2,
      "unit": "kg",
      "variant": null,
      "source_text": "2 kilo atta",
      "needs_review": false
    },
    {
      "product_mention": "amul butter cheruth",
      "quantity": 1,
      "unit": "pack",
      "variant": "small",
      "source_text": "1 amul butter cheruth",
      "needs_review": true
    }
  ],
  "clarification_question": null
}
```

Treat this as a proposed schema, not a claim that the model will always
return correct data. Validate all output and handle missing or malformed
fields.

### Rules

-   Gemma extracts meaning; catalogue code chooses the final SKU.
-   Prices and totals come only from the catalogue and deterministic
    code.
-   Ambiguous product variants require review.
-   Order confirmation is an explicit state transition.
-   Stock updates happen in one transaction with a unique source
    event/order ID.
-   Replayed messages must be idempotent.
-   Never execute arbitrary code returned by the model.

### Minimal internal interfaces

Agree on exact function signatures and keep them stable:

``` python
# Developer B owns catalogue and inventory helpers.
find_product_candidates(mention: str) -> list
get_product(product_id: str)
confirm_stock_deduction(order_id: str, items: list) -> result

# Developer A owns message and order flow.
parse_incoming_message(message: dict) -> dict
create_order(parsed_order: dict) -> dict
confirm_order(order_id: str) -> dict
```

These are illustrative contracts; adapt them to the actual codebase
before implementation. Avoid both developers editing the same file at
the same time.

------------------------------------------------------------------------

## 5. GitHub Instructions

### Step 1 --- Choose one integration branch

For a four-hour build, use a simple branch model: - `main`: always
runnable and demo-ready. - `feat/orderops`: Developer A's work. -
`feat/stock-chatops`: Developer B's work.

If the repository already has a branch convention, follow it rather than
restructuring the project during the event.

### Step 2 --- Clone and create branches

Both developers should clone the same repository. Each developer creates
their own feature branch:

``` bash
git clone <REPOSITORY_URL>
cd <REPOSITORY_DIRECTORY>
git switch main
git pull --ff-only origin main

# Developer A:
git switch -c feat/orderops

# Developer B, in their own clone:
git switch main
git switch -c feat/stock-chatops
```

Replace placeholders with the real repository URL and directory. If the
project already exists locally, do not clone over it; commit or safely
back up uncommitted work first.

### Step 3 --- Commit in small, working increments

Use descriptive commit messages:

``` bash
git add path/to/changed/files
git commit -m "feat: parse multilingual WhatsApp orders"
git push -u origin feat/orderops
```

Developer B can use:

``` bash
git add path/to/changed/files
git commit -m "feat: add idempotent stock ledger"
git push -u origin feat/stock-chatops
```

Make a small commit whenever a module reaches a working checkpoint. Do
not wait until the final hour to push.

### Step 4 --- Open pull requests

Open one pull request per feature branch: - `feat/orderops` → `main` -
`feat/stock-chatops` → `main`

The other developer reviews the diff, runs the relevant tests, and
checks that shared contracts are unchanged. With only four hours,
reviews should be short and focused.

### Step 5 --- Integrate early

Before merging, update the feature branch from `main`:

``` bash
git fetch origin
git switch feat/orderops
git merge origin/main
```

For Developer B:

``` bash
git fetch origin
git switch feat/stock-chatops
git merge origin/main
```

Resolve conflicts carefully, run tests, then push the updated branch.
Avoid force-pushing shared branches.

### Step 6 --- Merge and test the demo branch

After both branches pass review, merge the pull requests into `main` and
pull the latest version:

``` bash
git switch main
git pull --ff-only origin main
```

Run the complete application from a clean terminal. Test the actual demo
path, not just isolated functions.

If the repository's protections or the hackathon platform require
another merge workflow, follow those rules. Do not disable repository
protections just to save time.

### Step 7 --- Protect secrets and customer data

Never commit: - `.env` files with API keys. - WhatsApp
authentication/session files. - Customer conversations or phone
numbers. - Merchant UPI credentials or private configuration. - Local
databases containing real user data.

Add appropriate entries to `.gitignore`. Commit a sanitized
`.env.example` instead. Use synthetic demo messages and a dedicated test
account.

### Step 8 --- Final submission checklist

-   [ ] Both feature branches pushed.
-   [ ] Pull requests reviewed and merged.
-   [ ] `main` runs on the demo machine.
-   [ ] README contains setup instructions and model requirements.
-   [ ] `.env.example` is present; secrets are not committed.
-   [ ] Sample catalogue and synthetic test messages are included.
-   [ ] Demo flow and fallback are tested.
-   [ ] Known limitations and measured results are documented.
-   [ ] Repository is public if the event requires public submission.

------------------------------------------------------------------------

## 6. How to Use AI Coding Tools Effectively

AI coding tools can save time, but use them for bounded tasks and verify
the result immediately.

### Good tasks for an AI coding assistant

-   Generate a Pydantic schema for Gemma's JSON output.
-   Create seed data with product aliases and pack sizes.
-   Write unit tests for Malayalam/Manglish sample messages.
-   Implement an idempotent stock transaction from a precise
    specification.
-   Generate a print stylesheet for bills.
-   Review diffs for duplicate deductions, race conditions, missing
    validation, or secret leakage.
-   Explain unfamiliar errors and suggest the smallest safe fix.

### Avoid

-   Asking an agent to rewrite the entire repository.
-   Letting both developers' agents modify shared schema files
    simultaneously.
-   Accepting generated code without running it.
-   Putting API keys, WhatsApp sessions, or real customer data into
    prompts.
-   Spending more than 10--15 minutes debugging a non-essential feature.

### Suggested AI prompt template

``` text
You are contributing to BhashaOps, a hackathon prototype.

Task: <one bounded task>

Existing interface:
<paste the agreed function signature or schema>

Constraints:
- Do not change unrelated files.
- Do not duplicate the shared Gemma client.
- Treat model output as untrusted and validate it.
- Never calculate final prices with the language model.
- Add focused tests for success and failure cases.
- Report changed files, commands run, and any unverified assumptions.

Implement the smallest working solution.
```

------------------------------------------------------------------------

## 7. Testing Checklist

Use these as acceptance tests.

### Order interpretation

-   [ ] `chetta 2 kilo atta, 6 ande`
-   [ ] `randu kilo atta venam, 6 mutta koodi`
-   [ ] `രണ്ട് കിലോ ആട്ടയും ആറ് മുട്ടയും വേണം`
-   [ ] Unknown product is flagged instead of silently matched.
-   [ ] Unclear pack size enters review.
-   [ ] Correction such as `butter venda` is not treated as a new
    positive item.

### Inventory integrity

-   [ ] Confirmed order deducts stock once.
-   [ ] Replayed webhook does not create a duplicate order.
-   [ ] Repeated confirmation does not deduct stock again.
-   [ ] Out-of-stock item is flagged.
-   [ ] Supplier message does not increase stock until receipt
    confirmation.

### Final workflow

-   [ ] Total matches catalogue-derived arithmetic.
-   [ ] Bill and packing slip show the confirmed items and total.
-   [ ] Customer reply is a draft until approved.
-   [ ] UPI QR uses validated merchant details and exact amount.
-   [ ] WhatsApp failure can be bypassed using the local simulator.

Record the actual results; do not claim every test passes until it has
been run.

------------------------------------------------------------------------

## 8. Final Four-Hour Priority Order

1.  **P0:** message input → Gemma → catalogue match → review → correct
    bill.
2.  **P0:** save confirmed order and update stock exactly once.
3.  **P1:** automatic WhatsApp receive, packing slip, and approved
    customer reply.
4.  **P1:** low-stock warning and robust duplicate handling.
5.  **P2:** UPI QR and Chat2Ops demonstration.
6.  **Final 15 minutes:** freeze code, rehearse, verify repository and
    submit.

**Final rule:** a small, correct and testable end-to-end workflow beats
three partially connected features. Keep BhashaOps centered on
Malayalam/Manglish conversations becoming verified actions, and make
Gemma 4's contribution obvious in the live demo.

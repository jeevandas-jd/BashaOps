# Main Branch Plan

## Purpose
`main` must remain the stable, runnable integration branch for the BhashaOps hackathon MVP.

## Initial baseline
- FastAPI starts without a model runtime.
- `GET /api/health` returns a basic health response.
- Frontend scaffold can display whether the API is reachable.
- `.gitignore` excludes secrets, local databases, caches, WhatsApp sessions, and local model files.
- Model and database modules are explicit placeholders until implemented.

## Ownership
- Developer A: message intake, Gemma integration, interpretation, order workflow, pricing, bill.
- Developer B: database, catalogue, inventory ledger, idempotency, low-stock logic, dashboard.
- Shared: schema/API contract, integration tests, README, demo script.

## Rules
1. No direct commits to `main` while both developers are working in parallel; use feature branches.
2. Agree on schema and endpoint shapes before implementing both sides.
3. Merge small pull requests and run the health check and tests after each merge.
4. Stock changes only after order confirmation.
5. Confirmation and stock ledger updates must be atomic and idempotent.
6. Keep the simulator working even if WhatsApp is unavailable.
7. Do not commit `.env`, real customer data, WhatsApp sessions, or local database files.

## Baseline smoke test
From the repository root:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/api/health`. Expected response:
```json
{"status":"ok","service":"bhashaops-api","mode":"scaffold"}
```
This is only a scaffold health check; it does not mean the order workflow is implemented.

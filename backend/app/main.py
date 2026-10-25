"""BhashaOps FastAPI application entry point.

Run from the repository root:
    cd backend
    python -m uvicorn app.main:app --reload
"""
from fastapi import FastAPI

app = FastAPI(
    title="BhashaOps API",
    description="Turn multilingual shop conversations into reviewable business actions.",
    version="0.1.0",
)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """Basic health check; does not require Gemma or the database to be running."""
    return {"status": "ok", "service": "bhashaops-api", "mode": "scaffold"}

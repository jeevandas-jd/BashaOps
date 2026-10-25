"""Shared API/data contracts.

Keep status names and field names stable. Add Pydantic models here initially;
split into multiple schema modules when the project grows.
"""
from typing import Literal
from pydantic import BaseModel, Field


OrderStatus = Literal[
    "RECEIVED",
    "PARSING",
    "NEEDS_REVIEW",
    "READY_FOR_CONFIRMATION",
    "CONFIRMED",
    "FULFILLED",
    "CANCELLED",
    "FAILED",
]


class MessageIn(BaseModel):
    source: str = "simulator"
    external_message_id: str = Field(min_length=1, max_length=200)
    conversation_id: str | None = None
    sender_id: str | None = None
    text: str = Field(min_length=1, max_length=5000)


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str

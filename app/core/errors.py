"""Canonical error response envelope."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(..., examples=["not_found"])
    message: str = Field(..., examples=["Order not found"])
    details: Any | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody

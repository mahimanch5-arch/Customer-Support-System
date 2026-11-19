from __future__ import annotations

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    category: str | None = Field(
        None,
        pattern="^(refunds|returns|shipping|delays|damaged|payments|account|"
                "warranty|promotions|order_management|other)$",
    )
    order_number: str | None = None
    message: str = Field(..., min_length=1, max_length=4000)
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")


class TicketMessageOut(BaseModel):
    message_id: int
    sender: str
    body: str
    created_at: str


class TicketOut(BaseModel):
    ticket_id: int
    ticket_number: str
    customer_id: int | None = None
    order_id: int | None = None
    category: str | None = None
    subject: str | None = None
    status: str
    priority: str
    escalated: bool
    assigned_to: str
    created_at: str
    messages: list[TicketMessageOut] = []

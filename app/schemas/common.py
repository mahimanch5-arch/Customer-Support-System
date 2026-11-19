"""Shared schema primitives: pagination envelope + money formatting."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Money(BaseModel):
    """Money is stored as integer cents; expose both for clients."""
    cents: int
    currency: str = "USD"
    display: str = Field(..., examples=["$60.00"])

    @classmethod
    def of(cls, cents: int | None, currency: str = "USD") -> "Money | None":
        if cents is None:
            return None
        return cls(cents=cents, currency=currency, display=f"${cents / 100:,.2f}")


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int
    returned: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


def make_page(items: list[T], total: int, limit: int, offset: int) -> Page[T]:
    return Page[T](
        items=items,
        meta=PageMeta(total=total, limit=limit, offset=offset, returned=len(items)),
    )

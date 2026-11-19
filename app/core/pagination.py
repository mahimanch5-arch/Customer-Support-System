"""Pagination / sorting helpers shared across list endpoints."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

from app.core.exceptions import ValidationError


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int
    sort: str | None
    order: str  # 'asc' | 'desc'


def page_params(
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    sort: str | None = Query(None, description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
) -> PageParams:
    return PageParams(limit=limit, offset=offset, sort=sort, order=order)


def resolve_sort(params: PageParams, allowed: dict[str, str], default_sql: str) -> str:
    """Map a client sort field to a safe SQL ``ORDER BY`` clause (whitelist only)."""
    if not params.sort:
        return default_sql
    column = allowed.get(params.sort)
    if column is None:
        raise ValidationError(
            f"Cannot sort by '{params.sort}'.",
            details={"allowed": sorted(allowed)},
        )
    return f"{column} {params.order.upper()}"

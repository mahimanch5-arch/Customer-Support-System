"""Repository base helpers: parameterized query execution.

All DB access goes through these helpers so SQL stays in the repository layer
and every query is parameterized (no string interpolation of user input).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def fetch_one(self, sql: str, params: dict[str, Any] | None = None) -> dict | None:
        result = await self.session.execute(text(sql), params or {})
        row = result.mappings().first()
        return dict(row) if row is not None else None

    async def fetch_all(self, sql: str, params: dict[str, Any] | None = None) -> list[dict]:
        result = await self.session.execute(text(sql), params or {})
        return [dict(r) for r in result.mappings().all()]

    async def scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        result = await self.session.execute(text(sql), params or {})
        return result.scalar()

    async def execute(self, sql: str, params: dict[str, Any] | None = None):
        return await self.session.execute(text(sql), params or {})

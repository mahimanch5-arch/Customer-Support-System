"""Authentication, principals, and customer-ownership authorization.

Auth model (demo-grade but realistic):
  * Clients authenticate with `X-API-Key`. Each key maps to a named principal.
  * A principal may act **on behalf of** a customer via `X-Customer-Id`.
    This scopes every read/write to that customer and is how the agent calls
    its own tools: the chat endpoint mints an agent-service call scoped to the
    requesting customer, so the agent can never touch another customer's data.
  * Order/payment endpoints additionally verify that the resource's customer
    matches the effective customer scope (ownership check).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import AuthError, ForbiddenError

API_KEY_HEADER = "X-API-Key"
CUSTOMER_ID_HEADER = "X-Customer-Id"


@dataclass(frozen=True)
class Principal:
    """The authenticated caller."""
    name: str                       # 'public', 'agent', ...
    kind: str                       # 'service'
    customer_id: int | None = None  # effective customer scope, if any

    @property
    def is_agent(self) -> bool:
        return self.name == "agent"

    @property
    def scoped_to_customer(self) -> bool:
        return self.customer_id is not None


def authenticate(api_key: str | None, customer_id_header: str | None) -> Principal:
    if not api_key:
        raise AuthError("Missing API key.", code="missing_api_key")
    name = settings.api_key_map().get(api_key)
    if not name:
        raise AuthError("Invalid API key.", code="invalid_api_key")

    customer_id: int | None = None
    if customer_id_header is not None and customer_id_header != "":
        try:
            customer_id = int(customer_id_header)
        except (TypeError, ValueError):
            raise AuthError("Invalid X-Customer-Id header.", code="invalid_customer_scope")
        if customer_id <= 0:
            raise AuthError("Invalid X-Customer-Id header.", code="invalid_customer_scope")

    return Principal(name=name, kind="service", customer_id=customer_id)


def ensure_owns_customer(principal: Principal, resource_customer_id: int) -> None:
    """Fail closed if the principal is customer-scoped to a different customer."""
    if principal.scoped_to_customer and principal.customer_id != resource_customer_id:
        raise ForbiddenError(
            "You are not authorized to access this customer's data.",
            code="ownership_violation",
        )

"""Cross-cutting structural contracts shared by finance_api services.

Feature-scoped contracts live next to their domain (``*_protocols.py`` or the
feature package). This module must stay free of infrastructure imports.
"""

from typing import Protocol


class CategorizedAmountProtocol(Protocol):
    """Structural contract for any amount that can be aggregated by category."""

    amount: float
    category: str

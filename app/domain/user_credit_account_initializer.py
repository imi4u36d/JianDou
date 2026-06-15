"""Port interface for initializing credit state for newly activated users.

Mirrors the Java UserCreditAccountInitializer interface.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UserCreditAccountInitializer(Protocol):
    """Initializes credit state for newly activated or created users.

    Mirrors the Java UserCreditAccountInitializer interface.
    """

    def ensure_account(self, user_id: int) -> None:
        """Ensure a credit account exists for the given user."""
        ...

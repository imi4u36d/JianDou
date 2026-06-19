from __future__ import annotations

from typing import Protocol, TypeVar

T = TypeVar("T")


class OwnerResolver(Protocol[T]):
    def owner_user_id(self, candidate: T) -> int | None:
        """Return the owner user id for a candidate, or None for system-owned work."""
        ...


class TaskQueueFairScheduler:
    """Fair round-robin scheduler across owner queues."""

    SYSTEM_OWNER_KEY = "system"

    @classmethod
    def fair_order(
        cls,
        candidates: list[T],
        owner_resolver: OwnerResolver[T],
        last_dispatched_owner_key: str,
    ) -> list[T]:
        if not candidates:
            return []

        by_owner: dict[str, list[T]] = {}
        for candidate in candidates:
            key = cls.owner_key(owner_resolver.owner_user_id(candidate))
            by_owner.setdefault(key, []).append(candidate)

        owner_keys = list(by_owner.keys())
        owner_offset = cls._start_offset(owner_keys, last_dispatched_owner_key)
        ordered: list[T] = []

        while len(ordered) < len(candidates):
            consumed = False
            for idx in range(len(owner_keys)):
                owner_key = owner_keys[(owner_offset + idx) % len(owner_keys)]
                owner_queue = by_owner.get(owner_key)
                if not owner_queue:
                    continue
                ordered.append(owner_queue.pop(0))
                consumed = True
            if not consumed:
                break
        return ordered

    @classmethod
    def owner_key(cls, owner_user_id: int | None) -> str:
        if owner_user_id is None:
            return cls.SYSTEM_OWNER_KEY
        return f"user:{owner_user_id}"

    @staticmethod
    def _start_offset(owner_keys: list[str], last_dispatched_owner_key: str) -> int:
        if not owner_keys:
            return 0
        try:
            last_idx = owner_keys.index(last_dispatched_owner_key)
        except ValueError:
            return 0
        return (last_idx + 1) % len(owner_keys)

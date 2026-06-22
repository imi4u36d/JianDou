from __future__ import annotations

import pytest

pytestmark = pytest.mark.domain
from dataclasses import dataclass

from backend.domain.task_queue_fairness import TaskQueueFairScheduler
from backend.services.task_diagnosis_service import TaskQueueFairScheduler as CompatTaskQueueFairScheduler


@dataclass(frozen=True)
class Candidate:
    id: str
    owner_user_id: int | None


class CandidateOwnerResolver:
    def owner_user_id(self, candidate: Candidate) -> int | None:
        return candidate.owner_user_id


def test_fair_order_round_robins_without_dropping_single_remaining_items() -> None:
    candidates = [
        Candidate("a1", 1),
        Candidate("a2", 1),
        Candidate("b1", 2),
    ]

    ordered = TaskQueueFairScheduler.fair_order(candidates, CandidateOwnerResolver(), "")

    assert [item.id for item in ordered] == ["a1", "b1", "a2"]


def test_fair_order_starts_after_last_dispatched_owner() -> None:
    candidates = [
        Candidate("a1", 1),
        Candidate("b1", 2),
        Candidate("system1", None),
        Candidate("a2", 1),
    ]

    ordered = TaskQueueFairScheduler.fair_order(
        candidates,
        CandidateOwnerResolver(),
        TaskQueueFairScheduler.owner_key(1),
    )

    assert [item.id for item in ordered] == ["b1", "system1", "a1", "a2"]


def test_task_diagnosis_service_re_exports_scheduler_for_compatibility() -> None:
    candidates = [Candidate("system1", None)]

    assert CompatTaskQueueFairScheduler.owner_key(None) == "system"
    assert CompatTaskQueueFairScheduler.fair_order(candidates, CandidateOwnerResolver(), "") == candidates

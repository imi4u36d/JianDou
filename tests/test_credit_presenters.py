from types import SimpleNamespace

from backend.services.credit_presenters import account_to_dict, transaction_to_dict


def test_account_presenter_normalizes_nullable_totals() -> None:
    account = SimpleNamespace(id=1, user_id=7, balance=25, total_consumed=None, total_adjusted=None)

    assert account_to_dict(account) == {
        "id": 1,
        "userId": 7,
        "balance": 25,
        "totalConsumed": 0,
        "totalAdjusted": 0,
    }


def test_transaction_presenter_decodes_metadata_and_preserves_links() -> None:
    transaction = SimpleNamespace(
        transaction_id="credit-1",
        user_id=7,
        feature_code="VIDEO_GENERATION",
        transaction_type="CONSUME",
        amount_delta=-50,
        balance_before=60,
        balance_after=10,
        related_run_id="run-1",
        related_task_id="task-1",
        related_workflow_id="",
        reason="generate",
        metadata_json='{"source":"task"}',
        created_at="2026-07-11T00:00:00Z",
    )

    result = transaction_to_dict(transaction)

    assert result["metadata"] == {"source": "task"}
    assert result["relatedTaskId"] == "task-1"
    assert result["amountDelta"] == -50

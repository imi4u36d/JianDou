"""Pure response mapping for credit records."""

from __future__ import annotations

import json

from backend.models.credit import SysCreditAccount, SysCreditRule, SysCreditTransaction
from backend.models.user import SysUser


def account_to_dict(account: SysCreditAccount) -> dict:
    return {
        "id": account.id,
        "userId": account.user_id,
        "balance": account.balance or 0,
        "totalConsumed": account.total_consumed or 0,
        "totalAdjusted": account.total_adjusted or 0,
    }


def rule_to_dict(rule: SysCreditRule) -> dict:
    return {
        "featureCode": rule.feature_code,
        "displayName": rule.display_name,
        "cost": rule.cost or 0,
        "updatedAt": rule.updated_at,
    }


def transaction_to_dict(transaction: SysCreditTransaction) -> dict:
    metadata = {}
    if transaction.metadata_json:
        try:
            metadata = json.loads(transaction.metadata_json)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    return {
        "transactionId": transaction.transaction_id,
        "userId": transaction.user_id,
        "featureCode": transaction.feature_code,
        "transactionType": transaction.transaction_type,
        "amountDelta": transaction.amount_delta or 0,
        "balanceBefore": transaction.balance_before or 0,
        "balanceAfter": transaction.balance_after or 0,
        "relatedRunId": transaction.related_run_id,
        "relatedTaskId": transaction.related_task_id,
        "relatedWorkflowId": transaction.related_workflow_id,
        "reason": transaction.reason,
        "metadata": metadata,
        "createdAt": transaction.created_at,
    }


def credit_user_to_dict(
    user: SysUser,
    account: SysCreditAccount | None,
    stats: dict | None,
) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "status": user.status,
        "balance": account.balance if account else 0,
        "totalConsumed": account.total_consumed if account else 0,
        "totalAdjusted": account.total_adjusted if account else 0,
        "imageGenerationCount": stats["imageGenerationCount"] if stats else 0,
        "videoGenerationCount": stats["videoGenerationCount"] if stats else 0,
        "lastUsedAt": stats["lastUsedAt"] if stats else None,
    }

from __future__ import annotations

from typing import Literal, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class AdminRequestModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_camel),
        populate_by_name=True,
    )


class AdminOverviewResponse(BaseModel):
    total_tasks: int = 0
    queued_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0


class AdminTaskBatchResult(BaseModel):
    action: str = ""
    requested_count: int = 0
    succeeded_task_ids: list[str] = Field(default_factory=list)
    failed: list[dict] = Field(default_factory=list)


class AdminTaskBatchActionRequest(AdminRequestModel):
    action: Literal["terminate"] = "terminate"
    task_ids: list[str] = Field(default_factory=list, alias="taskIds")


class AdminModelProviderKeyRequest(AdminRequestModel):
    key: str
    api_key: str = Field(default="", alias="apiKey")


class AdminModelConfigKeysRequest(AdminRequestModel):
    providers: list[AdminModelProviderKeyRequest] = Field(default_factory=list)


class AdminCreateUserRequest(AdminRequestModel):
    username: str
    display_name: str = ""
    password: str
    role: str = "USER"
    status: str = "ACTIVE"
    task_concurrency_limit: int = 1


class AdminUpdateUserRequest(AdminRequestModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    task_concurrency_limit: Optional[int] = None


class AdminUpdateUserPasswordRequest(AdminRequestModel):
    password: str


class AdminUpdateUserStatusRequest(AdminRequestModel):
    action: Literal["enable", "disable"]


class AdminAdjustCreditRequest(AdminRequestModel):
    amount: int
    reason: str


class AdminUpdateCreditRuleRequest(AdminRequestModel):
    cost: int = Field(ge=0)


class AdminBulkTerminateTasksRequest(AdminRequestModel):
    task_ids: list[str] = Field(default_factory=list, alias="taskIds")


class AdminCreateInviteRequest(AdminRequestModel):
    role: str = "USER"
    expires_at: Optional[str] = Field(default=None, alias="expiresAt")

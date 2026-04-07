from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError

from backend_core.schemas import (
    AgentArtifact,
    AgentDashboardResponse,
    AgentDefinitionSummary,
    AgentEvent,
    AgentRunDetail,
    AgentRunSummary,
    AgentTimelineEvent,
)


router = APIRouter(prefix="/agents", tags=["agents"])


def _service(request: Request):
    return request.app.state.runtime.service


@router.get("", response_model=list[AgentDefinitionSummary])
def list_agents(request: Request) -> list[AgentDefinitionSummary]:
    return _service(request).list_agents()


@router.get("/dashboard", response_model=AgentDashboardResponse)
def agent_dashboard(request: Request) -> AgentDashboardResponse:
    return _service(request).get_agent_dashboard()


@router.get("/runs", response_model=list[AgentRunSummary])
def list_agent_runs(
    request: Request,
    agentKey: str | None = Query(default=None),
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AgentRunSummary]:
    return _service(request).list_agent_runs(
        agent_key=agentKey.strip() if agentKey else None,
        q=q.strip() if q else None,
        status=status.strip() if status else None,
        limit=limit,
    )


@router.get("/events", response_model=list[AgentTimelineEvent])
def list_agent_events(
    request: Request,
    agentKey: str | None = Query(default=None),
    runId: str | None = Query(default=None),
    level: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AgentTimelineEvent]:
    return _service(request).list_agent_events(
        agent_key=agentKey.strip() if agentKey else None,
        run_id=runId.strip() if runId else None,
        level=level.strip() if level else None,
        q=q.strip() if q else None,
        limit=limit,
    )


@router.get("/{agent_key}", response_model=AgentDefinitionSummary)
def get_agent(request: Request, agent_key: str) -> AgentDefinitionSummary:
    try:
        return _service(request).get_agent(agent_key)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{agent_key}/runs", response_model=AgentRunDetail)
async def create_agent_run(request: Request, agent_key: str) -> AgentRunDetail:
    try:
        payload: Any = await request.json()
        return _service(request).create_agent_run(agent_key, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=AgentRunDetail)
def get_agent_run(request: Request, run_id: str) -> AgentRunDetail:
    try:
        return _service(request).get_agent_run(run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/events", response_model=list[AgentEvent])
def get_agent_run_events(
    request: Request,
    run_id: str,
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[AgentEvent]:
    try:
        return _service(request).list_agent_run_events(run_id, limit=limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/artifacts", response_model=list[AgentArtifact])
def get_agent_run_artifacts(request: Request, run_id: str) -> list[AgentArtifact]:
    try:
        return _service(request).list_agent_run_artifacts(run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

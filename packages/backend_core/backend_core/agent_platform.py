from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal
import json
import re
import time

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from .media import RenderSegmentSpec, probe_media, render_output_segments
from .models import AgentArtifact, AgentDefinition, AgentEvent, AgentRun, Task
from .schemas import (
    AIDramaAgentRunRequest,
    AgentArtifact as AgentArtifactSchema,
    AgentDashboardAgent,
    AgentDashboardCounts,
    AgentDashboardResponse,
    AgentDefinitionSummary,
    AgentEvent as AgentEventSchema,
    AgentRunDetail,
    AgentRunStatus,
    AgentRunSummary,
    AgentTimelineEvent,
    CreateTaskRequest,
    ShortDramaAgentRunRequest,
    TaskDetail,
    TextMediaAgentRunRequest,
    TextMediaKind,
    TextScriptAgentRunRequest,
)
from .service import TaskService
from .storage import MediaStorage
from .text_generation import DEFAULT_SCRIPT_VISUAL_STYLE, TextGenerationEngine
from .utils import isoformat_utc, new_id, truncate_text, utcnow


@dataclass(frozen=True)
class _AgentProfile:
    key: str
    name: str
    summary: str
    category: str
    color: str
    icon: str
    run_path: str
    execution_mode: str
    system_prompt: str
    default_input: dict[str, Any]
    capabilities: list[str]
    sort_order: int


@dataclass(frozen=True)
class _ArtifactSpec:
    kind: str
    title: str
    mime_type: str | None = None
    text_content: str | None = None
    json_content: dict[str, Any] | None = None
    file_path: str | None = None
    file_url: str | None = None
    order_index: int = 0


@dataclass(frozen=True)
class _ExecutionResult:
    status: AgentRunStatus
    title: str
    summary: str | None
    output_text: str | None
    output_json: dict[str, Any]
    monitor_json: dict[str, Any]
    artifacts: list[_ArtifactSpec]
    events: list[dict[str, Any]]
    progress: int = 100
    source_task_id: str | None = None


@dataclass(frozen=True)
class _StoryboardShot:
    index: int
    shot_no: str
    shot_type: str
    visual_prompt: str
    dialogue: str
    duration_seconds: float


@dataclass(frozen=True)
class _AIDramaDirection:
    visual_style: str
    shot_count: int
    shot_duration_seconds: float
    total_duration_seconds: float
    intro_template: str
    outro_template: str
    transition_style: str
    reasoning: list[str]


AGENT_PROFILES: list[_AgentProfile] = [
    _AgentProfile(
        key="ai-drama",
        name="AI 剧总控 Agent",
        summary="输入正文后一键生成角色设定、分镜、镜头视频、拼接成片以及配音口型规划。",
        category="showrunner",
        color="#ef4444",
        icon="clapperboard",
        run_path="/api/v1/agents/ai-drama/runs",
        execution_mode="orchestrated-drama",
        system_prompt=(
            "你是一个 AI 剧总控 Agent，负责串联脚本、角色一致性、镜头生成、视频拼接和音频规划。"
            "输出必须包含可追踪的多阶段结果和最终成片。"
        ),
        default_input={
            "title": "暴雨车站",
            "text": "暴雨夜，少女在旧车站找到失踪哥哥留下的录音机。",
            "aspectRatio": "9:16",
            "continuitySeed": 2025,
            "includeKeyframes": True,
            "includeDubPlan": True,
            "includeLipsyncPlan": True,
        },
        capabilities=["one-click-drama", "storyboard-generation", "consistency-control", "video-stitching"],
        sort_order=5,
    ),
    _AgentProfile(
        key="short-drama",
        name="短剧剪辑 Agent",
        summary="输入素材、字幕和约束，生成可执行的短剧剪辑结果、分镜计划和产物摘要。",
        category="editing",
        color="#f97316",
        icon="scissors",
        run_path="/api/v1/agents/short-drama/runs",
        execution_mode="clip-planning",
        system_prompt=(
            "你是一个短剧剪辑导演 Agent，负责把素材整理成可执行的剪辑任务。"
            "输出应包含剪辑节奏、镜头分布、字幕理解、转场建议和成片说明。"
        ),
        default_input={
            "title": "高能短剧剪辑",
            "platform": "douyin",
            "aspectRatio": "9:16",
            "minDurationSeconds": 15,
            "maxDurationSeconds": 60,
            "outputCount": 3,
            "introTemplate": "hook",
            "outroTemplate": "brand",
        },
        capabilities=["clip-planning", "timeline-analysis", "render-output", "trace-monitoring"],
        sort_order=10,
    ),
    _AgentProfile(
        key="text-media",
        name="文生图 / 文生视频 Agent",
        summary="输入提示词即可产出图片或视频，统一管理版本、风格和媒体结果。",
        category="media",
        color="#4f7cff",
        icon="sparkles",
        run_path="/api/v1/agents/text-media/runs",
        execution_mode="text-generation",
        system_prompt=(
            "你是一个文本到媒体生成 Agent，负责把自然语言提示转化为图片或视频结果。"
            "输出应该包含媒体文件、生成提示词和模型运行信息。"
        ),
        default_input={
            "prompt": "暮色里的未来都市，霓虹与薄雾交错，电影感广角镜头。",
            "mediaKind": "image",
            "version": 1,
            "aspectRatio": "9:16",
        },
        capabilities=["image-generation", "video-generation", "prompt-shaping", "artifact-storage"],
        sort_order=20,
    ),
    _AgentProfile(
        key="text-script",
        name="文生脚本 Agent",
        summary="输入小说、故事片段或梗概，输出角色档案、场景设定和分镜脚本。",
        category="script",
        color="#22c55e",
        icon="book-open",
        run_path="/api/v1/agents/text-script/runs",
        execution_mode="markdown-script",
        system_prompt=(
            "你是一个短剧脚本生成 Agent，输出必须包含角色档案、场景设定、分镜表和音效建议。"
            "请始终保持视觉一致性和镜头语言专业性。"
        ),
        default_input={
            "text": "少女在暴雨夜闯进旧车站，发现失踪哥哥留下的录音机。",
            "visualStyle": DEFAULT_SCRIPT_VISUAL_STYLE,
        },
        capabilities=["script-generation", "character-anchoring", "shot-listing", "markdown-artifact"],
        sort_order=30,
    ),
]

DISABLED_SHORT_DRAMA_CONTENT_TYPES = {"travel"}
DISABLED_SHORT_DRAMA_STYLE_PRESETS = {
    "travel_citywalk",
    "travel_landscape",
    "travel_healing",
    "travel_roadtrip",
}


class AgentPlatformService(TaskService):
    def __init__(
        self,
        settings,
        session_factory,
        storage: MediaStorage,
        planner,
    ) -> None:
        super().__init__(settings=settings, session_factory=session_factory, storage=storage, planner=planner)
        self._agent_profiles = {profile.key: profile for profile in AGENT_PROFILES}
        self._seed_agent_definitions()

    def _seed_agent_definitions(self) -> None:
        with self.session() as session:
            for profile in AGENT_PROFILES:
                row = session.get(AgentDefinition, profile.key)
                if row is None:
                    row = AgentDefinition(
                        key=profile.key,
                        name=profile.name,
                        summary=profile.summary,
                        category=profile.category,
                        color=profile.color,
                        icon=profile.icon,
                        run_path=profile.run_path,
                        execution_mode=profile.execution_mode,
                        system_prompt=profile.system_prompt,
                        default_input_json=profile.default_input,
                        capabilities_json=profile.capabilities,
                        enabled=True,
                        sort_order=profile.sort_order,
                    )
                else:
                    row.name = profile.name
                    row.summary = profile.summary
                    row.category = profile.category
                    row.color = profile.color
                    row.icon = profile.icon
                    row.run_path = profile.run_path
                    row.execution_mode = profile.execution_mode
                    row.system_prompt = profile.system_prompt
                    row.default_input_json = profile.default_input
                    row.capabilities_json = profile.capabilities
                    row.enabled = True
                    row.sort_order = profile.sort_order
                session.add(row)
            session.commit()

    def _utc_iso(self) -> str:
        return isoformat_utc(utcnow())

    def _profile(self, agent_key: str) -> _AgentProfile:
        profile = self._agent_profiles.get(agent_key)
        if profile is None:
            raise LookupError("agent not found")
        return profile

    def _load_agent_definition(self, session, agent_key: str) -> AgentDefinition:
        row = session.get(AgentDefinition, agent_key)
        if row is None:
            raise LookupError("agent not found")
        return row

    def _load_agent_stats(self, session) -> dict[str, dict[str, Any]]:
        stats: dict[str, dict[str, Any]] = {
            profile.key: {
                "totalRuns": 0,
                "runningRuns": 0,
                "succeededRuns": 0,
                "failedRuns": 0,
                "lastRunAt": None,
                "lastRunStatus": None,
                "recentRuns": [],
            }
            for profile in AGENT_PROFILES
        }
        runs = session.scalars(select(AgentRun).options(selectinload(AgentRun.agent)).order_by(AgentRun.created_at.desc())).all()
        for run in runs:
            bucket = stats.setdefault(
                run.agent_key,
                {
                    "totalRuns": 0,
                    "runningRuns": 0,
                    "succeededRuns": 0,
                    "failedRuns": 0,
                    "lastRunAt": None,
                    "lastRunStatus": None,
                    "recentRuns": [],
                },
            )
            bucket["totalRuns"] += 1
            normalized_status = (run.status or "").lower()
            if normalized_status == AgentRunStatus.RUNNING.value:
                bucket["runningRuns"] += 1
            elif normalized_status == AgentRunStatus.SUCCEEDED.value:
                bucket["succeededRuns"] += 1
            elif normalized_status == AgentRunStatus.FAILED.value:
                bucket["failedRuns"] += 1
            if bucket["lastRunAt"] is None:
                bucket["lastRunAt"] = run.created_at
                bucket["lastRunStatus"] = run.status
            if len(bucket["recentRuns"]) < 5:
                bucket["recentRuns"].append(run)
        return stats

    def _agent_summary_from_definition(
        self,
        definition: AgentDefinition,
        stats: dict[str, Any],
    ) -> AgentDefinitionSummary:
        profile = self._profile(definition.key)
        return AgentDefinitionSummary(
            key=definition.key,
            name=definition.name,
            summary=definition.summary,
            category=definition.category,
            color=definition.color,
            icon=definition.icon,
            runPath=definition.run_path,
            executionMode=definition.execution_mode,
            capabilities=list(definition.capabilities_json or profile.capabilities),
            defaultInput=dict(definition.default_input_json or profile.default_input),
            enabled=definition.enabled,
            sortOrder=definition.sort_order,
            totalRuns=int(stats.get("totalRuns", 0)),
            runningRuns=int(stats.get("runningRuns", 0)),
            succeededRuns=int(stats.get("succeededRuns", 0)),
            failedRuns=int(stats.get("failedRuns", 0)),
            lastRunAt=_format_datetime(stats.get("lastRunAt")),
            lastRunStatus=_to_agent_status(stats.get("lastRunStatus")),
        )

    def _agent_summary(self, session, agent_key: str) -> AgentDefinitionSummary:
        definition = self._load_agent_definition(session, agent_key)
        stats = self._load_agent_stats(session).get(agent_key, {})
        return self._agent_summary_from_definition(definition, stats)

    def list_agents(self) -> list[AgentDefinitionSummary]:
        with self.session() as session:
            stats_by_key = self._load_agent_stats(session)
            rows = session.scalars(select(AgentDefinition).order_by(AgentDefinition.sort_order.asc(), AgentDefinition.name.asc())).all()
            return [self._agent_summary_from_definition(row, stats_by_key.get(row.key, {})) for row in rows]

    def get_agent(self, agent_key: str) -> AgentDefinitionSummary:
        with self.session() as session:
            return self._agent_summary(session, agent_key)

    def get_agent_dashboard(self) -> AgentDashboardResponse:
        with self.session() as session:
            stats_by_key = self._load_agent_stats(session)
            definitions = session.scalars(select(AgentDefinition).order_by(AgentDefinition.sort_order.asc(), AgentDefinition.name.asc())).all()
            all_runs = session.scalars(select(AgentRun)).all()
            runs = session.scalars(
                select(AgentRun)
                .options(selectinload(AgentRun.agent))
                .order_by(AgentRun.created_at.desc())
                .limit(12)
            ).all()
            total_runs = len(all_runs)
            total_artifacts = session.scalar(select(func.count(AgentArtifact.id))) or 0
            total_events = session.scalar(select(func.count(AgentEvent.id))) or 0

            dashboard_agents: list[AgentDashboardAgent] = []
            for row in definitions:
                stats = stats_by_key.get(row.key, {})
                run_count = int(stats.get("totalRuns", 0))
                succeeded = int(stats.get("succeededRuns", 0))
                failed = int(stats.get("failedRuns", 0))
                dashboard_agents.append(
                    AgentDashboardAgent(
                        key=row.key,
                        name=row.name,
                        category=row.category,
                        color=row.color,
                        enabled=row.enabled,
                        totalRuns=run_count,
                        runningRuns=int(stats.get("runningRuns", 0)),
                        succeededRuns=succeeded,
                        failedRuns=failed,
                        lastRunAt=_format_datetime(stats.get("lastRunAt")),
                        lastRunStatus=_to_agent_status(stats.get("lastRunStatus")),
                        successRate=round((succeeded / run_count) * 100.0, 1) if run_count else 0.0,
                    )
                )

            return AgentDashboardResponse(
                generatedAt=self._utc_iso(),
                counts=AgentDashboardCounts(
                    totalAgents=len(definitions),
                    totalRuns=int(total_runs),
                    queuedRuns=len([run for run in all_runs if run.status == AgentRunStatus.QUEUED.value]),
                    runningRuns=len([run for run in all_runs if run.status == AgentRunStatus.RUNNING.value]),
                    succeededRuns=len([run for run in all_runs if run.status == AgentRunStatus.SUCCEEDED.value]),
                    failedRuns=len([run for run in all_runs if run.status == AgentRunStatus.FAILED.value]),
                    totalArtifacts=int(total_artifacts),
                    totalEvents=int(total_events),
                ),
                agents=dashboard_agents,
                recentRuns=[self._run_summary_from_row(row) for row in runs],
            )

    def list_agent_runs(
        self,
        *,
        agent_key: str | None = None,
        q: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[AgentRunSummary]:
        with self.session() as session:
            stmt = select(AgentRun).options(selectinload(AgentRun.agent))
            filters = []
            if agent_key:
                filters.append(AgentRun.agent_key == agent_key)
            if status:
                filters.append(AgentRun.status == status)
            if q:
                pattern = f"%{q}%"
                filters.append(
                    AgentRun.title.ilike(pattern)
                    | AgentRun.summary.ilike(pattern)
                    | AgentRun.input_text.ilike(pattern)
                    | AgentRun.output_text.ilike(pattern)
                    | AgentRun.agent_key.ilike(pattern)
                )
            if filters:
                stmt = stmt.where(*filters)
            rows = session.scalars(stmt.order_by(AgentRun.created_at.desc()).limit(limit)).all()
            return [self._run_summary_from_row(row) for row in rows]

    def list_agent_events(
        self,
        *,
        agent_key: str | None = None,
        run_id: str | None = None,
        level: str | None = None,
        q: str | None = None,
        limit: int = 200,
    ) -> list[AgentTimelineEvent]:
        with self.session() as session:
            stmt = (
                select(AgentEvent, AgentRun, AgentDefinition)
                .join(AgentRun, AgentEvent.run_id == AgentRun.id)
                .join(AgentDefinition, AgentRun.agent_key == AgentDefinition.key)
            )
            filters = []
            if agent_key:
                filters.append(AgentRun.agent_key == agent_key)
            if run_id:
                filters.append(AgentEvent.run_id == run_id)
            if level:
                filters.append(AgentEvent.level == level)
            if q:
                pattern = f"%{q}%"
                filters.append(
                    AgentEvent.stage.ilike(pattern)
                    | AgentEvent.event.ilike(pattern)
                    | AgentEvent.message.ilike(pattern)
                    | AgentRun.title.ilike(pattern)
                    | AgentDefinition.name.ilike(pattern)
                )
            if filters:
                stmt = stmt.where(*filters)
            rows = session.execute(stmt.order_by(AgentEvent.created_at.desc()).limit(limit)).all()
            return [self._timeline_event_from_row(event, run, agent) for event, run, agent in rows]

    def get_agent_run(self, run_id: str) -> AgentRunDetail:
        with self.session() as session:
            stmt = (
                select(AgentRun)
                .options(
                    selectinload(AgentRun.agent),
                    selectinload(AgentRun.artifacts),
                    selectinload(AgentRun.events),
                )
                .where(AgentRun.id == run_id)
            )
            run = session.scalars(stmt).one_or_none()
            if run is None:
                raise LookupError("agent run not found")
            return self._run_detail_from_row(run)

    def list_agent_run_artifacts(self, run_id: str) -> list[AgentArtifactSchema]:
        with self.session() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise LookupError("agent run not found")
            artifacts = session.scalars(
                select(AgentArtifact)
                .where(AgentArtifact.run_id == run_id)
                .order_by(AgentArtifact.order_index.asc(), AgentArtifact.created_at.asc())
            ).all()
            return [self._artifact_schema(artifact) for artifact in artifacts]

    def list_agent_run_events(self, run_id: str, limit: int = 500) -> list[AgentEventSchema]:
        with self.session() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise LookupError("agent run not found")
            events = session.scalars(
                select(AgentEvent)
                .where(AgentEvent.run_id == run_id)
                .order_by(AgentEvent.created_at.asc())
                .limit(limit)
            ).all()
            return [self._event_schema(event) for event in events]

    def create_short_drama_run(self, payload: ShortDramaAgentRunRequest) -> AgentRunDetail:
        payload_dict = payload.model_dump()
        if str(payload_dict.get("mixcutContentType") or "").strip() in DISABLED_SHORT_DRAMA_CONTENT_TYPES:
            payload_dict["mixcutContentType"] = "generic"
        if str(payload_dict.get("mixcutStylePreset") or "").strip() in DISABLED_SHORT_DRAMA_STYLE_PRESETS:
            payload_dict["mixcutStylePreset"] = "director"
        request = CreateTaskRequest.model_validate(payload_dict)
        title = payload.title.strip() or self._profile("short-drama").name
        input_text = payload.creativePrompt or payload.transcriptText or title
        input_json = payload_dict
        run_id = self._create_agent_run_record(
            agent_key="short-drama",
            title=title,
            input_text=input_text,
            input_json=input_json,
        )
        try:
            result = self._execute_short_drama_run(
                request,
                run_id=run_id,
                input_json=input_json,
                title=title,
                input_text=input_text,
            )
        except Exception as exc:
            return self._fail_run(
                run_id,
                title=title,
                agent_key="short-drama",
                error=exc,
                input_json=input_json,
            )
        return self._finalize_run(run_id, result)

    def create_ai_drama_run(self, payload: AIDramaAgentRunRequest) -> AgentRunDetail:
        title = payload.title.strip() or self._profile("ai-drama").name
        input_json = payload.model_dump()
        run_id = self._create_agent_run_record(
            agent_key="ai-drama",
            title=title,
            input_text=payload.text,
            input_json=input_json,
        )
        try:
            result = self._execute_ai_drama_run(payload, run_id=run_id, title=title)
        except Exception as exc:
            return self._fail_run(
                run_id,
                title=title,
                agent_key="ai-drama",
                error=exc,
                input_json=input_json,
            )
        return self._finalize_run(run_id, result)

    def create_text_media_run(self, payload: TextMediaAgentRunRequest) -> AgentRunDetail:
        title = self._media_run_title(payload)
        input_text = payload.prompt
        input_json = payload.model_dump()
        run_id = self._create_agent_run_record(
            agent_key="text-media",
            title=title,
            input_text=input_text,
            input_json=input_json,
        )
        try:
            result = self._execute_text_media_run(payload, title=title, input_text=input_text)
        except Exception as exc:
            return self._fail_run(
                run_id,
                title=title,
                agent_key="text-media",
                error=exc,
                input_json=input_json,
            )
        return self._finalize_run(run_id, result)

    def create_text_script_run(self, payload: TextScriptAgentRunRequest) -> AgentRunDetail:
        title = self._script_run_title(payload)
        input_text = payload.text
        input_json = payload.model_dump()
        run_id = self._create_agent_run_record(
            agent_key="text-script",
            title=title,
            input_text=input_text,
            input_json=input_json,
        )
        try:
            result = self._execute_text_script_run(payload, title=title, input_text=input_text)
        except Exception as exc:
            return self._fail_run(
                run_id,
                title=title,
                agent_key="text-script",
                error=exc,
                input_json=input_json,
            )
        return self._finalize_run(run_id, result)

    def create_agent_run(self, agent_key: str, payload: Any) -> AgentRunDetail:
        if agent_key == "ai-drama":
            if not isinstance(payload, AIDramaAgentRunRequest):
                payload = AIDramaAgentRunRequest.model_validate(payload)
            return self.create_ai_drama_run(payload)
        if agent_key == "short-drama":
            if not isinstance(payload, ShortDramaAgentRunRequest):
                payload = ShortDramaAgentRunRequest.model_validate(payload)
            return self.create_short_drama_run(payload)
        if agent_key == "text-media":
            if not isinstance(payload, TextMediaAgentRunRequest):
                payload = TextMediaAgentRunRequest.model_validate(payload)
            return self.create_text_media_run(payload)
        if agent_key == "text-script":
            if not isinstance(payload, TextScriptAgentRunRequest):
                payload = TextScriptAgentRunRequest.model_validate(payload)
            return self.create_text_script_run(payload)
        raise LookupError("agent not found")

    def _create_agent_run_record(
        self,
        *,
        agent_key: str,
        title: str,
        input_text: str | None,
        input_json: dict[str, Any],
        source_task_id: str | None = None,
    ) -> str:
        with self.session() as session:
            self._load_agent_definition(session, agent_key)
            run = AgentRun(
                id=new_id("run"),
                agent_key=agent_key,
                title=title,
                status=AgentRunStatus.RUNNING.value,
                progress=0,
                input_text=input_text,
                input_json=input_json,
                summary=f"{title} 已受理",
                output_text=None,
                output_json={},
                monitor_json={"stage": "accepted"},
                source_task_id=source_task_id,
                error_message=None,
                started_at=utcnow(),
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            self._insert_event(
                session,
                run_id=run.id,
                stage="api",
                event="run.accepted",
                level="INFO",
                message="agent run accepted",
                payload={"agentKey": agent_key, "title": title},
            )
            session.commit()
            return run.id

    def _fail_run(
        self,
        run_id: str,
        *,
        title: str,
        agent_key: str,
        error: Exception,
        input_json: dict[str, Any],
    ) -> AgentRunDetail:
        error_message = truncate_text(str(error), 800) or "agent run failed"
        with self.session() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise LookupError("agent run not found")
            run.status = AgentRunStatus.FAILED.value
            run.progress = 100
            run.summary = f"{title} 执行失败"
            run.output_text = None
            run.output_json = {"error": error_message}
            run.monitor_json = {
                "source": "agent-platform",
                "status": "failed",
                "error": error_message,
                "input": input_json,
                "agentKey": agent_key,
            }
            run.error_message = error_message
            run.finished_at = utcnow()
            self._insert_event(
                session,
                run_id=run_id,
                stage="agent",
                event="run.failed",
                level="ERROR",
                message=error_message,
                payload={"agentKey": agent_key, "error": error_message},
            )
            session.commit()
        return self.get_agent_run(run_id)

    def _insert_event(
        self,
        session,
        *,
        run_id: str,
        stage: str,
        event: str,
        level: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        order_index = session.scalar(
            select(func.count(AgentEvent.id)).where(AgentEvent.run_id == run_id)
        ) or 0
        row = AgentEvent(
            id=new_id("evt"),
            run_id=run_id,
            stage=stage,
            event=event,
            level=level,
            message=truncate_text(message, 1200) or message,
            payload_json=payload or {},
            order_index=int(order_index),
        )
        session.add(row)

    def _append_run_event(
        self,
        run_id: str,
        *,
        stage: str,
        event: str,
        level: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self.session() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise LookupError("agent run not found")
            self._insert_event(
                session,
                run_id=run_id,
                stage=stage,
                event=event,
                level=level,
                message=message,
                payload=payload,
            )
            session.commit()

    def _update_run_state(
        self,
        run_id: str,
        *,
        status: AgentRunStatus | str | None = None,
        progress: int | None = None,
        summary: str | None = None,
        monitor_json: dict[str, Any] | None = None,
        monitor_patch: dict[str, Any] | None = None,
        source_task_id: str | None = None,
        finished: bool = False,
    ) -> None:
        with self.session() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise LookupError("agent run not found")
            if status is not None:
                run.status = status.value if isinstance(status, AgentRunStatus) else str(status)
            if progress is not None:
                run.progress = max(0, min(100, int(progress)))
            if summary is not None:
                next_summary = truncate_text(summary, 800)
                if next_summary:
                    run.summary = next_summary
            if monitor_json is not None:
                run.monitor_json = dict(monitor_json)
            elif monitor_patch:
                next_monitor = dict(run.monitor_json or {})
                next_monitor.update(monitor_patch)
                run.monitor_json = next_monitor
            if source_task_id is not None:
                run.source_task_id = source_task_id
            if finished:
                run.finished_at = utcnow()
            session.commit()

    def _sync_short_drama_run_state(
        self,
        *,
        run_id: str,
        task_detail: TaskDetail,
        title: str,
        input_json: dict[str, Any],
    ) -> None:
        trace = super().get_task_trace(task_detail.id, limit=1000)
        task_status = str(getattr(task_detail.status, "value", task_detail.status) or "").upper()
        if task_status == "ANALYZING":
            summary = "短剧剪辑任务正在分析素材。"
        elif task_status == "PLANNING":
            summary = "短剧剪辑任务正在生成规划方案。"
        elif task_status == "RENDERING":
            summary = "短剧剪辑任务正在渲染输出。"
        elif task_status == "COMPLETED":
            summary = f"短剧剪辑任务已完成，输出 {len(task_detail.outputs)} 条成片。"
        elif task_status == "FAILED":
            summary = "短剧剪辑任务执行失败。"
        else:
            summary = f"{title} 已受理，等待任务执行。"

        with self.session() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise LookupError("agent run not found")
            previous_monitor = dict(run.monitor_json or {})
            previous_trace_count = int(previous_monitor.get("mirroredTraceCount") or 0)
            for entry in trace[previous_trace_count:]:
                self._insert_event(
                    session,
                    run_id=run_id,
                    stage=getattr(entry, "stage", "task"),
                    event=getattr(entry, "event", "step"),
                    level=getattr(entry, "level", "INFO"),
                    message=getattr(entry, "message", ""),
                    payload=getattr(entry, "payload", {}) or {},
                )
            run.status = _task_status_to_agent_status(task_detail.status).value
            run.progress = max(0, min(100, int(task_detail.progress or 0)))
            run.summary = summary
            run.source_task_id = task_detail.id
            run.monitor_json = {
                "source": "task-service",
                "taskId": task_detail.id,
                "taskStatus": task_status,
                "outputCount": len(task_detail.outputs),
                "progress": int(task_detail.progress or 0),
                "input": input_json,
                "mirroredTraceCount": len(trace),
            }
            session.commit()

    def _insert_artifact(
        self,
        session,
        *,
        run_id: str,
        spec: _ArtifactSpec,
    ) -> None:
        order_index = session.scalar(
            select(func.count(AgentArtifact.id)).where(AgentArtifact.run_id == run_id)
        ) or 0
        row = AgentArtifact(
            id=new_id("art"),
            run_id=run_id,
            kind=spec.kind,
            title=spec.title,
            mime_type=spec.mime_type,
            text_content=spec.text_content,
            json_content=spec.json_content or {},
            file_path=spec.file_path,
            file_url=spec.file_url,
            order_index=max(int(order_index), spec.order_index),
        )
        session.add(row)

    def _finalize_run(self, run_id: str, result: _ExecutionResult) -> AgentRunDetail:
        with self.session() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise LookupError("agent run not found")
            run.status = result.status.value
            run.progress = result.progress
            run.summary = result.summary
            run.output_text = result.output_text
            run.output_json = result.output_json
            run.monitor_json = result.monitor_json
            if result.source_task_id:
                run.source_task_id = result.source_task_id
            run.error_message = None if result.status != AgentRunStatus.FAILED else result.output_json.get("error", "")
            run.finished_at = utcnow()
            for event in result.events:
                self._insert_event(
                    session,
                    run_id=run_id,
                    stage=str(event.get("stage", "agent")),
                    event=str(event.get("event", "step")),
                    level=str(event.get("level", "INFO")),
                    message=str(event.get("message", "")),
                    payload=dict(event.get("payload") or {}),
                )
            for spec in result.artifacts:
                self._insert_artifact(session, run_id=run_id, spec=spec)
            if not result.monitor_json:
                run.monitor_json = {"status": result.status.value, "summary": result.summary}
            session.commit()
        return self.get_agent_run(run_id)

    def _execute_short_drama_run(
        self,
        payload: CreateTaskRequest,
        *,
        run_id: str,
        input_json: dict[str, Any],
        title: str,
        input_text: str | None,
    ) -> _ExecutionResult:
        initial_task = super().create_task(payload)
        self._append_run_event(
            run_id,
            stage="task",
            event="task.created",
            level="INFO",
            message=f"已创建剪辑任务 {initial_task.id}",
            payload={"taskId": initial_task.id},
        )
        self._sync_short_drama_run_state(
            run_id=run_id,
            task_detail=initial_task,
            title=title,
            input_json=input_json,
        )
        task_detail = self._wait_for_task_terminal_state(
            initial_task.id,
            on_progress=lambda current: self._sync_short_drama_run_state(
                run_id=run_id,
                task_detail=current,
                title=title,
                input_json=input_json,
            ),
        )
        trace = super().get_task_trace(task_detail.id, limit=1000)
        output_json = task_detail.model_dump()
        task_status = _task_status_to_agent_status(task_detail.status)
        if task_status == AgentRunStatus.SUCCEEDED:
            summary = f"短剧剪辑任务已完成，输出 {len(task_detail.outputs)} 条成片。"
        elif task_status == AgentRunStatus.FAILED:
            summary = "短剧剪辑任务执行失败。"
        else:
            summary = "短剧剪辑任务仍在处理中，已生成统一 Agent 运行记录。"
        artifacts: list[_ArtifactSpec] = [
            _ArtifactSpec(
                kind="task-detail",
                title="任务详情 JSON",
                mime_type="application/json",
                json_content=output_json,
                order_index=0,
            )
        ]
        source_asset_ids = [item for item in input_json.get("sourceAssetIds", []) if isinstance(item, str)]
        source_file_names = [item for item in input_json.get("sourceFileNames", []) if isinstance(item, str)]
        for index, asset_id in enumerate(source_asset_ids):
            label = source_file_names[index] if index < len(source_file_names) else asset_id
            artifacts.append(
                _ArtifactSpec(
                    kind="source-asset",
                    title=f"源素材 · {label}",
                    mime_type="application/json",
                    json_content={"sourceAssetId": asset_id, "sourceFileName": label},
                    order_index=index + 1,
                )
            )
        if task_detail.plan:
            artifacts.append(
                _ArtifactSpec(
                    kind="clip-plan",
                    title="分镜计划 JSON",
                    mime_type="application/json",
                    json_content=[clip.model_dump() for clip in task_detail.plan],
                    order_index=len(artifacts),
                )
            )
        for index, output in enumerate(task_detail.outputs, start=len(artifacts)):
            artifacts.append(
                _ArtifactSpec(
                    kind="clip-output",
                    title=output.title,
                    mime_type="video/mp4",
                    file_url=output.downloadUrl,
                    text_content=output.reason,
                    json_content=output.model_dump(),
                    order_index=index,
                )
            )

        monitor_json = {
            "source": "task-service",
            "taskId": task_detail.id,
            "taskStatus": task_detail.status.value if hasattr(task_detail.status, "value") else str(task_detail.status),
            "outputCount": len(task_detail.outputs),
            "progress": task_detail.progress,
            "input": input_json,
        }
        return _ExecutionResult(
            status=task_status,
            title=title,
            summary=summary,
            output_text=task_detail.creativePrompt or task_detail.transcriptPreview or summary,
            output_json=output_json,
            monitor_json=monitor_json,
            artifacts=artifacts,
            events=[
                {
                    "stage": "agent",
                    "event": "run.completed" if task_status == AgentRunStatus.SUCCEEDED else "run.finalized",
                    "level": "INFO" if task_status != AgentRunStatus.FAILED else "ERROR",
                    "message": summary,
                    "payload": {"taskId": task_detail.id, "traceCount": len(trace)},
                }
            ],
            progress=int(task_detail.progress),
            source_task_id=task_detail.id,
        )

    def _execute_ai_drama_run(
        self,
        payload: AIDramaAgentRunRequest,
        *,
        run_id: str,
        title: str,
    ) -> _ExecutionResult:
        def report_progress(
            *,
            stage: str,
            event: str,
            progress: int,
            summary: str,
            message: str,
            payload_data: dict[str, Any] | None = None,
            level: str = "INFO",
            monitor_patch: dict[str, Any] | None = None,
        ) -> None:
            self._append_run_event(
                run_id,
                stage=stage,
                event=event,
                level=level,
                message=message,
                payload=payload_data,
            )
            self._update_run_state(
                run_id,
                status=AgentRunStatus.RUNNING,
                progress=progress,
                summary=summary,
                monitor_patch={
                    "stage": stage,
                    "progress": progress,
                    **(monitor_patch or {}),
                },
            )

        started_at = time.monotonic()
        direction = _decide_ai_drama_direction(
            title=title,
            text=payload.text,
            aspect_ratio=payload.aspectRatio,
            visual_style=payload.visualStyle,
            total_duration_seconds=payload.totalDurationSeconds,
            shot_count=payload.shotCount,
            shot_duration_seconds=payload.shotDurationSeconds,
            intro_template=payload.introTemplate,
            outro_template=payload.outroTemplate,
            transition_style=payload.transitionStyle,
        )
        visual_style = direction.visual_style
        report_progress(
            stage="showrunner",
            event="pipeline.started",
            progress=5,
            summary="AI 剧总控正在完成导演决策并生成剧本。",
            message="AI 剧总控已启动，正在拆解故事、判定风格和镜头节奏。",
            payload_data={
                "requestedShotCount": payload.shotCount,
                "requestedShotDurationSeconds": payload.shotDurationSeconds,
                "requestedTotalDurationSeconds": payload.totalDurationSeconds,
                "aspectRatio": payload.aspectRatio,
            },
            monitor_patch={"visualStyle": visual_style},
        )
        report_progress(
            stage="showrunner",
            event="direction.decided",
            progress=9,
            summary="AI 剧总控已完成导演决策，正在生成剧本。",
            message="导演 Agent 已决定视觉风格、镜头规模、片头片尾和转场策略",
            payload_data={
                "visualStyle": direction.visual_style,
                "shotCount": direction.shot_count,
                "shotDurationSeconds": direction.shot_duration_seconds,
                "totalDurationSeconds": direction.total_duration_seconds,
                "introTemplate": direction.intro_template,
                "outroTemplate": direction.outro_template,
                "transitionStyle": direction.transition_style,
                "reasoning": direction.reasoning,
            },
            monitor_patch={
                "visualStyle": direction.visual_style,
                "shotCount": direction.shot_count,
                "shotDurationSeconds": direction.shot_duration_seconds,
                "totalDurationSeconds": direction.total_duration_seconds,
                "introTemplate": direction.intro_template,
                "outroTemplate": direction.outro_template,
                "transitionStyle": direction.transition_style,
                "directorReasoning": direction.reasoning,
            },
        )
        script_payload = TextScriptAgentRunRequest(text=payload.text, visualStyle=visual_style)
        script_response = self.text_generator.generate_text_script(script_payload)
        script_raw = script_response.model_dump()
        script_markdown = str(script_raw.get("scriptMarkdown") or "")
        report_progress(
            stage="script-writer",
            event="script.generated",
            progress=14,
            summary="AI 剧总控正在锁定角色和分镜。",
            message=f"文生脚本 Agent 输出 {len(script_markdown)} 字 Markdown 剧本",
            payload_data={"requestedShotCount": direction.shot_count, "visualStyle": visual_style},
            monitor_patch={"scriptLength": len(script_markdown)},
        )

        shots = _extract_storyboard_shots(
            script_markdown,
            preferred_count=direction.shot_count,
            fallback_duration=direction.shot_duration_seconds,
            source_text=payload.text,
        )
        if not shots:
            raise RuntimeError("storyboard parser did not produce any shots")

        character_anchors = _extract_character_anchors(script_markdown)
        continuity = _build_continuity_plan(
            title=title,
            visual_style=visual_style,
            continuity_seed=payload.continuitySeed,
            character_anchors=character_anchors,
            shot_count=len(shots),
        )
        version = _pick_media_version(visual_style)
        transition_style = direction.transition_style
        report_progress(
            stage="consistency-director",
            event="continuity.locked",
            progress=22,
            summary="AI 剧总控正在生成镜头素材。",
            message="角色锚点、统一风格和 continuity seed 已锁定",
            payload_data=continuity,
            monitor_patch={"continuitySeed": payload.continuitySeed, "shotCount": len(shots)},
        )
        artifacts: list[_ArtifactSpec] = [
            _ArtifactSpec(
                kind="markdown",
                title="剧本与分镜 Markdown",
                mime_type="text/markdown",
                text_content=script_markdown,
                file_path=str(script_raw.get("markdownFilePath") or "") or None,
                file_url=str(script_raw.get("markdownFileUrl") or script_raw.get("downloadUrl") or "") or None,
                json_content=script_raw,
                order_index=0,
            ),
            _ArtifactSpec(
                kind="consistency-plan",
                title="角色与风格一致性方案",
                mime_type="application/json",
                json_content=continuity,
                order_index=1,
            ),
            _ArtifactSpec(
                kind="storyboard",
                title="分镜 JSON",
                mime_type="application/json",
                json_content={"shots": [_shot_to_dict(item) for item in shots]},
                order_index=2,
            ),
        ]

        generated_shots: list[dict[str, Any]] = []
        stitch_segments: list[RenderSegmentSpec] = []
        artifact_index = len(artifacts)
        for shot in shots:
            shot_prompt = _compose_shot_prompt(
                shot=shot,
                visual_style=visual_style,
                continuity=continuity,
            )
            keyframe_raw: dict[str, Any] | None = None
            keyframe_url: str | None = None
            if payload.includeKeyframes:
                keyframe_response = self.text_generator.generate_text_image(
                    {
                        "prompt": shot_prompt,
                        "version": version,
                        "width": 1080 if payload.aspectRatio == "9:16" else 1920,
                        "height": 1920 if payload.aspectRatio == "9:16" else 1080,
                        "extras": {
                            "styleHint": visual_style,
                            "lightingHint": continuity["styleLock"],
                        },
                    }
                )
                keyframe_raw = keyframe_response.model_dump()
                keyframe_url = str(keyframe_raw.get("fileUrl") or keyframe_raw.get("outputUrl") or "") or None
                artifacts.append(
                    _ArtifactSpec(
                        kind="keyframe",
                        title=f"关键帧 {shot.shot_no}",
                        mime_type=str(keyframe_raw.get("mimeType") or "image/svg+xml"),
                        file_path=str(keyframe_raw.get("filePath") or "") or None,
                        file_url=keyframe_url,
                        json_content=keyframe_raw,
                        order_index=artifact_index,
                    )
                )
                artifact_index += 1

            video_response = self.text_generator.generate_text_video(
                {
                    "prompt": shot_prompt,
                    "version": version,
                    "width": 1080 if payload.aspectRatio == "9:16" else 1920,
                    "height": 1920 if payload.aspectRatio == "9:16" else 1080,
                    "durationSeconds": shot.duration_seconds,
                    "extras": {
                        "styleHint": visual_style,
                        "cameraHint": shot.shot_type,
                        "lightingHint": continuity["styleLock"],
                    },
                }
            )
            video_raw = video_response.model_dump()
            relative_video_path = str(video_raw.get("filePath") or "").strip()
            if not relative_video_path:
                raise RuntimeError(f"shot {shot.shot_no} did not return a local video path")
            absolute_video_path = (self.storage.root / relative_video_path).resolve()
            if not absolute_video_path.exists():
                raise RuntimeError(f"shot {shot.shot_no} video artifact missing: {absolute_video_path.as_posix()}")
            video_probe = probe_media(absolute_video_path)
            segment_duration = max(1.0, float(video_probe.durationSeconds or shot.duration_seconds))
            stitch_segments.append(
                RenderSegmentSpec(
                    source_path=absolute_video_path,
                    start_seconds=0.0,
                    end_seconds=segment_duration,
                    has_audio=bool(video_probe.hasAudio),
                )
            )
            artifacts.append(
                _ArtifactSpec(
                    kind="shot-video",
                    title=f"镜头视频 {shot.shot_no}",
                    mime_type=str(video_raw.get("mimeType") or "video/mp4"),
                    file_path=relative_video_path,
                    file_url=str(video_raw.get("fileUrl") or video_raw.get("outputUrl") or "") or None,
                    json_content=video_raw,
                    order_index=artifact_index,
                )
            )
            artifact_index += 1
            generated_shots.append(
                {
                    **_shot_to_dict(shot),
                    "prompt": shot_prompt,
                    "keyframe": keyframe_raw or {},
                    "video": video_raw,
                }
            )
            report_progress(
                stage="media-artist",
                event="shot.rendered",
                progress=22 + int(50 * (len(generated_shots) / max(len(shots), 1))),
                summary=f"AI 剧总控正在生成镜头素材（{len(generated_shots)}/{len(shots)}）。",
                message=f"{shot.shot_no} 已完成{'关键帧与' if payload.includeKeyframes else ''}视频镜头生成",
                payload_data={
                    "shotNo": shot.shot_no,
                    "durationSeconds": shot.duration_seconds,
                    "hasKeyframe": payload.includeKeyframes,
                },
                monitor_patch={"renderedShots": len(generated_shots)},
            )

        stitched_relative_path, stitched_public_url, stitched_duration = self._stitch_ai_drama_segments(
            run_id=run_id,
            segments=stitch_segments,
            aspect_ratio=payload.aspectRatio,
            intro_template=direction.intro_template,
            outro_template=direction.outro_template,
            transition_style=transition_style,
        )
        stitch_plan = {
            "introTemplate": direction.intro_template,
            "outroTemplate": direction.outro_template,
            "transitionStyle": transition_style,
            "clipCount": len(stitch_segments),
            "estimatedDurationSeconds": stitched_duration,
            "timeline": [
                {"shotNo": shot["shotNo"], "durationSeconds": shot["video"].get("durationSeconds") or shot["durationSeconds"]}
                for shot in generated_shots
            ],
        }
        artifacts.append(
            _ArtifactSpec(
                kind="stitched-video",
                title="AI 剧拼接成片",
                mime_type="video/mp4",
                file_path=stitched_relative_path,
                file_url=stitched_public_url,
                json_content=stitch_plan,
                order_index=artifact_index,
            )
        )
        artifact_index += 1
        artifacts.append(
            _ArtifactSpec(
                kind="stitch-plan",
                title="视频拼接算法方案",
                mime_type="application/json",
                json_content=stitch_plan,
                order_index=artifact_index,
            )
        )
        artifact_index += 1
        report_progress(
            stage="stitch-algorithm",
            event="timeline.composed",
            progress=84,
            summary="AI 剧总控正在编排成片与收尾方案。",
            message=f"算法 Agent 已完成 {len(stitch_segments)} 段镜头拼接",
            payload_data=stitch_plan,
            monitor_patch={"finalVideoUrl": stitched_public_url, "durationSeconds": stitched_duration},
        )

        dub_plan = _build_dub_plan(title=title, shots=shots) if payload.includeDubPlan else None
        if dub_plan is not None:
            artifacts.append(
                _ArtifactSpec(
                    kind="dub-plan",
                    title="AI 配音方案",
                    mime_type="application/json",
                    json_content=dub_plan,
                    order_index=artifact_index,
                )
            )
            artifact_index += 1
            report_progress(
                stage="voice-director",
                event="tts.planned",
                progress=90 if payload.includeLipsyncPlan else 95,
                summary="AI 剧总控正在收敛配音与节奏方案。",
                message="已生成对白配音与字幕节奏建议",
                payload_data={"lineCount": dub_plan["lineCount"]},
            )

        lipsync_plan = _build_lipsync_plan(shots=shots, continuity_seed=payload.continuitySeed) if payload.includeLipsyncPlan else None
        if lipsync_plan is not None:
            artifacts.append(
                _ArtifactSpec(
                    kind="lipsync-plan",
                    title="口型同步方案",
                    mime_type="application/json",
                    json_content=lipsync_plan,
                    order_index=artifact_index,
                )
            )
            report_progress(
                stage="lipsync-agent",
                event="lipsync.planned",
                progress=96,
                summary="AI 剧总控正在整理最终交付结果。",
                message="已生成口型驱动与角色嘴型绑定计划",
                payload_data={"shotCount": len(shots)},
            )

        elapsed = round(time.monotonic() - started_at, 3)
        summary = f"AI 剧已生成，共 {len(shots)} 个镜头，已输出拼接成片。"
        pipeline_stages = [
            stage
            for stage in [
                "script-writer",
                "consistency-director",
                "media-artist",
                "stitch-algorithm",
                "voice-director" if payload.includeDubPlan else None,
                "lipsync-agent" if payload.includeLipsyncPlan else None,
            ]
            if stage
        ]
        output_json = {
            "title": title,
            "visualStyle": visual_style,
            "aspectRatio": payload.aspectRatio,
            "shotCount": len(shots),
            "continuitySeed": payload.continuitySeed,
            "shotDurationSeconds": direction.shot_duration_seconds,
            "totalDurationSeconds": direction.total_duration_seconds,
            "introTemplate": direction.intro_template,
            "outroTemplate": direction.outro_template,
            "transitionStyle": transition_style,
            "directorDecision": {
                "visualStyle": direction.visual_style,
                "shotCount": direction.shot_count,
                "shotDurationSeconds": direction.shot_duration_seconds,
                "totalDurationSeconds": direction.total_duration_seconds,
                "introTemplate": direction.intro_template,
                "outroTemplate": direction.outro_template,
                "transitionStyle": direction.transition_style,
                "reasoning": direction.reasoning,
            },
            "script": script_raw,
            "consistency": continuity,
            "storyboard": {"shots": [_shot_to_dict(item) for item in shots]},
            "generatedShots": generated_shots,
            "stitchPlan": stitch_plan,
            "dubPlan": dub_plan or {},
            "lipsyncPlan": lipsync_plan or {},
            "finalVideoUrl": stitched_public_url,
            "finalVideoPath": stitched_relative_path,
            "durationSeconds": stitched_duration,
        }
        return _ExecutionResult(
            status=AgentRunStatus.SUCCEEDED,
            title=title,
            summary=summary,
            output_text=summary,
            output_json=output_json,
            monitor_json={
                "pipeline": pipeline_stages,
                "shotCount": len(shots),
                "shotDurationSeconds": direction.shot_duration_seconds,
                "totalDurationSeconds": direction.total_duration_seconds,
                "introTemplate": direction.intro_template,
                "outroTemplate": direction.outro_template,
                "transitionStyle": transition_style,
                "continuitySeed": payload.continuitySeed,
                "elapsedSeconds": elapsed,
                "finalVideoUrl": stitched_public_url,
                "visualStyle": visual_style,
                "directorReasoning": direction.reasoning,
            },
            artifacts=artifacts,
            events=[
                {
                    "stage": "agent",
                    "event": "run.completed",
                    "level": "INFO",
                    "message": summary,
                    "payload": {"shotCount": len(shots), "finalVideoUrl": stitched_public_url},
                }
            ],
            progress=100,
        )

    def _wait_for_task_terminal_state(
        self,
        task_id: str,
        timeout_seconds: float = 90.0,
        on_progress: Callable[[TaskDetail], None] | None = None,
    ) -> TaskDetail:
        deadline = time.monotonic() + timeout_seconds
        last_detail = super().get_task_detail(task_id)
        if on_progress is not None:
            on_progress(last_detail)
        while time.monotonic() < deadline:
            current = super().get_task_detail(task_id)
            last_detail = current
            if on_progress is not None:
                on_progress(current)
            normalized_status = str(getattr(current.status, "value", current.status) or "").upper()
            if normalized_status in {"COMPLETED", "FAILED"}:
                return current
            time.sleep(0.5)
        return last_detail

    def _stitch_ai_drama_segments(
        self,
        *,
        run_id: str,
        segments: list[RenderSegmentSpec],
        aspect_ratio: str,
        intro_template: str,
        outro_template: str,
        transition_style: str,
    ) -> tuple[str, str, float]:
        output_dir = self.storage.outputs_root / "agent_runs" / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "final_cut.mp4"
        result = render_output_segments(
            segments=segments,
            output_path=output_path,
            aspect_ratio=aspect_ratio,
            intro_template=intro_template,
            outro_template=outro_template,
            transition_style=transition_style,
        )
        relative_path = output_path.resolve().relative_to(self.storage.root.resolve()).as_posix()
        return relative_path, self.storage.build_public_url(relative_path), round(result.duration_seconds, 3)

    def _execute_text_media_run(
        self,
        payload: TextMediaAgentRunRequest,
        *,
        title: str,
        input_text: str | None,
    ) -> _ExecutionResult:
        engine_payload = {
            "prompt": payload.prompt,
            "version": payload.version,
            "providerModel": payload.providerModel if payload.mediaKind == "video" else None,
            "width": payload.width or (1080 if payload.aspectRatio == "9:16" else 1920),
            "height": payload.height or (1920 if payload.aspectRatio == "9:16" else 1080),
            "durationSeconds": payload.durationSeconds if payload.mediaKind == "video" else None,
            "extras": {
                "styleHint": payload.visualStyle or payload.stylePreset or "",
                "cameraHint": payload.stylePreset or "",
            },
        }
        response = (
            self.text_generator.generate_text_image(engine_payload)
            if payload.mediaKind == TextMediaKind.IMAGE.value
            else self.text_generator.generate_text_video(engine_payload)
        )
        raw = response.model_dump()
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        call_chain = raw.get("callChain") if isinstance(raw.get("callChain"), list) else []
        output_url = str(raw.get("outputUrl") or raw.get("fileUrl") or "")
        if not output_url:
            raise RuntimeError("text media response did not include output url")
        summary = f"{'图片' if payload.mediaKind == 'image' else '视频'}已生成。"
        artifacts = [
            _ArtifactSpec(
                kind="media-asset",
                title="生成媒体文件",
                mime_type=str(raw.get("mimeType") or ("image/png" if payload.mediaKind == "image" else "video/mp4")),
                file_url=output_url,
                json_content=raw,
                order_index=0,
            )
        ]
        shaped_prompt = str(raw.get("shapedPrompt") or metadata.get("shapedPrompt") or "")
        if shaped_prompt:
            artifacts.append(
                _ArtifactSpec(
                    kind="shaped-prompt",
                    title="提示词编排结果",
                    mime_type="text/plain",
                    text_content=shaped_prompt,
                    order_index=1,
                )
            )
        events = [_call_chain_to_event(row) for row in call_chain]
        return _ExecutionResult(
            status=AgentRunStatus.SUCCEEDED,
            title=title,
            summary=summary,
            output_text=str(raw.get("prompt") or payload.prompt),
            output_json=raw,
            monitor_json={
                "source": raw.get("source", "remote"),
                "modelInfo": raw.get("modelInfo") or metadata.get("modelInfo") or {},
                "stylePreset": payload.stylePreset,
                "visualStyle": payload.visualStyle or "",
                "outputUrl": output_url,
                "mediaKind": payload.mediaKind,
            },
            artifacts=artifacts,
            events=events,
            progress=100,
        )

    def _execute_text_script_run(
        self,
        payload: TextScriptAgentRunRequest,
        *,
        title: str,
        input_text: str | None,
    ) -> _ExecutionResult:
        response = self.text_generator.generate_text_script(payload)
        raw = response.model_dump()
        summary = "脚本已生成。"
        markdown = str(raw.get("scriptMarkdown") or "")
        markdown_file_url = str(raw.get("markdownFileUrl") or raw.get("downloadUrl") or "").strip() or None
        markdown_file_path = str(raw.get("markdownFilePath") or "").strip() or None
        artifacts = [
            _ArtifactSpec(
                kind="markdown",
                title="Markdown 脚本",
                mime_type="text/markdown",
                text_content=markdown,
                file_path=markdown_file_path,
                file_url=markdown_file_url,
                json_content=raw,
                order_index=0,
            )
        ]
        call_chain = raw.get("callChain") if isinstance(raw.get("callChain"), list) else []
        events = [_call_chain_to_event(row) for row in call_chain]
        return _ExecutionResult(
            status=AgentRunStatus.SUCCEEDED,
            title=title,
            summary=summary,
            output_text=markdown,
            output_json=raw,
            monitor_json={
                "source": raw.get("source", "remote"),
                "modelInfo": raw.get("modelInfo") or {},
                "visualStyle": raw.get("visualStyle") or payload.visualStyle or DEFAULT_SCRIPT_VISUAL_STYLE,
                "scriptLength": len(markdown),
                "downloadUrl": markdown_file_url,
            },
            artifacts=artifacts,
            events=events,
            progress=100,
        )

    def _run_summary_from_row(self, run: AgentRun) -> AgentRunSummary:
        agent = run.agent or None
        agent_name = agent.name if agent else self._profile(run.agent_key).name
        agent_color = agent.color if agent else self._profile(run.agent_key).color
        return AgentRunSummary(
            id=run.id,
            agentKey=run.agent_key,
            agentName=agent_name,
            agentColor=agent_color,
            status=_to_agent_status(run.status) or AgentRunStatus.RUNNING,
            title=run.title,
            summary=run.summary,
            progress=int(run.progress or 0),
            inputText=run.input_text,
            outputText=run.output_text,
            sourceTaskId=run.source_task_id,
            artifactCount=len(run.artifacts or []),
            eventCount=len(run.events or []),
            createdAt=_format_datetime(run.created_at) or self._utc_iso(),
            startedAt=_format_datetime(run.started_at),
            finishedAt=_format_datetime(run.finished_at),
            durationSeconds=_duration_seconds(run.started_at, run.finished_at),
        )

    def _run_detail_from_row(self, run: AgentRun) -> AgentRunDetail:
        summary = self._run_summary_from_row(run)
        agent = run.agent or self._profile(run.agent_key)
        agent_definition = AgentDefinitionSummary(
            key=agent.key if isinstance(agent, AgentDefinition) else agent.key,
            name=agent.name if isinstance(agent, AgentDefinition) else agent.name,
            summary=agent.summary if isinstance(agent, AgentDefinition) else agent.summary,
            category=agent.category if isinstance(agent, AgentDefinition) else agent.category,
            color=agent.color if isinstance(agent, AgentDefinition) else agent.color,
            icon=agent.icon if isinstance(agent, AgentDefinition) else agent.icon,
            runPath=agent.run_path if isinstance(agent, AgentDefinition) else agent.run_path,
            executionMode=agent.execution_mode if isinstance(agent, AgentDefinition) else agent.execution_mode,
            capabilities=list((agent.capabilities_json if isinstance(agent, AgentDefinition) else agent.capabilities) or []),
            defaultInput=dict((agent.default_input_json if isinstance(agent, AgentDefinition) else agent.default_input) or {}),
            enabled=agent.enabled if isinstance(agent, AgentDefinition) else True,
            sortOrder=agent.sort_order if isinstance(agent, AgentDefinition) else 0,
        )
        return AgentRunDetail(
            **summary.model_dump(),
            inputJson=dict(run.input_json or {}),
            outputJson=dict(run.output_json or {}),
            monitor=dict(run.monitor_json or {}),
            agent=agent_definition,
            artifacts=[self._artifact_schema(artifact) for artifact in run.artifacts or []],
            events=[self._event_schema(event) for event in run.events or []],
        )

    def _artifact_schema(self, artifact: AgentArtifact) -> AgentArtifactSchema:
        return AgentArtifactSchema(
            id=artifact.id,
            kind=artifact.kind,
            title=artifact.title,
            mimeType=artifact.mime_type,
            textContent=artifact.text_content,
            jsonContent=dict(artifact.json_content or {}),
            filePath=artifact.file_path,
            fileUrl=artifact.file_url,
            orderIndex=int(artifact.order_index or 0),
            createdAt=_format_datetime(artifact.created_at) or self._utc_iso(),
        )

    def _event_schema(self, event: AgentEvent) -> AgentEventSchema:
        return AgentEventSchema(
            timestamp=_format_datetime(event.created_at) or self._utc_iso(),
            level=event.level,
            stage=event.stage,
            event=event.event,
            message=event.message,
            payload=dict(event.payload_json or {}),
        )

    def _timeline_event_from_row(
        self,
        event: AgentEvent,
        run: AgentRun,
        agent: AgentDefinition,
    ) -> AgentTimelineEvent:
        return AgentTimelineEvent(
            timestamp=_format_datetime(event.created_at) or self._utc_iso(),
            level=event.level,
            stage=event.stage,
            event=event.event,
            message=event.message,
            payload=dict(event.payload_json or {}),
            runId=run.id,
            agentKey=agent.key,
            agentName=agent.name,
            runStatus=_to_agent_status(run.status) or AgentRunStatus.RUNNING,
            runTitle=run.title,
        )

    def _media_run_title(self, payload: TextMediaAgentRunRequest) -> str:
        kind_label = "文生图" if payload.mediaKind == "image" else "文生视频"
        return f"{kind_label} · {truncate_text(payload.prompt, 18) or '未命名提示词'}"

    def _script_run_title(self, payload: TextScriptAgentRunRequest) -> str:
        return f"文生脚本 · {truncate_text(payload.text, 18) or '未命名正文'}"


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return isoformat_utc(value)


def _duration_seconds(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return max(0.0, (end - start).total_seconds())


def _to_agent_status(value: Any) -> AgentRunStatus | None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    for candidate in AgentRunStatus:
        if candidate.value == normalized:
            return candidate
    return None


def _task_status_to_agent_status(value: Any) -> AgentRunStatus:
    normalized = str(getattr(value, "value", value) or "").strip().upper()
    if normalized == "COMPLETED":
        return AgentRunStatus.SUCCEEDED
    if normalized == "FAILED":
        return AgentRunStatus.FAILED
    if normalized in {"ANALYZING", "PLANNING", "RENDERING"}:
        return AgentRunStatus.RUNNING
    return AgentRunStatus.QUEUED


def _call_chain_to_event(entry: dict[str, Any]) -> dict[str, Any]:
    status = str(entry.get("status", "ok")).lower()
    level = "INFO"
    if status == "error":
        level = "ERROR"
    elif status == "retry":
        level = "WARN"
    return {
        "stage": entry.get("stage", "model"),
        "event": entry.get("event", "step"),
        "level": level,
        "message": entry.get("message", ""),
        "payload": entry.get("details") or {},
    }


def _task_trace_to_event(entry) -> dict[str, Any]:
    return {
        "stage": getattr(entry, "stage", "task"),
        "event": getattr(entry, "event", "step"),
        "level": getattr(entry, "level", "INFO"),
        "message": getattr(entry, "message", ""),
        "payload": getattr(entry, "payload", {}) or {},
    }


def _decide_ai_drama_direction(
    *,
    title: str,
    text: str,
    aspect_ratio: str,
    visual_style: str | None,
    total_duration_seconds: float | None,
    shot_count: int | None,
    shot_duration_seconds: float | None,
    intro_template: str | None,
    outro_template: str | None,
    transition_style: str | None,
) -> _AIDramaDirection:
    normalized_text = f"{title}\n{text}".strip()
    visual_style = (visual_style or "").strip() or None
    intro_template = (intro_template or "").strip() or None
    outro_template = (outro_template or "").strip() or None
    transition_style = (transition_style or "").strip() or None
    suspense_hits = sum(keyword in normalized_text for keyword in ["暴雨", "失踪", "秘密", "录音", "深夜", "悬疑", "惊悚", "车站", "追逐"])
    action_hits = sum(keyword in normalized_text for keyword in ["追逐", "战斗", "枪", "爆炸", "对峙", "冲进", "逃亡", "突袭"])
    fantasy_hits = sum(keyword in normalized_text for keyword in ["未来", "赛博", "机械", "宇宙", "异界", "魔法", "神", "星"])
    romance_hits = sum(keyword in normalized_text for keyword in ["告白", "心动", "重逢", "拥抱", "恋", "婚礼", "想念"])
    healing_hits = sum(keyword in normalized_text for keyword in ["日常", "午后", "街角", "家", "治愈", "成长", "回忆", "风"])

    if visual_style and visual_style.strip():
        chosen_style = visual_style.strip()
        style_reason = "沿用用户指定视觉风格。"
    elif suspense_hits >= max(action_hits, fantasy_hits, romance_hits, healing_hits) and suspense_hits > 0:
        chosen_style = "冷色悬疑电影写实风格"
        style_reason = "正文包含悬疑和压迫线索，优先采用冷色电影写实风格。"
    elif action_hits >= max(fantasy_hits, romance_hits, healing_hits) and action_hits > 0:
        chosen_style = "高对比动作电影风格"
        style_reason = "正文节奏偏冲突和追逐，适合高对比动作电影风格。"
    elif fantasy_hits >= max(romance_hits, healing_hits) and fantasy_hits > 0:
        chosen_style = "奇幻电影概念艺术风格"
        style_reason = "正文世界观偏奇幻或未来感，采用概念艺术取向。"
    elif romance_hits >= healing_hits and romance_hits > 0:
        chosen_style = "柔光情绪电影风格"
        style_reason = "正文情绪以人物关系为主，采用柔光情绪电影风格。"
    elif healing_hits > 0:
        chosen_style = "生活流治愈电影风格"
        style_reason = "正文偏生活流和回忆感，采用治愈型电影风格。"
    else:
        chosen_style = "写实电影叙事风格"
        style_reason = "正文题材未明显偏向单一类型，采用通用写实电影叙事风格。"

    estimated_complexity = len([char for char in normalized_text if char not in {" ", "\n", "\t"}])
    auto_shot_count = 5 if estimated_complexity < 80 else 6 if estimated_complexity < 180 else 7 if estimated_complexity < 360 else 8
    if action_hits > 0:
        auto_shot_count += 1
    if romance_hits > 0 and action_hits == 0:
        auto_shot_count -= 1
    if aspect_ratio == "16:9" and auto_shot_count < 7:
        auto_shot_count += 1
    auto_shot_count = max(4, min(8, auto_shot_count))

    if shot_duration_seconds is not None:
        chosen_shot_duration = round(float(shot_duration_seconds), 1)
        duration_reason = "沿用用户指定单镜头时长。"
    elif action_hits > 0:
        chosen_shot_duration = 2.8
        duration_reason = "动作和冲突场景需要更快切换节奏。"
    elif suspense_hits > 0:
        chosen_shot_duration = 3.4
        duration_reason = "悬疑场景需要兼顾信息揭示和压迫感。"
    elif romance_hits > 0 or healing_hits > 0:
        chosen_shot_duration = 4.5
        duration_reason = "情绪和关系场景需要更长停留来承载表演。"
    else:
        chosen_shot_duration = 3.8
        duration_reason = "通用叙事场景使用中等镜头时长平衡节奏和信息量。"

    auto_total_duration = round(auto_shot_count * chosen_shot_duration, 1)
    chosen_total_duration = round(float(total_duration_seconds), 1) if total_duration_seconds is not None else auto_total_duration
    chosen_total_duration = max(6.0, min(90.0, chosen_total_duration))

    if shot_count is not None:
        chosen_shot_count = max(4, min(8, int(shot_count)))
        shot_reason = f"沿用用户指定镜头数：{chosen_shot_count}。"
    else:
        inferred_shot_count = int(round(chosen_total_duration / max(chosen_shot_duration, 1.0)))
        chosen_shot_count = max(4, min(8, inferred_shot_count if total_duration_seconds is not None else auto_shot_count))
        shot_reason = f"根据题材复杂度和总时长约束自动决定镜头数：{chosen_shot_count}。"

    if shot_duration_seconds is None and total_duration_seconds is not None:
        chosen_shot_duration = round(chosen_total_duration / chosen_shot_count, 1)
        chosen_shot_duration = max(2.0, min(8.0, chosen_shot_duration))
        duration_reason = "根据目标总时长和镜头数自动回推单镜头时长。"

    chosen_total_duration = round(chosen_shot_count * chosen_shot_duration, 1)
    total_reason = (
        f"沿用用户指定总时长约束：{chosen_total_duration:.1f} 秒。"
        if total_duration_seconds is not None
        else f"根据题材和节奏自动决定总时长：{chosen_total_duration:.1f} 秒。"
    )

    if intro_template:
        chosen_intro = intro_template
        intro_reason = "沿用用户指定片头模板。"
    elif action_hits > 0:
        chosen_intro = "flash_hook"
        intro_reason = "动作题材优先用闪切钩子快速入戏。"
    elif suspense_hits > 0:
        chosen_intro = "cold_open"
        intro_reason = "悬疑题材适合冷开场直接抛出谜面。"
    elif romance_hits > 0:
        chosen_intro = "pressure_build"
        intro_reason = "人物关系题材更适合情绪递进式片头。"
    else:
        chosen_intro = "hook"
        intro_reason = "默认使用冲突钩子片头稳定建立观看动机。"

    if outro_template:
        chosen_outro = outro_template
        outro_reason = "沿用用户指定片尾模板。"
    elif suspense_hits > 0:
        chosen_outro = "question_freeze"
        outro_reason = "悬疑题材适合用反问或停顿留悬念。"
    elif action_hits > 0:
        chosen_outro = "call_to_action"
        outro_reason = "动作题材适合强烈收束并推动下一步动作。"
    else:
        chosen_outro = "follow_hook"
        outro_reason = "叙事型短剧默认保留追更钩子。"

    if transition_style:
        chosen_transition = transition_style
        transition_reason = "沿用用户指定转场策略。"
    elif action_hits > 0:
        chosen_transition = "cut"
        transition_reason = "动作段落优先硬切保持速度。"
    elif suspense_hits > 0:
        chosen_transition = "fade_black"
        transition_reason = "悬疑段落适合黑场压迫式转场。"
    elif romance_hits > 0 or healing_hits > 0:
        chosen_transition = "crossfade"
        transition_reason = "情绪场景适合柔和溶解转场。"
    else:
        chosen_transition = "crossfade"
        transition_reason = "默认采用稳定的电影化溶解转场。"

    return _AIDramaDirection(
        visual_style=chosen_style,
        shot_count=chosen_shot_count,
        shot_duration_seconds=chosen_shot_duration,
        total_duration_seconds=chosen_total_duration,
        intro_template=chosen_intro,
        outro_template=chosen_outro,
        transition_style=chosen_transition,
        reasoning=[style_reason, shot_reason, duration_reason, total_reason, intro_reason, outro_reason, transition_reason],
    )


def _extract_storyboard_shots(
    markdown: str,
    *,
    preferred_count: int,
    fallback_duration: float,
    source_text: str,
) -> list[_StoryboardShot]:
    shots: list[_StoryboardShot] = []
    lines = markdown.replace("\r\n", "\n").split("\n")
    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [item.strip() for item in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        header_signature = "".join(cells[:3])
        if "镜号" in header_signature or "---" in header_signature or ":---" in header_signature:
            continue
        shot_no = cells[0] or f"{len(shots) + 1:03d}"
        shot_type = cells[1] or "中景 / 固定镜头"
        visual_prompt = cells[2] or cells[1] or truncate_text(source_text, 80) or "剧情镜头"
        dialogue = cells[3] if len(cells) > 3 else ""
        duration_text = cells[4] if len(cells) > 4 else ""
        shots.append(
            _StoryboardShot(
                index=len(shots) + 1,
                shot_no=shot_no,
                shot_type=shot_type,
                visual_prompt=visual_prompt,
                dialogue=dialogue,
                duration_seconds=_parse_duration_seconds(duration_text, fallback_duration),
            )
        )
        if len(shots) >= preferred_count:
            break
    if shots:
        return shots

    fragments = [
        fragment.strip(" 。，！!？?；;：:\n")
        for fragment in re.split(r"[。！？!?；;\n]+", source_text)
        if fragment.strip()
    ]
    for index, fragment in enumerate(fragments[:preferred_count], start=1):
        shots.append(
            _StoryboardShot(
                index=index,
                shot_no=f"{index:03d}",
                shot_type="中景 / 轻推镜头",
                visual_prompt=fragment,
                dialogue="",
                duration_seconds=float(fallback_duration),
            )
        )
    return shots


def _extract_character_anchors(markdown: str) -> list[str]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    anchors: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if "分镜脚本" in line:
            break
        if line.startswith(("*", "-", "•")) or "角色" in line:
            cleaned = re.sub(r"^[*\-•]\s*", "", line).strip()
            if cleaned:
                anchors.append(cleaned)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in anchors:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:6]


def _parse_duration_seconds(raw_value: str, fallback_duration: float) -> float:
    text = str(raw_value or "").strip().lower()
    if not text:
        return float(fallback_duration)
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return float(fallback_duration)
    try:
        parsed = float(match.group(1))
    except Exception:
        return float(fallback_duration)
    return max(2.0, min(12.0, parsed))


def _build_continuity_plan(
    *,
    title: str,
    visual_style: str,
    continuity_seed: int,
    character_anchors: list[str],
    shot_count: int,
) -> dict[str, Any]:
    role_anchor_text = " / ".join(character_anchors[:4]) or "沿用主角外观、服装和情绪弧线"
    return {
        "title": title,
        "visualStyle": visual_style,
        "continuitySeed": continuity_seed,
        "characterAnchors": character_anchors,
        "styleLock": f"{visual_style}，角色造型统一，服装和发型连续，seed={continuity_seed}",
        "roleAnchorText": role_anchor_text,
        "shotCount": shot_count,
        "controlNotes": [
            "所有镜头保持同一角色外观锚点，不随镜头切换漂移",
            "颜色、光线和景别变化服从统一视觉风格",
            "后续口型同步沿用同一角色参考与 seed",
        ],
    }


def _compose_shot_prompt(
    *,
    shot: _StoryboardShot,
    visual_style: str,
    continuity: dict[str, Any],
) -> str:
    prompt_parts = [
        shot.visual_prompt,
        f"镜头语言：{shot.shot_type}",
        f"视觉风格：{visual_style}",
        f"角色一致性：{continuity.get('roleAnchorText') or continuity.get('styleLock')}",
    ]
    if shot.dialogue:
        prompt_parts.append(f"对白/字幕情绪：{shot.dialogue}")
    prompt_parts.append("保持同一主角脸型、服装、发型和色彩氛围。")
    return "；".join(part.strip() for part in prompt_parts if part and part.strip())


def _pick_media_version(visual_style: str) -> int:
    normalized = visual_style.lower()
    if any(keyword in normalized for keyword in ["日系", "anime", "手绘", "插画"]):
        return 2
    if any(keyword in normalized for keyword in ["奇幻", "fantasy", "史诗"]):
        return 8
    if any(keyword in normalized for keyword in ["赛博", "cyber", "霓虹"]):
        return 4
    if any(keyword in normalized for keyword in ["水彩", "dream", "梦"]):
        return 5
    return 1


def _build_dub_plan(*, title: str, shots: list[_StoryboardShot]) -> dict[str, Any]:
    lines = []
    for shot in shots:
        if not shot.dialogue:
            continue
        lines.append(
            {
                "shotNo": shot.shot_no,
                "text": shot.dialogue,
                "durationSeconds": shot.duration_seconds,
                "voiceTone": "情绪递进、贴合镜头节奏",
                "subtitleStrategy": "按短句断开，句尾保留情绪停顿",
            }
        )
    return {
        "title": title,
        "lineCount": len(lines),
        "providerSuggestion": "ElevenLabs / CosyVoice / 自定义 TTS",
        "lines": lines,
    }


def _build_lipsync_plan(*, shots: list[_StoryboardShot], continuity_seed: int) -> dict[str, Any]:
    return {
        "engineSuggestion": "HeyGen / LivePortrait / Wav2Lip",
        "continuitySeed": continuity_seed,
        "shots": [
            {
                "shotNo": shot.shot_no,
                "needsLipsync": bool(shot.dialogue),
                "shotType": shot.shot_type,
                "dialogue": shot.dialogue,
            }
            for shot in shots
        ],
    }


def _shot_to_dict(shot: _StoryboardShot) -> dict[str, Any]:
    return {
        "index": shot.index,
        "shotNo": shot.shot_no,
        "shotType": shot.shot_type,
        "visualPrompt": shot.visual_prompt,
        "dialogue": shot.dialogue,
        "durationSeconds": shot.duration_seconds,
    }

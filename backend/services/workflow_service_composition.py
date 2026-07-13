"""Dependency composition for the workflow application facade."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.json_payloads import read_json_object
from backend.domain.workflow_storyboard_plan import parse_workflow_storyboard_markdown
from backend.models.workflow import BizStageVersion
from backend.services.workflow_finalization_service import WorkflowFinalizationService
from backend.services.workflow_generation_request_builder import WorkflowGenerationRequestBuilder
from backend.services.workflow_generation_result_parser import WorkflowGenerationResultParser
from backend.services.workflow_keyframe_generation_service import WorkflowKeyframeGenerationService
from backend.services.workflow_lifecycle_service import WorkflowLifecycleService
from backend.services.workflow_model_validator import WorkflowModelValidator
from backend.services.workflow_persistence_row_factory import WorkflowPersistenceRowFactory
from backend.services.workflow_query_service import WorkflowQueryService
from backend.services.workflow_stage_mutation_service import WorkflowStageMutationService
from backend.services.workflow_storyboard_generation_service import WorkflowStoryboardGenerationService
from backend.services.workflow_thumbnail_resolver import WorkflowThumbnailResolver
from backend.services.workflow_video_generation_service import WorkflowVideoGenerationService
from backend.services.workflow_video_refresh_service import WorkflowVideoRefreshService
from backend.services.workflow_view_mapper import WorkflowViewMapper
from backend.shared import trim


def workflow_storyboard_plan(
    version: BizStageVersion | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if version is None:
        return [], []
    output = read_json_object(version.output_summary_json)
    script = trim(output.get("scriptMarkdown") or output.get("previewText"))
    return parse_workflow_storyboard_markdown(script).to_view()


@dataclass(slots=True)
class WorkflowServiceCollaborators:
    model_validator: WorkflowModelValidator
    thumbnail_resolver: WorkflowThumbnailResolver
    view_mapper: WorkflowViewMapper
    generation_request_builder: WorkflowGenerationRequestBuilder
    generation_result_parser: WorkflowGenerationResultParser
    row_factory: WorkflowPersistenceRowFactory
    finalization_service: WorkflowFinalizationService
    video_refresh_service: WorkflowVideoRefreshService
    query_service: WorkflowQueryService
    video_generation_service: WorkflowVideoGenerationService
    keyframe_generation_service: WorkflowKeyframeGenerationService
    storyboard_generation_service: WorkflowStoryboardGenerationService
    stage_mutation_service: WorkflowStageMutationService
    lifecycle_service: WorkflowLifecycleService


def build_workflow_service_collaborators(
    db: AsyncSession,
    generation_service: Callable[[], Any],
    media_service: Any | None,
) -> WorkflowServiceCollaborators:
    model_validator = WorkflowModelValidator(generation_service)
    thumbnail_resolver = WorkflowThumbnailResolver(media_service)
    view_mapper = WorkflowViewMapper(workflow_storyboard_plan)
    request_builder = WorkflowGenerationRequestBuilder()
    result_parser = WorkflowGenerationResultParser()
    row_factory = WorkflowPersistenceRowFactory()
    thumbnail = thumbnail_resolver.resolve
    finalization = WorkflowFinalizationService(
        db,
        media_service=media_service,
        row_factory=row_factory,
        thumbnail_resolver=thumbnail,
    )
    video_refresh = WorkflowVideoRefreshService(
        db,
        generation_service=generation_service,
        result_parser=result_parser,
        row_factory=row_factory,
        thumbnail_resolver=thumbnail,
    )
    return WorkflowServiceCollaborators(
        model_validator=model_validator,
        thumbnail_resolver=thumbnail_resolver,
        view_mapper=view_mapper,
        generation_request_builder=request_builder,
        generation_result_parser=result_parser,
        row_factory=row_factory,
        finalization_service=finalization,
        video_refresh_service=video_refresh,
        query_service=WorkflowQueryService(
            db,
            view_mapper=view_mapper,
            video_refresher=video_refresh.refresh,
        ),
        video_generation_service=WorkflowVideoGenerationService(
            db,
            generation_service=generation_service,
            request_builder=request_builder,
            result_parser=result_parser,
            row_factory=row_factory,
            thumbnail_resolver=thumbnail,
        ),
        keyframe_generation_service=WorkflowKeyframeGenerationService(
            db,
            generation_service=generation_service,
            request_builder=request_builder,
            result_parser=result_parser,
            row_factory=row_factory,
            thumbnail_resolver=thumbnail,
        ),
        storyboard_generation_service=WorkflowStoryboardGenerationService(
            db,
            generation_service=generation_service,
            request_builder=request_builder,
            result_parser=result_parser,
            row_factory=row_factory,
        ),
        stage_mutation_service=WorkflowStageMutationService(db),
        lifecycle_service=WorkflowLifecycleService(
            db,
            model_validator=model_validator.validate,
        ),
    )

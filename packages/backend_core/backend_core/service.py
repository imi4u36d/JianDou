from __future__ import annotations

from datetime import datetime
import json
import threading

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .media import probe_media, render_output
from .models import SourceAsset, Task, TaskOutput
from .planner import PlannerChain, PlannerContext
from .schemas import (
    ClipPlan,
    CreateTaskRequest,
    MediaProbe,
    TaskDetail,
    TaskListItem,
    TaskOutput as TaskOutputSchema,
    TaskSpec,
    UploadResponse,
)
from .storage import MediaStorage
from .utils import clamp, new_id, truncate_text, utcnow


def _iso(value: datetime | None) -> str:
    if value is None:
        return utcnow().isoformat()
    return value.isoformat()


def _task_status(value: str) -> str:
    return value


class TaskService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        storage: MediaStorage,
        planner: PlannerChain,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.storage = storage
        self.planner = planner
        self.worker = None

    def set_worker(self, worker) -> None:
        self.worker = worker

    def session(self) -> Session:
        return self.session_factory()

    def upload_video(self, file_obj, original_name: str, mime_type: str | None = None) -> UploadResponse:
        stored = self.storage.save_upload(file_obj, original_name, mime_type)
        with self.session() as session:
            asset = SourceAsset(
                id=stored.asset_id,
                original_file_name=stored.original_file_name,
                stored_file_name=stored.stored_file_name,
                storage_path=stored.relative_path,
                mime_type=mime_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
            )
            session.add(asset)
            session.commit()
        return UploadResponse(
            assetId=stored.asset_id,
            fileName=stored.original_file_name,
            fileUrl=stored.public_url,
            sizeBytes=stored.size_bytes,
        )

    def create_task(self, payload: CreateTaskRequest) -> TaskDetail:
        if payload.minDurationSeconds > payload.maxDurationSeconds:
            raise ValueError("minDurationSeconds must be less than or equal to maxDurationSeconds")
        if payload.outputCount > self.settings.pipeline.max_output_count:
            raise ValueError(f"outputCount exceeds limit {self.settings.pipeline.max_output_count}")

        with self.session() as session:
            asset = session.get(SourceAsset, payload.sourceAssetId)
            if asset is None:
                raise LookupError("source asset not found")

            task = Task(
                id=new_id("task"),
                title=payload.title,
                source_asset_id=payload.sourceAssetId,
                source_file_name=payload.sourceFileName or asset.original_file_name,
                platform=payload.platform,
                aspect_ratio=payload.aspectRatio,
                min_duration_seconds=payload.minDurationSeconds,
                max_duration_seconds=payload.maxDurationSeconds,
                output_count=payload.outputCount,
                intro_template=payload.introTemplate,
                outro_template=payload.outroTemplate,
                creative_prompt=payload.creativePrompt,
                model_provider=self.settings.model.provider,
                execution_mode=self.settings.app.execution_mode,
                status="PENDING",
                progress=0,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

        self.dispatch_task(task.id)
        return self.get_task_detail(task.id)

    def list_tasks(self) -> list[TaskListItem]:
        with self.session() as session:
            rows = session.scalars(select(Task).order_by(Task.created_at.desc())).all()
            return [self._task_to_list_item(row) for row in rows]

    def get_task_detail(self, task_id: str) -> TaskDetail:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            return self._task_to_detail(task)

    def retry_task(self, task_id: str) -> TaskDetail:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError("task not found")
            self._delete_outputs(session, task)
            task.status = "PENDING"
            task.progress = 0
            task.error_message = None
            task.plan_json = None
            task.started_at = None
            task.finished_at = None
            task.retry_count = (task.retry_count or 0) + 1
            session.commit()

        self.dispatch_task(task_id)
        return self.get_task_detail(task_id)

    def list_pending_task_ids(self, limit: int = 10) -> list[str]:
        with self.session() as session:
            rows = session.scalars(
                select(Task.id)
                .where(Task.status == "PENDING")
                .order_by(Task.created_at.asc())
                .limit(limit)
            ).all()
            return list(rows)

    def dispatch_task(self, task_id: str) -> None:
        if self.settings.using_inline_execution or self.worker is None or self.worker.job_queue is None:
            thread = threading.Thread(target=self.process_task, args=(task_id,), daemon=True)
            thread.start()
            return
        try:
            self.worker.job_queue.enqueue(task_id)
        except Exception:
            thread = threading.Thread(target=self.process_task, args=(task_id,), daemon=True)
            thread.start()

    def process_task(self, task_id: str) -> None:
        if not self._claim_task(task_id):
            return

        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                return
            asset = session.get(SourceAsset, task.source_asset_id)
            if asset is None:
                task.status = "FAILED"
                task.error_message = "source asset missing"
                task.finished_at = utcnow()
                session.commit()
                return
            source_asset_id = task.source_asset_id
            source_path = self.storage.root / asset.storage_path

        try:
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "ANALYZING"
                task.progress = 10
                task.started_at = task.started_at or utcnow()
                session.commit()

            probe = probe_media(source_path)
            with self.session() as session:
                asset = session.get(SourceAsset, source_asset_id)
                if asset is not None:
                    asset.duration_seconds = probe.durationSeconds
                    asset.width = probe.width
                    asset.height = probe.height
                    asset.has_audio = probe.hasAudio
                    session.commit()

            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "PLANNING"
                task.progress = 25
                session.commit()

                context = PlannerContext(
                    task=TaskSpec(
                        title=task.title,
                        platform=task.platform,
                        aspectRatio=task.aspect_ratio,
                        minDurationSeconds=task.min_duration_seconds,
                        maxDurationSeconds=task.max_duration_seconds,
                        outputCount=task.output_count,
                        introTemplate=task.intro_template,
                        outroTemplate=task.outro_template,
                        creativePrompt=task.creative_prompt,
                    ),
                    source=probe,
                )
                clips = self.planner.plan(context)
                if not clips:
                    clips = self._fallback_clips(task, probe)
                else:
                    clips = self._sanitize_clips(task, probe, clips)
                    if not clips:
                        clips = self._fallback_clips(task, probe)
                task.plan_json = json.dumps([clip.model_dump() for clip in clips], ensure_ascii=False)
                task.progress = 35
                session.commit()

            self._render_outputs(
                task_id=task_id,
                source_path=source_path,
                probe=probe,
                clips=clips,
            )

            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    return
                task.status = "COMPLETED"
                task.progress = 100
                task.finished_at = utcnow()
                session.commit()
        except Exception as exc:
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is not None:
                    task.status = "FAILED"
                    task.progress = min(99, task.progress or 0)
                    task.error_message = truncate_text(str(exc), 1000)
                    task.finished_at = utcnow()
                    session.commit()

    def _claim_task(self, task_id: str) -> bool:
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None or task.status not in {"PENDING", "FAILED"}:
                return False
            task.status = "ANALYZING"
            task.progress = max(task.progress or 0, 1)
            task.started_at = task.started_at or utcnow()
            session.commit()
            return True

    def _fallback_clips(self, task: Task, probe: MediaProbe) -> list[ClipPlan]:
        context = PlannerContext(
            task=TaskSpec(
                title=task.title,
                platform=task.platform,
                aspectRatio=task.aspect_ratio,
                minDurationSeconds=task.min_duration_seconds,
                maxDurationSeconds=task.max_duration_seconds,
                outputCount=task.output_count,
                introTemplate=task.intro_template,
                outroTemplate=task.outro_template,
                creativePrompt=task.creative_prompt,
            ),
            source=probe,
        )
        from .planner import HeuristicPlanner

        return HeuristicPlanner(self.settings).plan(context)

    def _sanitize_clips(self, task: Task, probe: MediaProbe, clips: list[ClipPlan]) -> list[ClipPlan]:
        normalized: list[ClipPlan] = []
        source_duration = max(1.0, probe.durationSeconds)
        minimum = float(task.min_duration_seconds)
        maximum = float(task.max_duration_seconds)
        for index, clip in enumerate(clips[: task.output_count], start=1):
            start_seconds = clamp(float(clip.startSeconds), 0.0, max(0.0, source_duration - 0.5))
            requested_end = float(clip.endSeconds)
            if requested_end <= start_seconds:
                requested_end = start_seconds + max(minimum, 1.0)
            end_seconds = clamp(requested_end, start_seconds + 0.5, source_duration)
            duration_seconds = end_seconds - start_seconds
            if duration_seconds < minimum:
                end_seconds = clamp(start_seconds + minimum, start_seconds + 0.5, source_duration)
                duration_seconds = max(1.0, end_seconds - start_seconds)
            duration_seconds = clamp(duration_seconds, 1.0, maximum)
            end_seconds = min(source_duration, start_seconds + duration_seconds)
            if end_seconds <= start_seconds:
                continue
            normalized.append(
                ClipPlan(
                    clipIndex=index,
                    title=(clip.title or f"素材 {index}")[:255],
                    reason=(clip.reason or "由模型规划生成")[:1000],
                    startSeconds=round(start_seconds, 3),
                    endSeconds=round(end_seconds, 3),
                    durationSeconds=round(end_seconds - start_seconds, 3),
                )
            )
        return normalized

    def _render_outputs(
        self,
        task_id: str,
        source_path,
        probe: MediaProbe,
        clips: list[ClipPlan],
    ) -> None:
        total = max(1, len(clips))
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is not None:
                task.status = "RENDERING"
                task.progress = 40
                session.commit()
        with self.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                return
            aspect_ratio = task.aspect_ratio
            intro_template = task.intro_template
            outro_template = task.outro_template
        for index, clip in enumerate(clips, start=1):
            output_path = self.storage.task_output_path(task_id, clip.clipIndex)
            render_output(
                source_path=source_path,
                output_path=output_path,
                start_seconds=clip.startSeconds,
                end_seconds=clip.endSeconds,
                aspect_ratio=aspect_ratio,
                intro_template=intro_template,
                outro_template=outro_template,
                has_audio=probe.hasAudio,
            )
            with self.session() as session:
                task = session.get(Task, task_id)
                if task is None:
                    continue
                session.add(
                    TaskOutput(
                        id=new_id("output"),
                        task_id=task_id,
                        clip_index=clip.clipIndex,
                        title=clip.title,
                        reason=clip.reason,
                        start_seconds=clip.startSeconds,
                        end_seconds=clip.endSeconds,
                        duration_seconds=clip.durationSeconds,
                        preview_path=output_path.relative_to(self.storage.root).as_posix(),
                        download_path=output_path.relative_to(self.storage.root).as_posix(),
                    )
                )
                task.progress = min(95, 35 + int(60 * (index / total)))
                session.commit()

    def _delete_outputs(self, session: Session, task: Task) -> None:
        self.storage.remove_output_bundle(task.id)
        session.execute(delete(TaskOutput).where(TaskOutput.task_id == task.id))
        session.flush()

    def _task_to_list_item(self, task: Task) -> TaskListItem:
        return TaskListItem(
            id=task.id,
            title=task.title,
            status=task.status,
            platform=task.platform,
            progress=task.progress,
            outputCount=task.output_count,
            createdAt=_iso(task.created_at),
            updatedAt=_iso(task.updated_at),
        )

    def _task_to_detail(self, task: Task) -> TaskDetail:
        outputs: list[TaskOutputSchema] = []
        for output in sorted(task.outputs, key=lambda item: item.clip_index):
            relative = output.preview_path
            outputs.append(
                TaskOutputSchema(
                    id=output.id,
                    clipIndex=output.clip_index,
                    title=output.title,
                    reason=output.reason,
                    startSeconds=output.start_seconds,
                    endSeconds=output.end_seconds,
                    durationSeconds=output.duration_seconds,
                    previewUrl=self.storage.build_public_url(relative),
                    downloadUrl=self.storage.build_public_url(output.download_path),
                )
            )
        return TaskDetail(
            id=task.id,
            title=task.title,
            status=task.status,
            platform=task.platform,
            progress=task.progress,
            outputCount=task.output_count,
            createdAt=_iso(task.created_at),
            updatedAt=_iso(task.updated_at),
            sourceFileName=task.source_file_name,
            aspectRatio=task.aspect_ratio,
            minDurationSeconds=task.min_duration_seconds,
            maxDurationSeconds=task.max_duration_seconds,
            introTemplate=task.intro_template,
            outroTemplate=task.outro_template,
            creativePrompt=task.creative_prompt,
            errorMessage=task.error_message,
            outputs=outputs,
        )

"""Stub service implementations used for testing and graceful degradation.

These provide no-op or minimal implementations of external service
interfaces so that the worker pipeline can function even when certain
optional services are not configured.
"""

from __future__ import annotations

from typing import Any


class GenerationApplicationServiceStub:
    """Stub for GenerationApplicationService. Replace with real client."""

    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"message": "not yet implemented", "id": "", "status": "pending", "result": {}}

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return {"id": run_id, "status": "completed", "result": {}}


class LocalMediaArtifactServiceStub:
    """Stub for LocalMediaArtifactService."""

    class StoredArtifact:
        def __init__(
            self,
            public_url: str = "",
            file_name: str = "",
            absolute_path: str = "",
            size_bytes: int = 0,
        ) -> None:
            self._public_url = public_url
            self._file_name = file_name
            self._absolute_path = absolute_path
            self._size_bytes = size_bytes

        def public_url(self) -> str:
            return self._public_url

        def file_name(self) -> str:
            return self._file_name

        def absolute_path(self) -> str:
            return self._absolute_path

        def size_bytes(self) -> int:
            return self._size_bytes

    def materialize_artifact(self, source_url: str, relative_dir: str, target_file_name: str) -> StoredArtifact:  # noqa: ARG002
        return self.StoredArtifact()

    def copy_artifact(self, source_url: str, relative_dir: str, target_file_name: str) -> StoredArtifact:  # noqa: ARG002
        return self.StoredArtifact()

    def concat_videos(self, relative_dir: str, output_file_name: str, segment_urls: list[str]) -> StoredArtifact:  # noqa: ARG002
        return self.StoredArtifact()

    def build_externally_accessible_url(self, local_path: str) -> str:
        return local_path

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        return public_url

    def ensure_media_thumbnail(
        self,
        media_type: str,
        public_url: str,
        candidate_image_urls: list[str],
        max_width: int,
    ) -> str:  # noqa: ARG002
        return public_url

    def resolve_absolute_path(self, file_url: str) -> str:
        return file_url


class TaskStoryboardPlannerStub:
    """Stub for TaskStoryboardPlanner."""

    class StoryboardShotPlan:
        def __init__(
            self,
            *,
            sequential_index: int = 1,
            shot_label: str = "",
            scene: str = "",
            video_prompt: str = "",
            image_prompt: str = "",
            first_frame_prompt: str = "",
            last_frame_prompt: str = "",
            motion: str = "",
            camera_movement: str = "",
            duration_hint: str = "",
        ) -> None:
            self._sequential_index = sequential_index
            self._shot_label = shot_label
            self._scene = scene
            self._video_prompt = video_prompt
            self._image_prompt = image_prompt
            self._first_frame_prompt = first_frame_prompt
            self._last_frame_prompt = last_frame_prompt
            self._motion = motion
            self._camera_movement = camera_movement
            self._duration_hint = duration_hint

        def sequential_index(self) -> int:
            return self._sequential_index

        def shot_label(self) -> str:
            return self._shot_label

        def scene(self) -> str:
            return self._scene

        def video_prompt(self) -> str:
            return self._video_prompt

        def image_prompt(self) -> str:
            return self._image_prompt

        def first_frame_prompt(self) -> str:
            return self._first_frame_prompt

        def last_frame_prompt(self) -> str:
            return self._last_frame_prompt

        def motion(self) -> str:
            return self._motion

        def camera_movement(self) -> str:
            return self._camera_movement

        def duration_hint(self) -> str:
            return self._duration_hint

    def build_storyboard_shot_plans(
        self,
        task,
        storyboard_markdown: str,
    ) -> list[StoryboardShotPlan]:  # noqa: ARG002
        return []

    def extract_character_definitions(
        self,
        storyboard_markdown: str,
    ) -> list[Any]:  # noqa: ARG002
        return []

    def resolve_requested_output_count(
        self,
        task,
        storyboard_clip_count: int,
    ) -> int:
        return storyboard_clip_count

    def extract_storyboard_shot_duration_ranges(
        self,
        storyboard_markdown: str,
    ) -> list[list[int]]:  # noqa: ARG002
        return []

    def build_clip_duration_plan(
        self,
        task,
        duration_seconds: int,
        clip_count: int,
        storyboard_markdown: str,
    ) -> list[list[int]]:  # noqa: ARG002
        return [[duration_seconds, duration_seconds, duration_seconds]] * clip_count

    def normalize_clip_duration_plan(
        self,
        video_model: str,
        clip_duration_plan: list[list[int]],
    ) -> list[list[int]]:  # noqa: ARG002
        return clip_duration_plan

    def request_snapshot_output_count(self, task) -> int:  # noqa: ARG002
        return 0

    def build_clip_duration_plan_context(
        self,
        clip_duration_plan: list[list[int]],
        duration_ranges: list[list[int]],
    ) -> list[dict[str, Any]]:  # noqa: ARG002
        return []

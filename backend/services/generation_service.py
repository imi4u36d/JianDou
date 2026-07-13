"""Generation application service and compatibility exports."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from backend.domain.generation_run import GenerationRunKinds, GenerationRunStatuses
from backend.infrastructure.generation_run_store import LocalGenerationRunStore
from backend.services.generation_catalog_service import GenerationCatalogService
from backend.services.generation_run_factory import (
    GenerationNotImplementedException,
    GenerationProviderException,
    GenerationRunFactory,
    GenerationRunNotFoundException,
    UnsupportedGenerationKindException,
)
from backend.services.generation_run_support import GenerationRunSupport
from backend.services.model_config_service import ModelRuntimePropertiesResolver


class DefaultGenerationApplicationService:
    """Main generation service combining catalog, factory, and run store.

    Mirrors the Java DefaultGenerationApplicationService.
    """

    def __init__(
        self,
        generation_run_store: LocalGenerationRunStore | None = None,
        catalog_service: GenerationCatalogService | None = None,
        generation_run_factory: GenerationRunFactory | None = None,
        support: GenerationRunSupport | None = None,
        config_resolver: ModelRuntimePropertiesResolver | None = None,
    ) -> None:
        self._store = generation_run_store or LocalGenerationRunStore()
        self._catalog_service = catalog_service or GenerationCatalogService()
        self._factory = generation_run_factory or GenerationRunFactory(
            support or GenerationRunSupport(),
            config_resolver=config_resolver,
        )
        self._support = support or GenerationRunSupport()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def catalog(self) -> dict[str, Any]:
        """Return the available generation catalog."""
        return self._catalog_service.catalog()

    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Synchronously create a generation run."""
        run_id = f"run_{uuid.uuid4().hex}"
        kind = str(request.get("kind", GenerationRunKinds.PROBE))
        return await self._create_run_by_kind_and_persist(run_id, kind, request)

    async def create_async_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create an async generation run (returns immediately with ACCEPTED status)."""
        run_id = f"run_{uuid.uuid4().hex}"
        kind = str(request.get("kind", GenerationRunKinds.PROBE))

        # Probe runs are always synchronous
        if kind.lower() == GenerationRunKinds.PROBE:
            return await self._create_run_by_kind_and_persist(run_id, kind, request)

        self._validate_supported_kind(kind)

        accepted = self._accepted_run(run_id, kind, request)
        self._runs_cache[run_id] = accepted
        await self._store.save(run_id, accepted)

        # Fire and forget the background execution
        asyncio.create_task(self._execute_async_run(run_id, kind, request))

        return accepted

    async def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        """List recent generation runs."""
        return await self._store.list(limit)

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a single generation run by ID, refreshing if it's a video run."""
        run = self._runs_cache.get(run_id)
        if run is None:
            run = await self._store.get(run_id)
        if run is None:
            raise GenerationRunNotFoundException(run_id)

        # Refresh video runs
        refreshed = await self._factory.refresh_video_run(dict(run))
        self._runs_cache[run_id] = refreshed
        await self._store.save(run_id, refreshed)
        return refreshed

    async def usage(self) -> dict[str, Any]:
        """Return usage statistics (stub)."""
        items: list[dict[str, Any]] = []
        for model in [
            {"value": "gpt-5.5", "label": "GPT-5.5", "provider": "openai"},
        ]:
            items.append(
                {
                    "model": str(model.get("value", "")).strip(),
                    "label": str(model.get("label", model.get("value", ""))).strip(),
                    "used": 0,
                    "unit": "count",
                    "remaining": 0,
                    "remainingUnit": "count",
                    "provider": str(model.get("provider", "")).strip(),
                    "source": "python-default",
                }
            )
        return {
            "items": items,
            "generatedAt": self._support.now_iso(),
            "updatedAt": self._support.now_iso(),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    _runs_cache: dict[str, dict[str, Any]] = {}

    async def _create_run_by_kind_and_persist(self, run_id: str, kind: str, request: dict[str, Any]) -> dict[str, Any]:
        run = await self._create_run_by_kind(run_id, kind, request)
        self._runs_cache[run_id] = run
        await self._store.save(run_id, run)
        return run

    async def _create_run_by_kind(self, run_id: str, kind: str, request: dict[str, Any]) -> dict[str, Any]:
        lower_kind = kind.lower()
        if lower_kind == GenerationRunKinds.PROBE:
            return await self._factory.create_probe_run(run_id, request)
        elif lower_kind == GenerationRunKinds.SCRIPT:
            return await self._factory.create_script_run(run_id, request)
        elif lower_kind == GenerationRunKinds.SCRIPT_ADJUST:
            return await self._factory.create_script_adjust_run(run_id, request)
        elif lower_kind == GenerationRunKinds.IMAGE:
            return await self._factory.create_image_run(run_id, request)
        elif lower_kind == GenerationRunKinds.VIDEO:
            return await self._factory.create_video_run(run_id, request)
        else:
            raise UnsupportedGenerationKindException(kind)

    @staticmethod
    def _validate_supported_kind(kind: str) -> None:
        lower_kind = kind.lower()
        supported = {
            GenerationRunKinds.PROBE,
            GenerationRunKinds.SCRIPT,
            GenerationRunKinds.SCRIPT_ADJUST,
            GenerationRunKinds.IMAGE,
            GenerationRunKinds.VIDEO,
        }
        if lower_kind not in supported:
            raise UnsupportedGenerationKindException(kind)

    def _accepted_run(self, run_id: str, kind: str, request: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "runId": run_id,
            "kind": kind,
            "callChain": [self._support.call_log("generation", "run.accepted", "running", "", {"kind": kind})],
            "metadata": {"async": True},
        }
        result_key = self._result_key(kind)
        return self._support.run_envelope(run_id, kind, request, result, result_key, GenerationRunStatuses.ACCEPTED)

    @staticmethod
    def _result_key(kind: str) -> str:
        lower_kind = kind.lower()
        if lower_kind == GenerationRunKinds.PROBE:
            return "resultProbe"
        if lower_kind in (GenerationRunKinds.SCRIPT, GenerationRunKinds.SCRIPT_ADJUST):
            return "resultScript"
        if lower_kind == GenerationRunKinds.IMAGE:
            return "resultImage"
        if lower_kind == GenerationRunKinds.VIDEO:
            return "resultVideo"
        return "result"

    async def _execute_async_run(self, run_id: str, kind: str, request: dict[str, Any]) -> None:
        try:
            run = await self._create_run_by_kind(run_id, kind, request)
            self._runs_cache[run_id] = run
            await self._store.save(run_id, run)
        except Exception as ex:
            failed = self._failed_run(run_id, kind, request, ex)
            self._runs_cache[run_id] = failed
            await self._store.save(run_id, failed)

    def _failed_run(self, run_id: str, kind: str, request: dict[str, Any], ex: Exception) -> dict[str, Any]:
        error_msg = str(ex) if str(ex) else ex.__class__.__name__
        result: dict[str, Any] = {
            "runId": run_id,
            "kind": kind,
            "error": error_msg,
            "callChain": [
                self._support.call_log(
                    "generation",
                    "run.failed",
                    "error",
                    "",
                    {
                        "error": error_msg,
                    },
                )
            ],
            "metadata": {"async": True},
        }
        result_key = self._result_key(kind)
        return self._support.run_envelope(run_id, kind, request, result, result_key, GenerationRunStatuses.FAILED)

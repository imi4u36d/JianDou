"""Application services — business-logic orchestration layer.

Each module encapsulates a cohesive set of business operations,
delegating persistence to the infrastructure layer and using
domain objects for core logic.

Submodules
----------
auth_rate_limiter                In-process auth-rate limiter.
auth_service                     Authentication business logic.
credit_service                   Credit accounting and consumption.
generation_artifacts             Artifact file I/O for generation runs.
generation_catalog_service      Generation-catalogue metadata.
generation_payloads             Payload builders for generation requests.
generation_request_values       Nested-value accessors for generation requests.
generation_service              Generation-run orchestration and factory.
material_asset_service          Material-asset business logic.
material_asset_thumbnail_service  Thumbnail generation for material assets.
media_service                   Media-file processing service.
model_config_service            Model-configuration resolution and management.
model_config_snapshot           Snapshots of model configuration at a point in time.
model_config_values             Value types for model configuration.
model_invocation                AI-model provider transport and invocation.
model_response_parsing          Parsers for AI-model responses.
provider_payload_sanitizer      Sanitises provider payloads before logging.
structured_application_logger   Structured JSON application-logging service.
stubs                           Stub implementations for testing/graceful degradation.
task_application_service        Task application-service facade.
task_artifact_assembler         Assembles task artifacts from generation results.
task_command_service            Task command-side service.
task_diagnosis_service          Task-diagnosis and queue-coordination service.
task_execution_coordinator      Coordinates task execution across worker instances.
task_execution_runtime_support  Runtime-support utilities for task execution.
task_query_service              Task query-side service.
task_render_stage_payloads      Payload builders for render-stage requests.
task_worker_render_stage_service  Render-stage pipeline logic.
task_worker_runner              Worker-runner lifecycle (poll loop, maintenance).
task_worker_service             Worker pipeline handler (analysis → render → join).
task_worker_status_stage_service  Status-stage pipeline logic.
task_worker_view_mapper         Maps task-worker models to view DTOs.
workflow_generation_request_builder  Builds generation requests from workflow state.
workflow_generation_result_parser   Parses generation results into workflow state.
workflow_persistence_row_factory    Creates persistence-row objects for workflow mutations.
workflow_service                Multi-stage creative workflow orchestration.
workflow_stage_generation_strategy  Per-stage generation-strategy dispatch.
workflow_view_mapper            Maps workflow domain to view DTOs.
"""

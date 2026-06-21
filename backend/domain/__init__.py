"""Domain model — core business entities, value objects, and domain services.

Submodules
----------
enums               Status and type enumerations used across the domain.
generation_run      Generation-run lifecycle model.
json_payloads       JSON serialisation helpers for domain objects.
media_artifacts     Media-artifact domain model.
media_result        Media-result value object.
request_snapshot    Snapshot of a generation request at a point in time.
task_aggregate      Task aggregate root for the task bounded context.
task_artifact_naming  Naming conventions for task artifacts.
task_attempt_snapshot  Snapshot of a single task execution attempt.
task_monitoring     Task monitoring and health-check domain logic.
task_queue_fairness  Fair-queueing algorithms for task scheduling.
task_record         Core task record entity.
task_result_types   Task result type definitions.
task_resume         Task-resume decision logic.
task_stage_run_snapshot  Snapshot of a stage within a task run.
task_status         Task-status state machine.
task_storyboard_planner  Storyboard markdown → shot-plan translation.
user_credit_account_initializer  New-user credit-account initialisation.
user_queue_stats    Per-user queue statistics.
video_run_monitor   Video-generation run monitoring domain logic.
workflow_storyboard_plan  Storyboard-plan value object for workflows.
"""

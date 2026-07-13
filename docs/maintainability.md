# Maintainability Guide

JianDou is optimized incrementally. Large modules are reduced behind stable interfaces, with tests added before the next boundary is moved. File size is a signal for review, not a reason to split unrelated code arbitrarily.

## Module boundaries

### Python backend

- Routers translate HTTP requests and responses; they do not assemble ORM rows or provider payloads.
- Services orchestrate use cases. Pure parsing, normalization, state transitions, and presentation mapping belong in focused domain or helper modules.
- Infrastructure modules own SQLAlchemy queries and persistence mapping.
- Existing public imports must remain compatible during extraction. The old module may re-export a moved class until callers are migrated.
- Prefer collaborators under 500 lines and orchestration methods under 80 lines. A file over 1,000 lines requires a documented follow-up boundary.

### Vue frontend

- Views coordinate routes, page-level state, and feature composition.
- Reusable state and side effects belong in composables.
- Pure labels, formatting, and view-model transformations belong in feature presenter modules with unit tests.
- Repeated or independently interactive template regions belong in child components.
- Large scoped styles may move to a view-owned CSS file first; subsequent component extraction should move the related styles with the component.
- New Vue components should normally stay below 800 lines. Existing larger views use ratcheted budgets and must not grow while they are being reduced.

## Safe extraction workflow

1. Identify one cohesive responsibility with a small input/output surface.
2. Add or identify focused regression tests.
3. Move the implementation without changing its public behavior.
4. Re-export old public names when compatibility is required.
5. Run focused tests, then the full backend and frontend quality gates.
6. Lower the source-size budget after the extraction.

## Current ratchet targets

The automated source-size policy prevents the modules improved so far from growing back to their previous size. Budgets are ceilings, not desired sizes.

- `admin.py`: 410 lines
- `admin_task_routes.py`: 210 lines
- `workflows.py`: 380 lines
- `workflow_stage_routes.py`: 230 lines
- `workflow_route_support.py`: 70 lines
- `task_storyboard_planner.py`: 120 lines
- `task_storyboard_shots.py`: 380 lines
- `task_storyboard_characters.py`: 310 lines
- `task_storyboard_duration.py`: 250 lines
- `generation_service.py`: 240 lines
- `credit_service.py`: 220 lines
- `credit_ledger.py`: 330 lines
- `credit_rule_catalog.py`: 140 lines
- `credit_presenters.py`: 90 lines
- `credit_user_directory.py`: 100 lines
- `auth_service.py`: 160 lines
- `auth_user_service.py`: 250 lines
- `auth_values.py`: 80 lines
- `auth_presenters.py`: 40 lines
- `auth_invite_service.py`: 230 lines
- `task_command_service.py`: 300 lines
- `task_command_inputs.py`: 140 lines
- `task_command_mutations.py`: 50 lines
- `task_creation_service.py`: 250 lines
- `generation_run_factory.py`: 370 lines
- `generation_provider_registry.py`: 90 lines
- `generation_profile_presenters.py`: 110 lines
- `generation_text_run_service.py`: 150 lines
- `generation_script_run_service.py`: 260 lines
- `generation_text_run_values.py`: 70 lines
- `generation_image_run_service.py`: 230 lines
- `generation_video_run_service.py`: 330 lines
- `generation_video_run_refresh.py`: 300 lines
- `task_execution_coordinator.py`: 320 lines
- `task_attempt_mutation_service.py`: 120 lines
- `task_transition_service.py`: 120 lines
- `task_queue_lifecycle.py`: 130 lines
- `task_attempt_lifecycle.py`: 180 lines
- `task_execution_record_factory.py`: 120 lines
- `task_execution_mutation_recorder.py`: 180 lines
- `task_worker_registry.py`: 90 lines
- `task_query_service.py`: 330 lines
- `task_query_cache.py`: 80 lines
- `task_query_policy.py`: 90 lines
- `task_admin_query_service.py`: 190 lines
- `task_query_presenters.py`: 140 lines
- `task_diagnosis_service.py`: 100 lines
- `task_diagnosis.py`: 290 lines
- `task_queue_coordinator.py`: 50 lines
- `task_request_snapshot_factory.py`: 180 lines
- `task_execution_runtime_support.py`: 300 lines
- `task_generation_request_factory.py`: 330 lines
- `task_execution_prompt_support.py`: 100 lines
- `task_reference_image_support.py`: 70 lines
- `task_state_transition.py`: 200 lines
- `task_stale_claim_recovery.py`: 150 lines
- `task_worker_service.py`: 340 lines
- `task_storyboard_preparation_service.py`: 270 lines
- `task_worker_pipeline_composition.py`: 110 lines
- `task_worker_pipeline_context.py`: 110 lines
- `task_worker_render_stage_service.py`: 360 lines
- `task_worker_status_stage_service.py`: 300 lines
- `task_worker_record_factory.py`: 230 lines
- `task_render_stage_context.py`: 160 lines
- `task_render_stage_payloads.py`: 240 lines
- `task_render_stage_contracts.py`: 200 lines
- `task_frame_render_service.py`: 180 lines
- `task_character_sheet_render_service.py`: 160 lines
- `task_render_reference_selector.py`: 130 lines
- `task_video_stage_service.py`: 370 lines
- `task_video_clip_result_recorder.py`: 170 lines
- `task_video_stage_context.py`: 320 lines
- `task_video_run_service.py`: 90 lines
- `task_video_join_service.py`: 80 lines
- `task_workspace_image_service.py`: 220 lines
- `task_storyboard_planner_adapter.py`: 80 lines
- `join_output_service.py`: 50 lines
- `task_artifact_assembler.py`: 320 lines
- `task_image_material_assembler.py`: 250 lines
- `task_artifact_storage.py`: 130 lines
- `task_artifact_support.py`: 120 lines
- `task_material_factory.py`: 130 lines
- `task_result_assembler.py`: 180 lines
- `model_invocation.py`: 60 lines
- `model_invocation_config.py`: 140 lines
- `model_config_path_locator.py`: 280 lines
- `model_invocation_text.py`: 150 lines
- `model_invocation_text_contracts.py`: 90 lines
- `model_invocation_text_strategies.py`: 80 lines
- `model_invocation_text_transport.py`: 320 lines
- `model_invocation_image.py`: 310 lines
- `model_invocation_image_contracts.py`: 90 lines
- `model_invocation_image_transport.py`: 240 lines
- `model_invocation_video.py`: 40 lines
- `model_invocation_video_seedance.py`: 170 lines
- `model_invocation_video_agnes.py`: 150 lines
- `model_invocation_video_composite.py`: 60 lines
- `model_invocation_video_contracts.py`: 90 lines
- `model_invocation_video_transport.py`: 210 lines
- `model_config_service.py`: 70 lines
- `model_config_admin.py`: 320 lines
- `model_config_user.py`: 190 lines
- `model_config_user_catalog.py`: 250 lines
- `model_config_runtime.py`: 220 lines
- `model_config_runtime_text.py`: 180 lines
- `model_config_runtime_media.py`: 210 lines
- `model_config_runtime_snapshot.py`: 150 lines
- `model_config_runtime_credentials.py`: 180 lines
- `model_config_contracts.py`: 100 lines
- `model_config_response_support.py`: 200 lines
- `model_config_credentials.py`: 360 lines
- `workflow_service.py`: 160 lines
- `workflow_lifecycle_commands.py`: 210 lines
- `workflow_stage_commands.py`: 220 lines
- `workflow_service_composition.py`: 150 lines
- `workflow_model_validator.py`: 80 lines
- `workflow_thumbnail_resolver.py`: 60 lines
- `workflow_auto_pilot.py`: 360 lines
- `workflow_auto_pilot_executor.py`: 340 lines
- `workflow_auto_pilot_planner.py`: 170 lines
- `workflow_lifecycle_service.py`: 370 lines
- `workflow_query_service.py`: 220 lines
- `workflow_keyframe_generation_service.py`: 330 lines
- `workflow_keyframe_version_store.py`: 170 lines
- `workflow_keyframe_persistence.py`: 280 lines
- `workflow_keyframe_support.py`: 100 lines
- `workflow_video_generation_service.py`: 320 lines
- `workflow_storyboard_generation_service.py`: 130 lines
- `workflow_stage_mutation_service.py`: 270 lines
- `workflow_stage_mutation_store.py`: 130 lines
- `workflow_stage_mutation_policy.py`: 80 lines
- `media_service.py`: 310 lines
- `media_artifacts.py`: 70 lines
- `media_prompt_cards.py`: 150 lines
- `media_artifact_storage.py`: 150 lines
- `media_thumbnails.py`: 280 lines
- `media_video_operations.py`: 190 lines
- `material_asset_service.py`: 220 lines
- `material_asset_mapping.py`: 180 lines
- `StageWorkflowView.vue`: 480 lines
- `useWorkflowPreviewInteractions.ts`: 140 lines
- `useWorkflowStageReadiness.ts`: 90 lines
- `AppSelect.vue`: 150 lines
- `useAppSelectInteraction.ts`: 230 lines
- `app-select.ts`: 30 lines
- `AppPreviewDialog.vue`: 160 lines
- `useAppPreviewDialog.ts`: 150 lines
- `app-preview-dialog.css`: 320 lines
- `AuthDialog.vue`: 150 lines
- `useAuthDialog.ts`: 130 lines
- `auth-dialog.css`: 290 lines
- `AuthStandaloneForm.vue`: 100 lines
- `auth-standalone-form.css`: 130 lines
- `LoginView.vue`: 70 lines
- `ActivateInviteView.vue`: 70 lines
- `auth/redirect.ts`: 20 lines
- `api/generation.ts`: 140 lines
- `api/generation-normalizers.ts`: 220 lines
- `app-select.css`: 400 lines
- `useStageWorkflowDetailLoader.ts`: 180 lines
- `useStageWorkflowInteractions.ts`: 90 lines
- `useStageWorkflowManagementCommands.ts`: 170 lines
- `types/index.ts`: 30 lines
- `types/admin.ts`: 200 lines
- `types/auth.ts`: 40 lines
- `types/credits.ts`: 60 lines
- `types/health.ts`: 80 lines
- `types/material.ts`: 30 lines
- `types/public-share.ts`: 70 lines
- `types/showcase.ts`: 60 lines
- `types/generation.ts`: 20 lines
- `types/generation-catalog.ts`: 90 lines
- `types/generation-media.ts`: 80 lines
- `types/generation-model-config.ts`: 90 lines
- `types/generation-task.ts`: 100 lines
- `types/task.ts`: 20 lines
- `types/task-assets.ts`: 40 lines
- `types/task-core.ts`: 70 lines
- `types/task-detail.ts`: 50 lines
- `types/task-execution.ts`: 80 lines
- `types/workflow.ts`: 20 lines
- `types/workflow-core.ts`: 130 lines
- `types/workflow-material.ts`: 120 lines
- `types/workflow-stage.ts`: 150 lines
- `stage-workflow-view.css`: 440 lines
- `CharacterSummaryDialog.vue`: 30 lines
- `character-summary-dialog.css`: 70 lines
- `ImagePreviewOverlay.vue`: 50 lines
- `image-preview-overlay.css`: 70 lines
- `WorkflowFinalBoard.vue`: 90 lines
- `WorkflowMissingClips.vue`: 60 lines
- `workflow-final-board.css`: 100 lines
- `WorkflowVideoBoard.vue`: 280 lines
- `workflow-video-board.css`: 260 lines
- `WorkflowKeyframeBoard.vue`: 230 lines
- `workflow-keyframe-board.css`: 230 lines
- `WorkflowCharacterBoard.vue`: 250 lines
- `workflow-character-board.css`: 220 lines
- `WorkflowStoryboardBoard.vue`: 160 lines
- `workflow-storyboard-board.css`: 230 lines
- `WorkflowHeaderSettings.vue`: 230 lines
- `workflow-header-settings.css`: 320 lines
- `workflow-settings.ts`: 120 lines
- `useWorkflowStagePreviews.ts`: 130 lines
- `useWorkflowStageCommands.ts`: 140 lines
- `useGenerationForm.ts`: 330 lines
- `useGenerationFormPresentation.ts`: 130 lines
- `useGenerationFormCatalog.ts`: 180 lines
- `generationFormOptions.ts`: 190 lines
- `useReferenceImages.ts`: 310 lines
- `referenceImageLayout.ts`: 140 lines
- `MaterialLibraryView.vue`: 400 lines
- `useMaterialLibraryState.ts`: 170 lines
- `useMaterialLibraryLifecycle.ts`: 150 lines
- `useMaterialAssetCommands.ts`: 220 lines
- `useMaterialFavoriteCommands.ts`: 270 lines
- `useMaterialSharing.ts`: 110 lines
- `material-library-view.css`: 850 lines
- `MaterialAssetCard.vue`: 320 lines
- `material-asset-card.css`: 430 lines
- `MaterialFavoriteDialog.vue`: 180 lines
- `material-favorite-dialog.css`: 300 lines
- `material-favorite-dialog.ts`: 20 lines
- `useMaterialPreview.ts`: 110 lines
- `useMaterialPagination.ts`: 100 lines
- `ImageTaskListPanel.vue`: 150 lines
- `image-task-list-panel.css`: 280 lines
- `useImageTaskListViewport.ts`: 130 lines
- `HomeView.vue`: 410 lines
- `home-view.css`: 660 lines
- `HomeBrandPlay.vue`: 110 lines
- `home-brand-play.css`: 500 lines
- `HomeActiveTasks.vue`: 50 lines
- `home-active-tasks.css`: 160 lines
- `HomeTaskToast.vue`: 40 lines
- `home-task-toast.css`: 130 lines
- `HomeComposerToolbar.vue`: 330 lines
- `PromptTemplateGallery.vue`: 110 lines
- `prompt-templates.ts`: 110 lines
- `prompt-template-gallery.css`: 260 lines
- `PublicShareGallery.vue`: 140 lines
- `usePublicShareGallery.ts`: 140 lines
- `public-share-gallery.css`: 220 lines
- `home-composer-toolbar.css`: 710 lines
- `active-task-presenters.ts`: 50 lines
- `home-submission.ts`: 120 lines
- `useHomeSubmissionGuard.ts`: 90 lines
- `useHomeComposerSubmission.ts`: 170 lines
- `useHomeComposerLifecycle.ts`: 110 lines
- `useHomeComposerControls.ts`: 150 lines
- `usePromptEditor.ts`: 170 lines
- `prompt-editor-dom.ts`: 200 lines
- `task_repository.py`: 270 lines
- `task_repository_aggregate_loader.py`: 250 lines
- `task_repository_mapping.py`: 340 lines
- `task_repository_mutations.py`: 180 lines
- `task_repository_entity_upserts.py`: 380 lines
- `task_repository_queries.py`: 250 lines
- `task_repository_summary_support.py`: 230 lines
- `task_repository_detail_queries.py`: 340 lines
- `task_repository_detail_collections.py`: 250 lines
- `task_repository_queue.py`: 260 lines
- `TaskDetailPanel.vue`: 380 lines
- `TaskDetailActions.vue`: 100 lines
- `TaskStageTimeline.vue`: 80 lines
- `TaskMonitoringSummary.vue`: 70 lines
- `CreateTaskDialog.vue`: 100 lines
- `create-task-dialog.css`: 150 lines
- `useCreateTaskDialog.ts`: 170 lines
- `create-task-options.ts`: 100 lines
- `useTaskPreviewState.ts`: 90 lines
- `useTaskResultSharing.ts`: 120 lines
- `useTaskDetail.ts`: 400 lines
- `useTaskDetailLoader.ts`: 130 lines
- `useTaskDetailCommands.ts`: 170 lines
- `task-detail-presenters.ts`: 250 lines
- `task-detail-panel.css`: 380 lines
- `task-detail-actions.css`: 70 lines
- `task-stage-timeline.css`: 350 lines
- `task-monitoring-summary.css`: 90 lines
- `TaskPromptDialog.vue`: 70 lines
- `task-prompt-dialog.css`: 150 lines
- `TaskResultPreview.vue`: 190 lines
- `task-result-preview.css`: 350 lines
- `WorkflowDetailPanel.vue`: 450 lines
- `workflow-detail-panel.css`: 470 lines
- `WorkflowCharacterAssetPicker.vue`: 100 lines
- `workflow-character-asset-picker.css`: 80 lines
- `WorkflowAutoPilotBar.vue`: 120 lines
- `workflow-auto-pilot-bar.css`: 60 lines
- `useWorkflowDetail.ts`: 370 lines
- unified `useWorkflowPreviewInteractions.ts` adapter: 30 lines
- `useWorkflowDetailLoader.ts`: 130 lines
- `useWorkflowGenerationCommands.ts`: 240 lines
- `useWorkflowVersionCommands.ts`: 150 lines
- `useWorkflowAutoPilotSync.ts`: 130 lines
- `workflow-detail-presenters.ts`: 210 lines
- `useWorkflowDetailHeader.ts`: 80 lines
- `TaskManagementView.vue`: 330 lines
- `useAdminTaskList.ts`: 160 lines
- `DashboardView.vue`: 220 lines
- `InviteManagementView.vue`: 150 lines
- `invite-management-view.css`: 150 lines
- `useInviteManagement.ts`: 130 lines
- `invite-management-presenters.ts`: 50 lines
- `dashboard-view.css`: 270 lines
- `useAdminDashboard.ts`: 90 lines
- `dashboard-presenters.ts`: 100 lines
- `task-management-view.css`: 180 lines
- `AdminTaskDetailExpansion.vue`: 160 lines
- `admin-task-detail-expansion.css`: 180 lines
- `task-management-presenters.ts`: 350 lines
- `useAdminTaskCommands.ts`: 200 lines
- `TaskDetailView.vue`: 230 lines
- `task-detail-view.css`: 250 lines
- `AdminTaskOverviewCard.vue`: 180 lines
- `admin-task-overview-card.css`: 100 lines
- `admin-task-detail-presenters.ts`: 310 lines
- `WorkspaceShell.vue`: 80 lines
- `workspace-shell.css`: 320 lines
- `WorkspaceAccountMenu.vue`: 170 lines
- `workspace-account-menu.css`: 290 lines
- `CreditDetailsDialog.vue`: 290 lines
- `credit-details-dialog.css`: 450 lines
- `credit-details-presenters.ts`: 80 lines
- `UserManagementView.vue`: 220 lines
- `user-management-view.css`: 180 lines
- `useUserManagement.ts`: 300 lines
- `UserManagementDialogs.vue`: 170 lines
- `user-management-dialogs.css`: 80 lines
- `user-management-presenters.ts`: 40 lines
- `CreditManagementView.vue`: 220 lines
- `credit-management-view.css`: 110 lines
- `useCreditManagement.ts`: 220 lines
- `credit-management-presenters.ts`: 40 lines

## Next extraction batches

1. Continue splitting task persistence: mapping, full aggregate loading, summary orchestration, summary filters/support reads, task detail reads, detail child rows, atomic mutation ordering, entity upserts, and queue/worker persistence now have separate modules. Keep `task_repository.py` as the low-level session/row compatibility facade; keep transaction ownership in `task_repository_mutations.py`, summary SQL support in `task_repository_summary_support.py`, and entity mapping in `task_repository_entity_upserts.py`.
2. Continue splitting unified workspace panels: the unreferenced and superseded `WorkflowResultPanel.vue` has been removed. `CreateTaskDialog.vue` now delegates focus lifecycle, catalog loading and authenticated submission to `useCreateTaskDialog.ts`, model/size policy to `create-task-options.ts`, and styling to its CSS module. `WorkflowDetailPanel.vue` delegates header progress/status and AutoPilot synchronization to `useWorkflowDetailHeader.ts`, reuses the current workflow page's storyboard, keyframe, video and final boards, and shares header settings, character summary and image preview components; only its enhanced character-material picker remains locally composed. Keep `TaskDetailPanel.vue` as the detail composition root; task status actions, stage timelines, and monitoring/artifact summaries have independent components and styles.
3. Keep `StageWorkflowView.vue` as the current workflow composition root. Character completeness, video readiness, five-stage status and finalization hints are shared with the unified workspace through `useWorkflowStageReadiness.ts`; character summaries, keyframe galleries, failed-image state and preview keyboard lifecycle share `useWorkflowPreviewInteractions.ts`; version deletion, stage clearing and asset reuse share `useWorkflowVersionCommands.ts`; settings mutation, workflow deletion, batch character generation and character asset selection belong to `useStageWorkflowManagementCommands.ts`; route/detail loading belongs to `useStageWorkflowDetailLoader.ts`; download handling, popover positioning and menu lifecycle belong to `useStageWorkflowInteractions.ts`.
4. Keep `MaterialLibraryView.vue` as the material feature composition root. Tabs, filters, batch selection, favorite-folder projection and query construction belong in `useMaterialLibraryState.ts`; authenticated initial loading, route filter hydration, infinite-scroll observer and watcher cleanup belong in `useMaterialLibraryLifecycle.ts`; asset rename/upload/delete/reuse/download transactions, favorite-folder commands, sharing, preview navigation and pagination/loading have dedicated composables.
5. Keep `model_config_service.py` as a compatibility facade and preserve the separated runtime/admin/user boundaries. `model_config_runtime.py` owns the cached facade and catalog queries; text profile construction belongs to `model_config_runtime_text.py`, while image/video profile construction belongs to `model_config_runtime_media.py`. Runtime user/global-default credential scope and sibling-provider fallback belong to `model_config_runtime_credentials.py`; YAML discovery, overlay merging, caching and fail-fast behavior belong to `model_config_runtime_snapshot.py`.
6. Continue the admin task page split with list loading/pagination state if it grows again; display rows, expandable details, and terminate/delete confirmation orchestration now have independent modules.
7. Keep `TaskDetailView.vue` focused on API loading, retry/delete commands, trace/diagnosis composition and routing. Task overview, request parameters, monitoring, duration diagnostics, artifacts and plan rendering belong to `AdminTaskOverviewCard.vue`; their display models remain in `admin-task-detail-presenters.ts`.
8. Keep `WorkspaceShell.vue` as a navigation/layout shell; account, credit, logout and outside-click lifecycle belong in `WorkspaceAccountMenu.vue`.
9. Keep `media_service.py` as the local artifact compatibility facade. Shared artifact value objects belong in `media_artifacts.py`; prompt-card drawing and text layout belong in `media_prompt_cards.py`; thumbnail generation and caching belong in `media_thumbnails.py`; silent-video generation and concatenation belong in `media_video_operations.py`; artifact persistence, publication, copying and remote materialization belong in `media_artifact_storage.py`.
10. Keep `UserManagementView.vue` as the user-table composition root. Pagination, filters, dialog state and user/password/model-Key commands belong in `useUserManagement.ts`; its three forms and dialog-specific layout belong in `UserManagementDialogs.vue`; page and dialog styles, plus display formatting, have independent modules.

## Required quality gates

```bash
uv run ruff check backend tests migrations
uv run pytest tests/ -q
npm run web:lint
npm run web:typecheck
npm run web:test
npm run packages:typecheck
```

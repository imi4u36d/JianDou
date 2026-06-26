<template>
  <main class="task-detail-panel">
    <section v-if="!selectedTaskId" class="task-detail-empty">
      <h3>选择任务</h3>
    </section>

    <section v-else class="task-detail-content" aria-labelledby="task-detail-title">
      <header class="task-detail-header">
        <div>
          <h2 id="task-detail-title">{{ selectedTask?.title || "任务详情" }}</h2>
          <div class="task-detail-header__meta">
            <span class="surface-chip">{{ selectedTaskTypeLabel }}</span>
            <span class="surface-chip" :title="selectedTaskId">{{ selectedTaskShortId }}</span>
            <span class="surface-chip">{{ selectedTaskStageLabel }}</span>
            <span v-if="selectedTaskLoading" class="surface-chip surface-chip-loading">
              <IconRefresh size="xs" />
            </span>
          </div>
        </div>
        <button class="task-detail-close-button" type="button" aria-label="关闭详情" title="关闭" @click="$emit('close')">
          <IconClose size="sm" />
        </button>
      </header>

      <div class="detail-stage-line" aria-label="任务阶段">
        <div v-for="stage in selectedTaskStages" :key="stage.key" class="detail-stage-line__item" :class="`detail-stage-line__item-${stage.state}`">
          <span class="detail-stage-line__dot" :class="stageStateClass(stage.state)" aria-hidden="true"></span>
          <span class="detail-stage-line__copy">
            <strong>{{ stage.label }}</strong>
            <small>{{ stage.stateLabel }}</small>
          </span>
        </div>
      </div>

      <section v-if="selectedTaskFailureReason" class="task-failure-card" :class="{ 'task-failure-card-open': failureDetailsOpen }">
        <button type="button" class="task-failure-card__summary" :aria-expanded="failureDetailsOpen" @click="failureDetailsOpen = !failureDetailsOpen">
          <span class="task-failure-card__icon" aria-hidden="true"><IconWarning size="xs" /></span>
          <strong>{{ selectedTaskFailureContext || "任务失败" }}</strong>
          <small class="task-failure-card__chevron" aria-hidden="true">
            <IconChevronDown size="xs" />
          </small>
        </button>
        <p v-if="failureDetailsOpen">{{ selectedTaskFailureReason }}</p>
      </section>

      <div class="task-detail-grid task-detail-grid-primary">
        <section class="detail-section detail-section-card detail-preview-section">
          <div class="detail-section__head">
            <h3>结果预览</h3>
            <span class="surface-chip">{{ selectedTaskJoinProgressPercent }}%</span>
          </div>
          <div class="task-result-preview">
            <video
              v-if="selectedTaskPreviewMedia?.type === 'video'"
              :src="selectedTaskPreviewMedia.url"
              :poster="selectedTaskPreviewMedia.posterUrl || undefined"
              controls
              playsinline
              preload="metadata"
              :aria-label="selectedTaskPreviewMedia.title"
            ></video>
            <img
              v-else-if="selectedTaskPreviewMedia?.type === 'image'"
              :src="selectedTaskPreviewMedia.url"
              :alt="selectedTaskPreviewMedia.title || '任务结果预览'"
            />
            <div v-else>生成中</div>
          </div>
          <div class="detail-overview">
            <div class="detail-overview__row detail-overview__row-progress">
              <span>进度</span>
              <div class="detail-overview__progress">
                <div class="detail-overview__progress-fill" :style="{ width: `${selectedTaskJoinProgressPercent}%` }"></div>
              </div>
              <strong>{{ selectedTaskJoinProgressPercent }}%</strong>
            </div>
            <div class="detail-overview__row"><span>参考图</span><strong>{{ selectedReferenceImageCount }} 张</strong></div>
            <div class="detail-overview__row"><span>实例</span><strong :title="selectedTaskActionTask?.activeWorkerInstanceId || ''">{{ selectedTaskShortWorkerLabel }}</strong></div>
            <div class="detail-overview__row"><span>种子</span><strong>{{ selectedTaskSeedLabel }}</strong></div>
          </div>
        </section>

        <section class="detail-section detail-section-card">
          <div class="detail-section__head">
            <h3>请求参数</h3>
            <span class="surface-chip">{{ selectedTaskDurationModeLabel }}</span>
          </div>
          <div class="detail-params">
            <div v-for="item in selectedTaskCompactParameterRows" :key="item.label" class="detail-params__row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
          <div v-if="selectedTaskTranscriptPreview" class="detail-note-block">
            <span>Prompt</span>
            <p>{{ selectedTaskTranscriptPreview }}</p>
          </div>
        </section>
      </div>

      <section v-if="selectedTaskResultItems.length || selectedTaskMaterialItems.length" class="detail-section detail-section-card">
        <div class="detail-section__head">
          <h3>结果和素材</h3>
          <RouterLink class="surface-chip detail-material-link" :to="materialLibraryLink">素材库</RouterLink>
        </div>
        <div class="detail-result-list">
          <a v-for="item in selectedTaskResultItems" :key="`result-${item.url}`" :href="item.url" target="_blank" rel="noreferrer">
            <IconDownload size="xs" />
            <span>{{ item.title }}</span>
          </a>
          <a v-for="item in selectedTaskMaterialItems" :key="`material-${item.url}`" :href="item.url" target="_blank" rel="noreferrer">
            <IconDownload size="xs" />
            <span>{{ item.title }}</span>
          </a>
        </div>
      </section>

      <div v-if="selectedTaskCompactMonitoringRows.length || selectedTaskCompactArtifactRows.length" class="task-detail-grid task-detail-grid-secondary">
        <section v-if="selectedTaskCompactMonitoringRows.length" class="detail-section detail-section-card">
          <h3>监控</h3>
          <div class="detail-params">
            <div v-for="item in selectedTaskCompactMonitoringRows" :key="item.label" class="detail-params__row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>

        <section v-if="selectedTaskCompactArtifactRows.length" class="detail-section detail-section-card">
          <div class="detail-section__head">
            <h3>产物</h3>
            <span class="surface-chip" :title="selectedTaskArtifactDirectoryHint">{{ selectedTaskShortArtifactDirectoryHint }}</span>
          </div>
          <div class="detail-params">
            <div v-for="item in selectedTaskCompactArtifactRows" :key="item.label" class="detail-params__row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>
      </div>

      <section class="detail-section detail-section-card">
        <div class="detail-section__head">
          <h3>追踪</h3>
          <span class="surface-chip">{{ selectedTaskTrace.length }}</span>
        </div>
        <div class="detail-traces">
          <div v-if="selectedTaskTrace.length === 0" class="detail-traces__empty">暂无记录</div>
          <div v-for="event in selectedTaskTracePreview" :key="`${event.timestamp}-${event.event}-${event.stage}`" class="detail-traces__item">
            <p>{{ event.message }}</p>
            <small>
              <span class="detail-traces__stage">{{ formatTraceStage(event.stage) }}</span>
              <span class="detail-traces__event">{{ formatTraceEvent(event.event) }}</span>
              <span class="detail-traces__time">{{ formatDateTime(event.timestamp) }}</span>
            </small>
          </div>
        </div>
      </section>

      <div class="detail-actions">
        <button v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING'].includes(selectedTaskActionTask.status)" class="detail-action-btn" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handlePause(selectedTaskActionTask)">
          <span class="detail-action-btn__pause" aria-hidden="true"></span>
          暂停
        </button>
        <button v-if="selectedTaskActionTask && ['PENDING', 'ANALYZING', 'PLANNING', 'RENDERING'].includes(selectedTaskActionTask.status)" class="detail-action-btn detail-action-btn-warning" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleTerminate(selectedTaskActionTask)">
          <IconWarning size="xs" />
          终止
        </button>
        <button v-if="selectedTaskActionTask?.status === 'PAUSED'" class="detail-action-btn detail-action-btn-primary" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleContinueTask(selectedTaskActionTask)">
          <IconRefresh size="xs" />
          继续
        </button>
        <button class="detail-action-btn" type="button" :disabled="selectedTaskLoading" @click="refreshSelectedTask">
          <IconRefresh size="xs" />
          刷新
        </button>
        <button v-if="selectedTaskActionTask" class="detail-action-btn detail-action-btn-danger" type="button" :disabled="selectedTaskLoading || managingTaskId === selectedTaskActionTask.id" @click="handleDelete(selectedTaskActionTask)">
          <IconDelete size="xs" />
          删除
        </button>
      </div>
    </section>

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
  </main>
</template>

<script setup lang="ts">
/**
 * 任务详情面板组件。
 * 从 TasksView 提取，展示选中任务的详情、监控和操作。
 */
import { RouterLink } from "vue-router";
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import { IconChevronDown, IconClose, IconDelete, IconDownload, IconRefresh, IconWarning } from "@/components/icons";
import { useTaskDetail } from "../composables/useTaskDetail";
import type { TaskListItem } from "@/types";

const props = defineProps<{
  selectedTaskId: string;
  tasks: TaskListItem[];
  reloadTasks: () => Promise<void>;
}>();

const emit = defineEmits<{
  close: [];
  deleted: [taskId: string];
}>();

const detail = useTaskDetail({
  selectedTaskId: () => props.selectedTaskId,
  tasks: () => props.tasks,
  reloadTasks: props.reloadTasks,
  onDeleted: (taskId) => emit("deleted", taskId),
});

const {
  selectedTaskTrace,
  selectedTaskLoading,
  managingTaskId,
  failureDetailsOpen,
  selectedTask,
  selectedTaskActionTask,
  selectedTaskTypeLabel,
  selectedTaskShortId,
  selectedTaskStageLabel,
  selectedTaskDurationModeLabel,
  selectedTaskTranscriptPreview,
  selectedReferenceImageCount,
  selectedTaskSeedLabel,
  selectedTaskCompactParameterRows,
  selectedTaskJoinProgressPercent,
  selectedTaskCompactMonitoringRows,
  selectedTaskShortWorkerLabel,
  selectedTaskFailureReason,
  selectedTaskFailureContext,
  selectedTaskPreviewMedia,
  selectedTaskResultItems,
  selectedTaskMaterialItems,
  selectedTaskTracePreview,
  materialLibraryLink,
  selectedTaskCompactArtifactRows,
  selectedTaskShortArtifactDirectoryHint,
  selectedTaskArtifactDirectoryHint,
  selectedTaskStages,
  loadSelectedTaskDetails,
  refreshSelectedTask,
  handlePause,
  handleTerminate,
  handleContinueTask,
  handleDelete,
  formatDateTime,
  formatTraceStage,
  formatTraceEvent,
  stageStateClass,
  confirmDialog,
  acceptConfirm,
  cancelConfirm,
} = detail;

// 选中变化时重新加载详情
import { watch } from "vue";
watch(() => props.selectedTaskId, () => {
  void loadSelectedTaskDetails();
}, { immediate: true });
</script>

<style scoped>
.task-detail-panel {
  display: grid;
  min-width: 0;
  min-height: 0;
  padding: 14px;
  overflow: auto;
}

.task-detail-empty {
  display: grid;
  place-items: center;
  min-height: 200px;
  color: var(--text-muted);
}

.task-detail-content {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.task-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 12px 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 60%, rgba(255, 255, 255, 0));
}

.task-detail-header h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text-strong);
}

.task-detail-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.surface-chip-loading {
  animation: chip-spin 1s linear infinite;
}

@keyframes chip-spin {
  to { transform: rotate(360deg); }
}

.task-detail-close-button {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
}

.task-detail-close-button:hover {
  background: var(--bg-soft);
  color: var(--text-strong);
}

.detail-stage-line {
  display: flex;
  gap: 2px;
  padding: 8px 0;
}

.detail-stage-line__item {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.detail-stage-line__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid var(--text-muted);
}

.detail-stage-line__dot.task-stage-row--done {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
}

.detail-stage-line__dot.task-stage-row--active {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}

.detail-stage-line__dot.task-stage-row--paused {
  background: var(--accent-warning);
  border-color: var(--accent-warning);
}

.detail-stage-line__dot.task-stage-row--failed {
  background: var(--accent-danger);
  border-color: var(--accent-danger);
}

.detail-stage-line__copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.detail-stage-line__copy strong {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-strong);
}

.detail-stage-line__copy small {
  font-size: 0.68rem;
  color: var(--text-muted);
}

.task-failure-card {
  border-radius: 12px;
  border: 1px solid rgba(229, 72, 101, 0.2);
  background: rgba(229, 72, 101, 0.04);
  padding: 10px 14px;
}

.task-failure-card__summary {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: var(--accent-danger);
  font-size: 0.85rem;
  padding: 0;
}

.task-failure-card__chevron {
  margin-left: auto;
  transition: transform 0.2s;
}

.task-failure-card-open .task-failure-card__chevron {
  transform: rotate(180deg);
}

.task-failure-card p {
  margin: 10px 0 0;
  font-size: 0.82rem;
  color: var(--text-body);
  white-space: pre-wrap;
  word-break: break-word;
}

.task-detail-grid {
  display: grid;
  gap: 14px;
}

.task-detail-grid-primary {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.task-detail-grid-secondary {
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.detail-section {
  display: grid;
  gap: 10px;
}

.detail-section-card {
  padding: 14px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  border: 1px solid var(--glass-border);
}

.detail-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.detail-section__head h3 {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-strong);
}

.task-result-preview {
  border-radius: 10px;
  overflow: hidden;
  background: var(--bg-softer);
  min-height: 160px;
  display: grid;
  place-items: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.task-result-preview img,
.task-result-preview video {
  width: 100%;
  max-height: min(52vh, 420px);
  display: block;
  object-fit: contain;
}

.task-result-preview video {
  aspect-ratio: 16 / 9;
  background: #111827;
}

.detail-overview {
  display: grid;
  gap: 6px;
}

.detail-overview__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.82rem;
  color: var(--text-body);
}

.detail-overview__row strong {
  color: var(--text-strong);
  font-weight: 600;
}

.detail-overview__row-progress {
  gap: 10px;
}

.detail-overview__progress {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-softer);
  overflow: hidden;
}

.detail-overview__progress-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--accent-indigo);
  transition: width 0.3s;
}

.detail-params {
  display: grid;
  gap: 4px;
}

.detail-params__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.8rem;
  padding: 3px 0;
  color: var(--text-body);
}

.detail-params__row strong {
  color: var(--text-strong);
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}

.detail-note-block {
  margin-top: 8px;
  padding: 10px;
  border-radius: 8px;
  background: var(--bg-softer);
}

.detail-note-block span {
  display: block;
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.detail-note-block p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-body);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow: auto;
}

.detail-material-link {
  text-decoration: none;
}

.detail-result-list {
  display: grid;
  gap: 6px;
}

.detail-result-list a {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--bg-softer);
  color: var(--accent-indigo);
  text-decoration: none;
  font-size: 0.82rem;
  transition: background 0.15s;
}

.detail-result-list a:hover {
  background: var(--bg-soft);
}

.detail-traces {
  display: grid;
  gap: 6px;
  max-height: 240px;
  overflow: auto;
}

.detail-traces__empty {
  text-align: center;
  padding: 16px;
  color: var(--text-muted);
  font-size: 0.82rem;
}

.detail-traces__item {
  padding: 6px 0;
  border-bottom: 1px solid var(--bg-softer);
}

.detail-traces__item p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-body);
  word-break: break-word;
}

.detail-traces__item small {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 0.7rem;
  color: var(--text-muted);
}

.detail-traces__stage {
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--bg-softer);
  font-weight: 600;
  font-size: 0.68rem;
}

.detail-traces__event {
  color: var(--text-body);
}

.detail-traces__time {
  margin-left: auto;
  font-family: monospace;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  position: sticky;
  bottom: 0;
  padding: 12px 0;
  background: linear-gradient(0deg, rgba(255, 255, 255, 0.92) 60%, rgba(255, 255, 255, 0));
}

.detail-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid var(--glass-border);
  background: var(--bg-surface);
  color: var(--text-strong);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}

.detail-action-btn:hover:not(:disabled):not(.detail-action-btn-primary):not(.detail-action-btn-warning):not(.detail-action-btn-danger) {
  background: var(--bg-soft);
}

.detail-action-btn-primary:hover:not(:disabled) {
  background: #5558e3;
}

.detail-action-btn-warning:hover:not(:disabled) {
  background: #c26b05;
}

.detail-action-btn-danger:hover:not(:disabled) {
  background: #d43d5e;
}

.detail-action-btn:active:not(:disabled) {
  transform: scale(0.97);
}

.detail-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.detail-action-btn-primary {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
  color: white;
}

.detail-action-btn-warning {
  background: var(--accent-warning);
  border-color: var(--accent-warning);
  color: white;
}

.detail-action-btn-danger {
  background: var(--accent-danger);
  border-color: var(--accent-danger);
  color: white;
}

.detail-action-btn__pause {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-left: 3px solid currentColor;
  border-right: 3px solid currentColor;
}

@media (max-width: 640px) {
  .task-detail-grid-primary,
  .task-detail-grid-secondary {
    grid-template-columns: 1fr;
  }

  .detail-actions {
    flex-direction: column;
  }

  .detail-action-btn {
    justify-content: center;
  }
}
</style>

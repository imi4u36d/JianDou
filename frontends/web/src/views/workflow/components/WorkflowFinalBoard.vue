<template>
  <section class="workflow-stage-board final-board">
    <div class="stage-board__head">
      <h3>成片</h3>
      <div class="stage-board__meta">
        <div class="readiness-strip">
          <span>{{ readiness.total }} 镜头</span><span>{{ readiness.selected }} 已选</span
          ><span>{{ finalizeHint }}</span>
        </div>
        <button
          class="jd-button jd-button--primary jd-button--sm"
          type="button"
          :disabled="!canFinalize || busyActionKey === 'finalize'"
          @click="$emit('finalize')"
        >
          <IconLoading v-if="busyActionKey === 'finalize'" size="xs" /><span>{{
            busyActionKey === "finalize" ? "拼接中" : finalizeButtonLabel
          }}</span>
        </button>
      </div>
    </div>

    <article v-if="finalResult" class="final-result">
      <video
        v-if="finalResult.publicUrl || finalResult.fileUrl"
        :src="finalResult.publicUrl || finalResult.fileUrl"
        controls
        playsinline
        preload="metadata"
      ></video>
      <div class="final-result__meta">
        <div>
          <h4>{{ finalResult.title }}</h4>
          <div class="kv-row">
            <span>时长</span><strong>{{ durationLabel(finalResult.durationSeconds) }}</strong>
          </div>
        </div>
        <WorkflowMissingClips
          v-if="readiness.missing.length"
          :clips="readiness.missing"
          hint="选中视频版本后可重新拼接。"
          @open="$emit('open-missing', $event)"
        />
        <button
          class="icon-action"
          type="button"
          aria-label="下载成片"
          @click="$emit('download', finalResult.publicUrl || finalResult.fileUrl || '', finalResult.title)"
        >
          <IconDownload size="xs" />
        </button>
      </div>
    </article>
    <WorkflowStageEmptyState
      v-else
      :compact="readiness.missing.length > 0"
      :title="canFinalize ? '片段已准备好' : `缺 ${readiness.missing.length} 个镜头`"
      :description="
        canFinalize
          ? '点击右上角按钮，将已选视频片段拼接为最终成片。'
          : `还需补齐 ${readiness.missing.length} 个镜头的视频片段。`
      "
    />
    <WorkflowMissingClips
      v-if="!finalResult && readiness.missing.length"
      :clips="readiness.missing"
      hint="点选后补齐。"
      @open="$emit('open-missing', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { durationLabel } from "@/features/workflows/stage-workflow-presenters";
import type { MaterialAssetLibraryItem, WorkflowClipSlot } from "@/types";
import { IconDownload, IconLoading } from "@/components/icons";
import WorkflowMissingClips from "./WorkflowMissingClips.vue";
import WorkflowStageEmptyState from "./WorkflowStageEmptyState.vue";

defineProps<{
  finalResult: MaterialAssetLibraryItem | null;
  readiness: { total: number; selected: number; missing: WorkflowClipSlot[] };
  canFinalize: boolean;
  finalizeHint: string;
  finalizeButtonLabel: string;
  busyActionKey: string;
}>();
defineEmits<{ finalize: []; download: [url: string, title: string]; "open-missing": [clipIndex: number] }>();
</script>

<style scoped src="./workflow-final-board.css"></style>

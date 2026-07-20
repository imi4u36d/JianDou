<!-- eslint-disable vue/no-v-html -->
<template>
  <section class="workflow-stage-board storyboard-board">
    <div class="stage-board__head">
      <h3>分镜脚本</h3>
      <div class="stage-board__head-actions">
        <button
          v-if="versions.length"
          class="jd-button jd-button--secondary jd-button--sm workflow-menu-danger"
          type="button"
          :disabled="busyActionKey === 'clear-storyboard-versions'"
          @click="$emit('clear')"
        >
          <IconLoading v-if="busyActionKey === 'clear-storyboard-versions'" size="xs" />
          <IconDelete v-else size="xs" />
          <span>{{ busyActionKey === "clear-storyboard-versions" ? "清空中" : "清空分镜版本" }}</span>
        </button>
        <button
          class="jd-button jd-button--primary jd-button--sm"
          type="button"
          :disabled="busyActionKey === 'storyboard'"
          @click="$emit('generate')"
        >
          <IconLoading v-if="busyActionKey === 'storyboard'" size="xs" />
          <span>{{ busyActionKey === "storyboard" ? "生成中" : "生成" }}</span>
        </button>
      </div>
    </div>

    <WorkflowStageEmptyState
      v-if="!versions.length"
      title="还没有分镜脚本"
      description="点击右上角“生成”，先把创作想法拆成清晰的镜头计划。"
    />
    <div v-else class="storyboard-layout">
      <article class="storyboard-preview-card">
        <div class="version-switcher__tabs">
          <article
            v-for="version in versions"
            :key="version.id"
            class="version-switcher__tab"
            :class="{ 'version-switcher__tab-active': selectedVersion?.id === version.id }"
          >
            <button type="button" class="version-switcher__tab-main" @click="$emit('preview', version.id)">
              <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
              <strong>{{ stageVersionDisplayTitle(version) }}</strong>
              <span class="compact-version-card__status">{{
                version.selected ? "当前" : stageStatusLabel(version.status)
              }}</span>
            </button>
            <div class="workflow-more-menu compact-version-menu">
              <button
                type="button"
                class="workflow-more-menu__trigger"
                aria-label="版本操作"
                :popovertarget="`vsm-${version.id}`"
              >
                <IconMore size="sm" />
              </button>
              <div
                :id="`vsm-${version.id}`"
                popover
                class="workflow-more-menu__popover"
                @beforetoggle="$emit('position-menu', $event)"
              >
                <button
                  type="button"
                  :disabled="version.selected || busyActionKey === version.id"
                  @click="$emit('select', version.id)"
                >
                  <IconCheck size="xs" /><span>{{ version.selected ? "当前" : "设为当前" }}</span>
                </button>
                <button
                  type="button"
                  :disabled="!version.asset || busyActionKey === `reuse-${version.id}`"
                  @click="$emit('reuse', version.asset?.id || '', version.id)"
                >
                  <IconPlus size="xs" /><span>复用</span>
                </button>
                <button
                  type="button"
                  class="workflow-menu-danger"
                  :disabled="busyActionKey === `delete-${version.id}`"
                  @click="$emit('delete', version)"
                >
                  <IconDelete size="xs" /><span>删除</span>
                </button>
              </div>
            </div>
          </article>
        </div>
        <div
          v-if="selectedVersion"
          class="storyboard-preview-markdown"
          v-html="storyboardPreviewHtml(selectedVersion)"
        ></div>
        <div v-if="selectedVersion" class="storyboard-adjust-panel">
          <input
            :value="adjustment"
            class="field-input storyboard-adjust-panel__input"
            type="text"
            placeholder="调整要求，可留空"
            @input="$emit('update:adjustment', ($event.target as HTMLInputElement).value)"
          />
          <button
            class="jd-button jd-button--primary jd-button--sm storyboard-adjust-panel__button"
            type="button"
            :disabled="
              busyActionKey === `storyboard-adjust-${selectedVersion.id}` || selectedVersion.status !== 'SUCCEEDED'
            "
            @click="$emit('adjust', selectedVersion.id)"
          >
            <IconLoading v-if="busyActionKey === `storyboard-adjust-${selectedVersion.id}`" size="xs" />
            <span>{{ busyActionKey === `storyboard-adjust-${selectedVersion.id}` ? "调整中" : "调整" }}</span>
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  stageStatusLabel,
  stageVersionDisplayTitle,
  storyboardPreviewHtml,
} from "@/features/workflows/stage-workflow-presenters";
import type { StageVersion } from "@/types";
import { IconCheck, IconDelete, IconLoading, IconMore, IconPlus } from "@/components/icons";
import WorkflowStageEmptyState from "./WorkflowStageEmptyState.vue";

defineProps<{
  versions: StageVersion[];
  selectedVersion: StageVersion | null;
  adjustment: string;
  busyActionKey: string;
}>();

defineEmits<{
  clear: [];
  generate: [];
  preview: [versionId: string];
  select: [versionId: string];
  reuse: [assetId: string, versionId: string];
  delete: [version: StageVersion];
  adjust: [versionId: string];
  "update:adjustment": [value: string];
  "position-menu": [event: ToggleEvent];
}>();
</script>

<style scoped src="./workflow-storyboard-board.css"></style>

<template>
  <header class="workflow-canvas-header">
    <div class="workflow-canvas-header__body">
      <h2>{{ title }}</h2>
      <div class="workflow-canvas-header__summary">
        <div class="workflow-summary__parameter-tags workflow-summary__parameter-tags-header">
          <span
            v-for="item in parameterTags"
            :key="item.label"
            class="surface-chip workflow-summary-tag"
            :title="`${item.label}：${item.value}`"
          >
            <span class="workflow-summary-tag__label" aria-hidden="true">{{ item.label }}</span>
            <strong class="workflow-summary-tag__value">{{ item.value }}</strong>
          </span>
        </div>
        <div v-if="$slots.actions" class="workflow-canvas-header__actions">
          <slot name="actions"></slot>
        </div>
        <button
          class="jd-button jd-button--secondary jd-button--sm workflow-canvas-header__settings-button"
          type="button"
          :class="{ 'workflow-canvas-header__settings-button-active': open }"
          :aria-label="open ? '收起参数' : '编辑参数'"
          :title="open ? '收起参数' : '编辑参数'"
          @click="emit('update:open', !open)"
        >
          <IconSettings size="sm" />
        </button>
      </div>

      <section v-if="open" class="workflow-header-settings">
        <div class="workflow-header-settings__head"><h3>编辑参数</h3></div>
        <form class="workflow-settings-stack workflow-header-settings__form" @submit.prevent="emit('save')">
          <label class="workflow-field">
            <span>文本模型</span>
            <AppSelect
              :model-value="settings.textAnalysisModel"
              :options="textModelOptions"
              @update:model-value="updateString('textAnalysisModel', $event)"
            />
          </label>
          <label class="workflow-field">
            <span>关键帧模型</span>
            <AppSelect
              :model-value="settings.imageModel"
              :options="imageModelOptions"
              @update:model-value="updateString('imageModel', $event)"
            />
          </label>
          <label class="workflow-field">
            <span>视频模型</span>
            <AppSelect
              :model-value="settings.videoModel"
              :options="videoModelOptions"
              @update:model-value="updateString('videoModel', $event)"
            />
          </label>
          <label class="workflow-field">
            <span>画幅</span>
            <AppSelect
              :model-value="settings.aspectRatio"
              :options="aspectRatioOptions"
              @update:model-value="updateString('aspectRatio', $event)"
            />
          </label>
          <label class="workflow-field">
            <span>输出尺寸</span>
            <AppSelect
              :model-value="settings.videoSize"
              :options="videoSizeOptions"
              @update:model-value="updateString('videoSize', $event)"
            />
          </label>
          <label class="workflow-field workflow-field-compact">
            <span>关键帧 Seed</span>
            <input
              :value="settings.keyframeSeed"
              class="field-input"
              type="number"
              min="0"
              placeholder="自动"
              @input="updateInput('keyframeSeed', $event)"
            />
          </label>
          <label class="workflow-field workflow-field-compact">
            <span>视频 Seed</span>
            <input
              :value="settings.videoSeed"
              class="field-input"
              type="number"
              min="0"
              placeholder="自动"
              @input="updateInput('videoSeed', $event)"
            />
          </label>
          <div class="workflow-field">
            <span>镜头时长</span>
            <div class="stage-toggle-row">
              <button
                type="button"
                class="stage-toggle-chip"
                :class="{ 'stage-toggle-chip-active': settings.durationMode === 'auto' }"
                @click="updateDurationMode('auto')"
              >
                自动
              </button>
              <button
                type="button"
                class="stage-toggle-chip"
                :class="{ 'stage-toggle-chip-active': settings.durationMode === 'manual' }"
                @click="updateDurationMode('manual')"
              >
                手动
              </button>
            </div>
          </div>
          <label v-if="settings.durationMode === 'manual'" class="workflow-field workflow-field-compact">
            <span>最小时长</span>
            <input
              :value="settings.minDurationSeconds"
              class="field-input"
              type="number"
              min="1"
              max="60"
              step="1"
              @input="updateInput('minDurationSeconds', $event)"
            />
          </label>
          <label v-if="settings.durationMode === 'manual'" class="workflow-field workflow-field-compact">
            <span>最大时长</span>
            <input
              :value="settings.maxDurationSeconds"
              class="field-input"
              type="number"
              min="1"
              max="60"
              step="1"
              @input="updateInput('maxDurationSeconds', $event)"
            />
          </label>
          <p v-if="validationMessage" class="workflow-error workflow-header-settings__error">
            {{ validationMessage }}
          </p>
          <div class="workflow-header-settings__actions">
            <button
              class="workflow-icon-action"
              type="button"
              :disabled="saving"
              title="收起"
              aria-label="收起参数"
              @click="emit('update:open', false)"
            >
              <IconClose size="xs" />
            </button>
            <button
              class="jd-button jd-button--primary jd-button--sm"
              type="submit"
              :disabled="saving || Boolean(validationMessage)"
            >
              <IconLoading v-if="saving" size="xs" />
              <span>{{ saving ? "保存中" : "保存" }}</span>
            </button>
          </div>
        </form>
      </section>
    </div>
  </header>
</template>

<script setup lang="ts">
import AppSelect from "@/components/common/AppSelect.vue";
import type { AppSelectOption } from "@/components/common/app-select";
import { IconClose, IconLoading, IconSettings } from "@/components/icons";
import {
  withWorkflowSetting,
  type WorkflowParameterTag,
  type WorkflowSettingsDraft,
} from "@/features/workflows/workflow-settings";

const props = defineProps<{
  title: string;
  parameterTags: WorkflowParameterTag[];
  open: boolean;
  settings: WorkflowSettingsDraft;
  textModelOptions: AppSelectOption[];
  imageModelOptions: AppSelectOption[];
  videoModelOptions: AppSelectOption[];
  aspectRatioOptions: AppSelectOption[];
  videoSizeOptions: AppSelectOption[];
  validationMessage: string;
  saving: boolean;
}>();

const emit = defineEmits<{
  "update:open": [value: boolean];
  "update:settings": [value: WorkflowSettingsDraft];
  save: [];
}>();

function updateSetting<K extends keyof WorkflowSettingsDraft>(key: K, value: WorkflowSettingsDraft[K]) {
  emit("update:settings", withWorkflowSetting(props.settings, key, value));
}

function updateString(key: keyof WorkflowSettingsDraft, value: unknown) {
  updateSetting(key, String(value ?? ""));
}

function updateInput(key: keyof WorkflowSettingsDraft, event: Event) {
  updateSetting(key, (event.target as HTMLInputElement).value);
}

function updateDurationMode(mode: WorkflowSettingsDraft["durationMode"]) {
  updateSetting("durationMode", mode);
}
</script>

<style scoped src="./workflow-header-settings.css"></style>

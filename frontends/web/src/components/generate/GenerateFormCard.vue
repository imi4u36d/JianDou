<template>
  <form class="form-card" @submit.prevent="$emit('submit')">
    <div class="form-head">
      <div>
        <h2>生成</h2>
      </div>
      <button type="button" class="usage-btn" @click="$emit('open-usage')">
        <IconLoading v-if="props.usageLoading" size="xs" />
        <IconInfo v-else size="xs" />
        <span>{{ props.usageLoading ? "读取" : "用量" }}</span>
      </button>
    </div>

    <div v-if="props.optionsLoading" class="state-tile">
      <IconLoading size="sm" />
      <span>加载中</span>
    </div>
    <div v-else-if="props.optionsError" class="error-tile">
      {{ props.optionsError }}
    </div>

    <label class="field">
      <span class="field-label">输入</span>
      <textarea
        v-model="props.form.prompt"
        rows="7"
        class="field-textarea"
        placeholder="例如：雨夜街头，人物回头，镜头缓慢推进，霓虹反射，电影感。"
      ></textarea>
    </label>

    <div class="field-grid">
      <label class="field">
        <span class="field-label">文本分析模型</span>
        <AppSelect v-model="props.form.textAnalysisModel" :options="textAnalysisModelOptions" />
        <TextModelProbeInline
          ref="textModelProbeRef"
          :model-value="props.form.textAnalysisModel"
          :disabled="props.optionsLoading || props.submitting"
        />
      </label>
      <label class="field">
        <span class="field-label">视频模型</span>
        <AppSelect v-model="props.form.providerModel" :options="videoModelOptions" />
      </label>
    </div>

    <div class="field-grid">
      <label class="field">
        <span class="field-label">清晰度 / 画幅</span>
        <AppSelect v-model="props.form.videoSize" :options="videoSizeOptions" />
      </label>
    </div>

    <div class="field-grid field-grid-duration">
      <label class="field">
        <span class="field-label">最小时长</span>
        <input
          v-model="props.form.minDurationSeconds"
          class="field-input"
          type="number"
          min="1"
          max="120"
          step="1"
          placeholder="可留空"
        />
      </label>
      <label class="field">
        <span class="field-label">最大时长</span>
        <input
          v-model="props.form.maxDurationSeconds"
          class="field-input"
          type="number"
          min="1"
          max="120"
          step="1"
          placeholder="可留空"
        />
      </label>
    </div>

    <div class="model-inline">
      <span>{{ props.selectedVideoModel?.label || props.form.providerModel }}</span>
      <span v-if="props.selectedVideoModel?.provider">{{ props.selectedVideoModel.provider }}</span>
      <span>{{ formatVideoSizeLabel(props.form.videoSize, "未选清晰度") }}</span>
      <span>{{ durationHint }}</span>
    </div>

    <div v-if="props.submitError" class="error-tile">
      {{ props.submitError }}
    </div>

    <button type="submit" class="submit-btn" :disabled="!props.canSubmit">
      <IconLoading v-if="props.submitting" size="xs" />
      <IconVideo v-else size="xs" />
      {{ props.submitting ? "生成中" : "生成" }}
    </button>
  </form>
</template>

<script setup lang="ts">
/**
 * Generate表单组件。
 */
import { computed, ref } from "vue";
import AppSelect from "@/components/common/AppSelect.vue";
import { IconInfo, IconLoading, IconVideo } from "@/components/icons";
import type { AppSelectOption } from "@/components/common/app-select";
import TextModelProbeInline from "@/components/TextModelProbeInline.vue";
import { formatVideoSizeLabel } from "@/utils/presentation";
import type { GenerateFormCardProps } from "./types";

const props = defineProps<GenerateFormCardProps>();
const textModelProbeRef = ref<{ ensureReady: (force?: boolean) => Promise<boolean> } | null>(null);
const textAnalysisModelOptions = computed<AppSelectOption[]>(() =>
  props.textAnalysisModels.map((item) => ({
    label: item.description ? `${item.label} · ${item.description}` : item.label,
    value: item.value,
  })),
);
const videoModelOptions = computed<AppSelectOption[]>(() =>
  props.videoModels.map((item) => ({
    label: item.label,
    value: item.value,
  })),
);
const videoSizeOptions = computed<AppSelectOption[]>(() =>
  props.videoSizes.map((item) => ({
    label: formatVideoSizeLabel(item.label || item.value),
    value: item.value,
  })),
);

const durationHint = computed(() => {
  const values = props.videoDurations.map((item) => item.value).filter((item) => Number.isFinite(item));
  return values.length ? `${values.join(" / ")} 秒` : "默认时长";
});

defineEmits<{
  submit: [];
  "open-usage": [];
}>();

defineExpose({
  async ensureTextModelReady() {
    return (await textModelProbeRef.value?.ensureReady()) !== false;
  },
});

</script>

<style scoped>
.form-card {
  display: grid;
  gap: 13px;
  padding: 18px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--text-strong);
  box-shadow:
    0 12px 30px rgba(99, 102, 241, 0.045),
    inset 0 1px 0 rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(40px) saturate(2.0);
}

.form-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-head h2 {
  margin: 0;
  font-family: inherit;
  font-size: 1rem;
  font-weight: 820;
  letter-spacing: 0;
  color: var(--text-strong);
}

.usage-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--text-body);
  font-size: 0.78rem;
  font-weight: 800;
  padding: 0 12px;
}

.state-tile {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.76);
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 760;
  padding: 12px;
}

.error-tile {
  display: grid;
  align-items: center;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid rgba(229, 72, 101, 0.12);
  border-radius: 13px;
  background: rgba(255, 244, 246, 0.76);
  color: var(--accent-danger);
  font-size: 0.82rem;
  font-weight: 720;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.field {
  display: grid;
  gap: 7px;
}

.field-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-grid-duration {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-label {
  color: var(--text-muted);
  font-size: 0.74rem;
  font-weight: 800;
}

.field-hint {
  margin: 0;
  color: #6b819b;
  font-size: 0.74rem;
  line-height: 1.5;
}

.field-input,
.field-select,
.field-textarea {
  width: 100%;
  min-height: 46px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--text-strong);
  padding: 0 14px;
  box-shadow: none;
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

.field-textarea {
  min-height: 160px;
  padding: 12px 14px;
  resize: vertical;
  line-height: 1.7;
}

.field-input:focus,
.field-select:focus,
.field-textarea:focus {
  outline: none;
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.3);
}

.model-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.model-inline span {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  border-radius: 999px;
  background: rgba(238, 242, 255, 0.78);
  border: 1px solid rgba(0, 0, 0, 0.06);
  padding: 0 9px;
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 700;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 46px;
  border: 0;
  border-radius: 13px;
  background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-blue) 100%);
  color: #fff;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 850;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(99, 102, 241, 0.2);
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    opacity 160ms ease;
}

.submit-btn:hover:not(:disabled),
.submit-btn:focus-visible {
  transform: translateY(-1px);
  box-shadow: 0 14px 32px rgba(99, 102, 241, 0.26);
}

.submit-btn:disabled {
  cursor: not-allowed;
  opacity: 0.48;
  box-shadow: none;
}

.submit-btn :deep(svg) {
  width: 16px;
  height: 16px;
}

@media (max-width: 820px) {
  .field-grid,
  .field-grid-duration {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 640px) {
  .form-card {
    padding: 1.1rem;
  }

  .form-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

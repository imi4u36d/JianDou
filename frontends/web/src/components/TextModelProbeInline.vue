<script lang="ts">
/**
 * 文本模型探测内联Expose接口定义。
 */
/**
 * 文本模型探测内联组件。
 */
export interface TextModelProbeInlineExpose {
  ensureReady: (force?: boolean) => Promise<boolean>;
  reset: () => void;
}
</script>

<template>
  <div class="text-model-probe">
    <button type="button" class="text-model-probe__button" :disabled="buttonDisabled" @click="handleProbe">
      <IconLoading v-if="probeState === 'loading'" size="xs" />
      <IconRefresh v-else-if="isCurrentModelReady" size="xs" />
      <IconCheck v-else size="xs" />
      <span>{{ buttonLabel }}</span>
    </button>
    <p class="text-model-probe__status" :class="statusClass">
      {{ statusText }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { probeTextAnalysisModel } from "@/api/generation";
import { IconCheck, IconLoading, IconRefresh } from "@/components/icons";
import type { ProbeTextAnalysisModelResponse } from "@/types";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    disabled?: boolean;
  }>(),
  {
    disabled: false,
  },
);

const probeState = ref<"idle" | "loading" | "success" | "error">("idle");
const checkedModel = ref("");
const errorMessage = ref("");
const probeResult = ref<ProbeTextAnalysisModelResponse | null>(null);
const probeToken = ref(0);

const normalizedModel = computed(() => props.modelValue.trim());
const isCurrentModelReady = computed(
  () => probeState.value === "success" && checkedModel.value === normalizedModel.value,
);
const buttonDisabled = computed(() => props.disabled || probeState.value === "loading" || !normalizedModel.value);
const buttonLabel = computed(() => {
  if (probeState.value === "loading") {
    return "测试中";
  }
  if (isCurrentModelReady.value) {
    return "重测";
  }
  return "测试";
});
const statusClass = computed(() => {
  if (probeState.value === "success") {
    return "text-model-probe__status-success";
  }
  if (probeState.value === "error") {
    return "text-model-probe__status-error";
  }
  return "text-model-probe__status-idle";
});
const statusText = computed(() => {
  if (probeState.value === "loading") {
    return "测试中";
  }
  if (probeState.value === "success" && probeResult.value) {
    const provider = probeResult.value.provider || "provider";
    const latency = Number.isFinite(probeResult.value.latencyMs) ? `${probeResult.value.latencyMs} ms` : "";
    return `${provider} 已连通${latency ? ` · ${latency}` : ""}`;
  }
  if (probeState.value === "error") {
    return errorMessage.value || "模型测试失败";
  }
  return "提交前会自动校验";
});

function reset() {
  probeToken.value += 1;
  probeState.value = "idle";
  checkedModel.value = "";
  errorMessage.value = "";
  probeResult.value = null;
}

watch(normalizedModel, () => {
  reset();
});

async function ensureReady(force = false) {
  const currentModel = normalizedModel.value;
  if (!currentModel) {
    probeState.value = "error";
    errorMessage.value = "请先选择文本模型";
    return false;
  }
  if (!force && isCurrentModelReady.value) {
    return true;
  }
  const token = probeToken.value + 1;
  probeToken.value = token;
  probeState.value = "loading";
  errorMessage.value = "";
  try {
    const response = await probeTextAnalysisModel({ textAnalysisModel: currentModel });
    if (probeToken.value !== token) {
      return false;
    }
    probeResult.value = response;
    checkedModel.value = currentModel;
    probeState.value = "success";
    return true;
  } catch (error) {
    if (probeToken.value !== token) {
      return false;
    }
    checkedModel.value = currentModel;
    probeState.value = "error";
    errorMessage.value = error instanceof Error ? error.message : "模型测试失败";
    probeResult.value = null;
    return false;
  }
}

async function handleProbe() {
  await ensureReady(true);
}

defineExpose<TextModelProbeInlineExpose>({
  ensureReady,
  reset,
});
</script>

<style scoped>
.text-model-probe {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.text-model-probe__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 40px;
  border: 1px solid var(--surface-border-strong);
  border-radius: 10px;
  background: var(--bg-surface);
  color: var(--accent-blue);
  font-size: 0.76rem;
  font-weight: 800;
  line-height: 1;
  padding: 0 10px;
  transition:
    border-color 160ms ease,
    background 160ms ease,
    color 160ms ease;
}

.text-model-probe__button:hover:not(:disabled) {
  border-color: rgba(99, 102, 241, 0.22);
  background: var(--bg-accent-soft);
}

.text-model-probe__button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.text-model-probe__status {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.45;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-model-probe__status-idle {
  color: #64748b;
}

.text-model-probe__status-success {
  color: #047857;
}

.text-model-probe__status-error {
  color: #be123c;
}
</style>

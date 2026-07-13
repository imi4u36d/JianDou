<template>
  <template v-if="executionMode === 'auto' || executionMode === 'manual'">
    <div v-if="autoPilot.isRunning.value" class="autopilot-bar autopilot-bar-running surface-panel">
      <div class="autopilot-bar__status">
        <span class="autopilot-bar__dot autopilot-bar__dot-running"></span>
        <strong>{{ autoPilot.currentTask.value || "自动执行中" }}</strong>
      </div>
      <StatusLog :entries="recentLog" active />
      <div class="autopilot-bar__actions">
        <button class="jd-button jd-button--secondary jd-button--sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.pauseAutoPilot()">⏸ 暂停</button>
        <button class="jd-button jd-button--secondary jd-button--sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.terminateAutoPilot()">⏹ 终止</button>
      </div>
    </div>

    <div v-else-if="autoPilot.isQueued.value" class="autopilot-bar autopilot-bar-queued surface-panel">
      <div class="autopilot-bar__status">
        <span class="autopilot-bar__dot autopilot-bar__dot-queued"></span>
        <strong>排队中</strong>
        <span v-if="queuePosition" class="autopilot-bar__queue-info">前面还有 {{ queuePosition - 1 }} 个任务</span>
      </div>
      <StatusLog :entries="recentLog" active />
      <div class="autopilot-bar__actions">
        <button class="jd-button jd-button--secondary jd-button--sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.terminateAutoPilot()">取消</button>
      </div>
    </div>

    <div v-else-if="autoPilot.isPaused.value" class="autopilot-bar autopilot-bar-paused surface-panel">
      <div class="autopilot-bar__status"><span class="autopilot-bar__dot autopilot-bar__dot-paused"></span><strong>已暂停</strong></div>
      <StatusLog :entries="recentLog" />
      <div class="autopilot-bar__actions">
        <button class="jd-button jd-button--primary jd-button--sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.resumeAutoPilot()">▶ 继续自动执行</button>
        <button class="jd-button jd-button--secondary jd-button--sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.terminateAutoPilot()">✏ 切换为手动模式</button>
      </div>
    </div>

    <div v-else-if="autoPilot.isFailed.value" class="autopilot-bar autopilot-bar-failed surface-panel">
      <div class="autopilot-bar__status"><span class="autopilot-bar__dot autopilot-bar__dot-failed"></span><strong>自动执行失败</strong></div>
      <StatusLog :entries="recentLog" />
      <div class="autopilot-bar__actions">
        <button class="jd-button jd-button--primary jd-button--sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.resumeAutoPilot()">重试</button>
      </div>
    </div>

    <div v-else class="autopilot-bar autopilot-bar-idle surface-panel">
      <div class="autopilot-bar__status"><strong>自动执行就绪</strong><span class="autopilot-bar__hint">点击启动后，工作流将自动依次执行各阶段。</span></div>
      <StatusLog :entries="recentLog" />
      <div class="autopilot-bar__actions">
        <button class="jd-button jd-button--primary jd-button--sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.startAutoPilot()">▶ 启动自动执行</button>
      </div>
    </div>
  </template>
</template>

<script setup lang="ts">
import { defineComponent, h, type PropType } from "vue";
import { useAutoPilot } from "@/composables/workflow/useAutoPilot";

type AutoPilot = ReturnType<typeof useAutoPilot>;
type StatusEntry = AutoPilot["statusLog"]["value"][number];

defineProps<{
  autoPilot: AutoPilot;
  executionMode: string;
  queuePosition?: number | null;
  recentLog: StatusEntry[];
}>();

const StatusLog = defineComponent({
  props: {
    entries: { type: Array as PropType<StatusEntry[]>, required: true },
    active: { type: Boolean, default: false },
  },
  setup(props) {
    return () => h("div", { class: "autopilot-bar__log" }, props.entries.map((entry) =>
      h("div", { class: ["autopilot-log-entry", props.active && "autopilot-log-entry--active"] }, [
        h("span", { class: ["autopilot-log-entry__stage", entry.stateKey && `autopilot-log-entry__stage--${entry.stateKey}`] }, entry.stage),
        h("span", { class: "autopilot-log-entry__message" }, entry.message),
      ])
    ));
  },
});
</script>

<style src="./workflow-auto-pilot-bar.css"></style>

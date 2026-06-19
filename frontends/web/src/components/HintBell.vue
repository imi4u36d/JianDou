<template>
  <div ref="root" class="relative inline-flex" @mouseenter="handleEnter" @mouseleave="handleLeave">
    <button
      type="button"
      class="hint-bell"
      :class="pinned ? 'hint-bell-active' : ''"
      :aria-expanded="visible ? 'true' : 'false'"
      :aria-label="title || '查看提示'"
      @click="toggle"
    >
      <IconBell />
      <span v-if="pinned" class="hint-bell-dot"></span>
    </button>
  </div>

  <Teleport to="body">
    <transition name="hint-fade">
      <div
        v-if="visible"
        ref="popover"
        class="hint-popover"
        :style="popoverStyle"
        @mouseenter="handleEnter"
        @mouseleave="handleLeave"
      >
        <p v-if="title" class="hint-title">{{ title }}</p>
        <p v-if="text" class="hint-text">{{ text }}</p>
        <ul v-if="items.length" class="hint-list">
          <li v-for="item in items" :key="item">{{ item }}</li>
        </ul>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 提示组件。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { IconBell } from "@/components/icons";

const props = withDefaults(
  defineProps<{
    title?: string;
    text?: string;
    items?: string[];
    align?: "left" | "right";
    maxWidth?: number;
  }>(),
  {
    title: "",
    text: "",
    items: () => [],
    align: "right",
    maxWidth: 288
  }
);

const root = ref<HTMLElement | null>(null);
const popover = ref<HTMLElement | null>(null);
const pinned = ref(false);
const hovering = ref(false);
let listenersBound = false;
const popoverStyle = ref<Record<string, string>>({
  top: "0px",
  left: "0px",
});
const visible = computed(() => pinned.value || hovering.value);
let leaveTimer: number | null = null;

/**
 * 处理切换。
 */
function toggle() {
  pinned.value = !pinned.value;
}

/**
 * 处理处理Enter。
 */
function handleEnter() {
  clearLeaveTimer();
  hovering.value = true;
}

/**
 * 处理处理Leave。
 */
function handleLeave() {
  clearLeaveTimer();
  leaveTimer = window.setTimeout(() => {
    hovering.value = false;
    leaveTimer = null;
  }, 120);
}

/**
 * 处理处理Pointer。
 * @param event 事件名称
 */
function handlePointer(event: MouseEvent) {
  if (
    (root.value && root.value.contains(event.target as Node)) ||
    (popover.value && popover.value.contains(event.target as Node))
  ) {
    return;
  }
  pinned.value = false;
  hovering.value = false;
}

/**
 * 处理处理Escape。
 * @param event 事件名称
 */
function handleEscape(event: KeyboardEvent) {
  if (event.key === "Escape") {
    pinned.value = false;
    hovering.value = false;
  }
}

/**
 * 处理bindDocumentListeners。
 */
function bindDocumentListeners() {
  if (listenersBound) {
    return;
  }
  document.addEventListener("mousedown", handlePointer);
  document.addEventListener("keydown", handleEscape);
  window.addEventListener("resize", syncPopoverPosition);
  window.addEventListener("scroll", syncPopoverPosition, true);
  listenersBound = true;
}

/**
 * 处理unbindDocumentListeners。
 */
function unbindDocumentListeners() {
  if (!listenersBound) {
    return;
  }
  document.removeEventListener("mousedown", handlePointer);
  document.removeEventListener("keydown", handleEscape);
  window.removeEventListener("resize", syncPopoverPosition);
  window.removeEventListener("scroll", syncPopoverPosition, true);
  listenersBound = false;
}

function clearLeaveTimer() {
  if (leaveTimer !== null) {
    window.clearTimeout(leaveTimer);
    leaveTimer = null;
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

async function syncPopoverPosition() {
  if (!visible.value || !root.value) {
    return;
  }
  const rect = root.value.getBoundingClientRect();
  const viewportPadding = 12;
  const preferredWidth = Math.max(220, props.maxWidth);
  const maxWidth = Math.min(preferredWidth, window.innerWidth - viewportPadding * 2);
  let left =
    props.align === "left"
      ? rect.left
      : rect.right - maxWidth;
  left = clamp(left, viewportPadding, window.innerWidth - maxWidth - viewportPadding);

  let top = rect.bottom + 12;
  popoverStyle.value = {
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
    width: `${Math.round(maxWidth)}px`,
    maxWidth: `${Math.round(maxWidth)}px`,
  };

  await nextTick();
  const popoverHeight = popover.value?.offsetHeight ?? 0;
  if (top + popoverHeight > window.innerHeight - viewportPadding) {
    top = rect.top - popoverHeight - 12;
    if (top < viewportPadding) {
      top = viewportPadding;
    }
    popoverStyle.value = {
      top: `${Math.round(top)}px`,
      left: `${Math.round(left)}px`,
      width: `${Math.round(maxWidth)}px`,
      maxWidth: `${Math.round(maxWidth)}px`,
    };
  }
}

watch(
  visible,
  async (nextVisible) => {
    if (!nextVisible) {
      unbindDocumentListeners();
      return;
    }
    bindDocumentListeners();
    await nextTick();
    await syncPopoverPosition();
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  clearLeaveTimer();
  unbindDocumentListeners();
});

</script>

<style scoped>
.hint-bell {
  position: relative;
  z-index: 24;
  display: inline-flex;
  height: 34px;
  width: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.74);
  color: var(--text-muted);
  border: 1px solid rgba(15, 20, 25, 0.08);
  box-shadow: none;
  transition:
    background 180ms ease,
    color 180ms ease,
    transform 180ms ease,
    box-shadow 180ms ease;
}

.hint-bell:hover,
.hint-bell:focus-visible {
  transform: translateY(-1px);
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(27, 124, 255, 0.07);
}

.hint-bell-active {
  border-color: rgba(27, 124, 255, 0.18);
  background: linear-gradient(135deg, rgba(239, 252, 255, 0.98), rgba(237, 245, 255, 0.94));
  color: var(--accent-blue);
}

.hint-bell svg {
  height: 1rem;
  width: 1rem;
}

.hint-bell-dot {
  position: absolute;
  right: 7px;
  top: 7px;
  height: 6px;
  width: 6px;
  border-radius: 9999px;
  background: var(--accent-coral);
  box-shadow: 0 0 0 2px #fff;
}

.hint-popover {
  position: fixed;
  z-index: 4200;
  width: min(18rem, calc(100vw - 1.5rem));
  border-radius: 16px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(249, 252, 253, 0.98));
  padding: 12px;
  color: var(--text-strong);
  box-shadow:
    0 18px 42px rgba(15, 20, 25, 0.11),
    0 2px 8px rgba(18, 28, 33, 0.04);
  backdrop-filter: blur(18px);
}

.hint-title {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 820;
  letter-spacing: 0;
  color: var(--text-strong);
}

.hint-text {
  margin: 8px 0 0;
  max-height: min(58vh, 32rem);
  overflow: auto;
  font-size: 0.86rem;
  line-height: 1.65;
  color: var(--text-body);
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.hint-list {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--text-body);
  font-size: 0.86rem;
}

.hint-list li {
  margin-top: 0.35rem;
  line-height: 1.5;
}

.hint-fade-enter-active,
.hint-fade-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.hint-fade-enter-from,
.hint-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}
</style>

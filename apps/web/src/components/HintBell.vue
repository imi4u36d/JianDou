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
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M15 17H9a2 2 0 0 1-2-2v-3.2c0-1.5-.4-2.9-1.2-4.2A5.9 5.9 0 0 1 11 4h2a5.9 5.9 0 0 1 5.2 3.6c.5 1 .8 2.1.8 3.2V15a2 2 0 0 1-2 2Z" />
        <path d="M10 20a2.5 2.5 0 0 0 4 0" />
      </svg>
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

const props = withDefaults(
  defineProps<{
    title?: string;
    text?: string;
    items?: string[];
    align?: "left" | "right";
  }>(),
  {
    title: "",
    text: "",
    items: () => [],
    align: "right"
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
  const maxWidth = Math.min(288, window.innerWidth - viewportPadding * 2);
  let left =
    props.align === "left"
      ? rect.left
      : rect.right - maxWidth;
  left = clamp(left, viewportPadding, window.innerWidth - maxWidth - viewportPadding);

  let top = rect.bottom + 12;
  popoverStyle.value = {
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
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
  height: 2rem;
  width: 2rem;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: var(--shadow-soft);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease;
}

.hint-bell:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-glow);
}

.hint-bell-active {
  border-color: rgba(145, 180, 255, 0.32);
  background: rgba(176, 92, 255, 0.12);
}

.hint-bell svg {
  height: 1rem;
  width: 1rem;
}

.hint-bell-dot {
  position: absolute;
  right: 0.28rem;
  top: 0.28rem;
  height: 0.32rem;
  width: 0.32rem;
  border-radius: 9999px;
  background: #4edbff;
  box-shadow: 0 0 0 2px rgba(11, 14, 20, 0.9);
}

.hint-popover {
  position: fixed;
  z-index: 4200;
  width: min(18rem, calc(100vw - 1.5rem));
  border-radius: 1rem;
  border: 1px solid rgba(145, 180, 255, 0.18);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)),
    rgba(10, 13, 20, 0.96);
  padding: 0.95rem 1rem;
  color: var(--text-strong);
  box-shadow: var(--shadow-panel);
  backdrop-filter: blur(18px);
}

.hint-title {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.hint-text {
  margin: 0.55rem 0 0;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-body);
}

.hint-list {
  margin: 0.6rem 0 0;
  padding-left: 1rem;
  color: var(--text-body);
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

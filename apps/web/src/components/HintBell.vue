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

    <transition name="hint-fade">
      <div v-if="visible" class="hint-popover" :class="alignClass">
        <p v-if="title" class="hint-title">{{ title }}</p>
        <p v-if="text" class="hint-text">{{ text }}</p>
        <ul v-if="items.length" class="hint-list">
          <li v-for="item in items" :key="item">{{ item }}</li>
        </ul>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

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
const pinned = ref(false);
const hovering = ref(false);
const visible = computed(() => pinned.value || hovering.value);

const alignClass = computed(() => (props.align === "left" ? "left-0 origin-top-left" : "right-0 origin-top-right"));

function toggle() {
  pinned.value = !pinned.value;
}

function handleEnter() {
  hovering.value = true;
}

function handleLeave() {
  hovering.value = false;
}

function handlePointer(event: MouseEvent) {
  if (!root.value || root.value.contains(event.target as Node)) {
    return;
  }
  pinned.value = false;
  hovering.value = false;
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === "Escape") {
    pinned.value = false;
    hovering.value = false;
  }
}

function bindDocumentListeners() {
  document.addEventListener("mousedown", handlePointer);
  document.addEventListener("keydown", handleEscape);
}

function unbindDocumentListeners() {
  document.removeEventListener("mousedown", handlePointer);
  document.removeEventListener("keydown", handleEscape);
}

watch(
  pinned,
  (nextPinned) => {
    if (nextPinned) {
      bindDocumentListeners();
      return;
    }
    unbindDocumentListeners();
  },
  { flush: "post" }
);

onBeforeUnmount(() => {
  unbindDocumentListeners();
});
</script>

<style scoped>
.hint-bell {
  display: inline-flex;
  height: 2rem;
  width: 2rem;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #475569;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    color 180ms ease;
}

.hint-bell:hover {
  transform: translateY(-1px);
  color: #0f172a;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
}

.hint-bell-active {
  color: #0f172a;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.14);
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
  background: #0891b2;
  box-shadow: 0 0 0 2px #f8fafc;
}

.hint-popover {
  position: absolute;
  top: calc(100% + 0.7rem);
  z-index: 30;
  width: min(18rem, calc(100vw - 3rem));
  border-radius: 1rem;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  padding: 0.95rem 1rem;
  color: #0f172a;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.16);
}

.hint-title {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #475569;
}

.hint-text {
  margin: 0.55rem 0 0;
  font-size: 0.9rem;
  line-height: 1.6;
  color: #334155;
}

.hint-list {
  margin: 0.6rem 0 0;
  padding-left: 1rem;
  color: #334155;
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

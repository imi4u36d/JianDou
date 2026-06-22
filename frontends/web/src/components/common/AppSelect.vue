<template>
  <div
    ref="root"
    class="app-select"
    :class="[
      `app-select--${variant}`,
      compact ? 'app-select--compact' : '',
      open ? 'app-select--open' : '',
      disabled ? 'app-select--disabled' : '',
    ]"
  >
    <button
      :id="triggerId"
      ref="trigger"
      type="button"
      class="app-select__trigger"
      :aria-controls="menuId"
      :aria-expanded="open ? 'true' : 'false'"
      aria-haspopup="listbox"
      :disabled="disabled"
      @click="toggleOpen"
      @keydown="handleTriggerKeydown"
    >
      <span v-if="prefix" class="app-select__prefix">{{ prefix }}</span>
      <span class="app-select__label" :class="{ 'app-select__label-placeholder': !selectedOption }">
        {{ selectedOption?.label || placeholder }}
      </span>
      <span class="app-select__chevron"><IconChevronDown size="xs" /></span>
    </button>
  </div>

  <Teleport to="body">
    <transition name="app-select-backdrop-fade">
      <button
        v-if="open"
        type="button"
        class="app-select__backdrop"
        aria-label="关闭选项"
        @click="closeMenu"
      ></button>
    </transition>
    <transition name="app-select-fade">
      <div
        v-if="open"
        :id="menuId"
        ref="menu"
        class="app-select__menu"
        :class="`app-select__menu--${variant}`"
        :style="menuStyle"
        role="listbox"
        :aria-labelledby="triggerId"
        tabindex="-1"
        @keydown="handleMenuKeydown"
      >
        <button
          v-for="(option, index) in options"
          :key="optionKey(option, index)"
          type="button"
          class="app-select__option"
          :class="[
            isSelected(option) ? 'app-select__option-selected' : '',
            highlightedIndex === index ? 'app-select__option-highlighted' : '',
            option.disabled ? 'app-select__option-disabled' : '',
          ]"
          role="option"
          :aria-selected="isSelected(option) ? 'true' : 'false'"
          :disabled="option.disabled"
          :data-index="index"
          @click="selectOption(option)"
          @mouseenter="highlightedIndex = index"
        >
          <span class="app-select__option-copy">
            <span class="app-select__option-label">{{ option.label }}</span>
            <span v-if="option.description" class="app-select__option-description">{{ option.description }}</span>
          </span>
          <span v-if="isSelected(option)" class="app-select__check"><IconCheck size="xs" /></span>
        </button>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import type { AppSelectOption } from "./app-select";
import { IconChevronDown, IconCheck } from "@/components/icons";

const props = withDefaults(
  defineProps<{
    modelValue: unknown;
    options: AppSelectOption[];
    placeholder?: string;
    disabled?: boolean;
    compact?: boolean;
    variant?: "field" | "toolbar" | "admin";
    prefix?: string;
  }>(),
  {
    placeholder: "请选择",
    disabled: false,
    compact: false,
    variant: "field",
    prefix: "",
  },
);

const emit = defineEmits<{
  (event: "update:modelValue", value: unknown): void;
}>();

const root = ref<HTMLElement | null>(null);
const trigger = ref<HTMLButtonElement | null>(null);
const menu = ref<HTMLElement | null>(null);
const open = ref(false);
const highlightedIndex = ref(-1);
const menuStyle = ref<Record<string, string>>({});
const instanceId = `app-select-${Math.random().toString(36).slice(2, 10)}`;
const triggerId = `${instanceId}-trigger`;
const menuId = `${instanceId}-menu`;
let listenersBound = false;

const selectedIndex = computed(() => props.options.findIndex((option) => Object.is(option.value, props.modelValue)));
const selectedOption = computed(() => props.options[selectedIndex.value] ?? null);

function optionKey(option: AppSelectOption, index: number) {
  const primitive = typeof option.value;
  if (primitive === "string" || primitive === "number" || primitive === "boolean") {
    return `${primitive}:${String(option.value)}`;
  }
  if (option.value === null) {
    return `null:${index}`;
  }
  return `${option.label}:${index}`;
}

function isSelected(option: AppSelectOption) {
  return Object.is(option.value, props.modelValue);
}

function findNextEnabledIndex(start: number, direction: 1 | -1) {
  if (!props.options.length) {
    return -1;
  }
  let index = start;
  for (let count = 0; count < props.options.length; count += 1) {
    index = (index + direction + props.options.length) % props.options.length;
    if (!props.options[index]?.disabled) {
      return index;
    }
  }
  return -1;
}

function syncHighlightedOptionIntoView() {
  if (!menu.value || highlightedIndex.value < 0) {
    return;
  }
  const option = menu.value.querySelector<HTMLElement>(`[data-index="${highlightedIndex.value}"]`);
  option?.scrollIntoView({ block: "nearest" });
}

async function syncMenuPosition() {
  if (!open.value || !trigger.value) {
    return;
  }
  if (window.innerWidth <= 640) {
    menuStyle.value = {
      left: "14px",
      right: "14px",
      bottom: "14px",
      width: "auto",
      maxHeight: `${Math.round(Math.min(430, window.innerHeight * 0.62))}px`,
    };
    return;
  }
  const rect = trigger.value.getBoundingClientRect();
  const viewportPadding = 12;
  const width = Math.max(rect.width, props.variant === "toolbar" ? 180 : rect.width);
  let left = rect.left;
  if (left + width > window.innerWidth - viewportPadding) {
    left = window.innerWidth - width - viewportPadding;
  }
  left = Math.max(viewportPadding, left);

  let top = rect.bottom + 8;
  menuStyle.value = {
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
    width: `${Math.round(width)}px`,
    maxHeight: `${Math.round(Math.min(340, window.innerHeight - viewportPadding * 2))}px`,
  };

  await nextTick();
  const menuHeight = menu.value?.offsetHeight ?? 0;
  if (top + menuHeight > window.innerHeight - viewportPadding) {
    top = Math.max(viewportPadding, rect.top - menuHeight - 8);
    menuStyle.value = {
      top: `${Math.round(top)}px`,
      left: `${Math.round(left)}px`,
      width: `${Math.round(width)}px`,
      maxHeight: `${Math.round(Math.min(340, window.innerHeight - viewportPadding * 2))}px`,
    };
  }
}

function bindListeners() {
  if (listenersBound) {
    return;
  }
  document.addEventListener("mousedown", handleDocumentPointer);
  document.addEventListener("keydown", handleDocumentKeydown);
  window.addEventListener("resize", syncMenuPosition);
  window.addEventListener("scroll", syncMenuPosition, true);
  listenersBound = true;
}

function unbindListeners() {
  if (!listenersBound) {
    return;
  }
  document.removeEventListener("mousedown", handleDocumentPointer);
  document.removeEventListener("keydown", handleDocumentKeydown);
  window.removeEventListener("resize", syncMenuPosition);
  window.removeEventListener("scroll", syncMenuPosition, true);
  listenersBound = false;
}

function handleDocumentPointer(event: MouseEvent) {
  const target = event.target as Node;
  if ((root.value && root.value.contains(target)) || (menu.value && menu.value.contains(target))) {
    return;
  }
  closeMenu();
}

function handleDocumentKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    closeMenu();
    trigger.value?.focus();
  }
}

async function openMenu() {
  if (props.disabled || !props.options.length) {
    return;
  }
  open.value = true;
  highlightedIndex.value = selectedIndex.value >= 0 && !props.options[selectedIndex.value]?.disabled
    ? selectedIndex.value
    : findNextEnabledIndex(-1, 1);
  bindListeners();
  await nextTick();
  await syncMenuPosition();
  syncHighlightedOptionIntoView();
  menu.value?.focus();
}

function closeMenu() {
  open.value = false;
  highlightedIndex.value = -1;
  unbindListeners();
}

function toggleOpen() {
  if (open.value) {
    closeMenu();
    return;
  }
  void openMenu();
}

function selectOption(option: AppSelectOption) {
  if (option.disabled) {
    return;
  }
  emit("update:modelValue", option.value);
  closeMenu();
  trigger.value?.focus();
}

function moveHighlight(direction: 1 | -1) {
  const nextIndex = findNextEnabledIndex(highlightedIndex.value >= 0 ? highlightedIndex.value : -1, direction);
  if (nextIndex >= 0) {
    highlightedIndex.value = nextIndex;
    syncHighlightedOptionIntoView();
  }
}

function handleTriggerKeydown(event: KeyboardEvent) {
  if (props.disabled) {
    return;
  }
  if (event.key === "ArrowDown") {
    event.preventDefault();
    if (!open.value) {
      void openMenu();
      return;
    }
    moveHighlight(1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    if (!open.value) {
      void openMenu();
      return;
    }
    moveHighlight(-1);
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    if (!open.value) {
      void openMenu();
      return;
    }
    if (highlightedIndex.value >= 0) {
      selectOption(props.options[highlightedIndex.value]);
    }
  } else if (event.key === "Escape") {
    closeMenu();
  }
}

function handleMenuKeydown(event: KeyboardEvent) {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    moveHighlight(1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    moveHighlight(-1);
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    if (highlightedIndex.value >= 0) {
      selectOption(props.options[highlightedIndex.value]);
    }
  } else if (event.key === "Escape") {
    event.preventDefault();
    closeMenu();
    trigger.value?.focus();
  } else if (event.key === "Tab") {
    closeMenu();
  }
}

watch(
  () => props.modelValue,
  () => {
    if (!open.value) {
      return;
    }
    highlightedIndex.value = selectedIndex.value;
  },
);

watch(
  () => props.options,
  () => {
    if (!open.value) {
      return;
    }
    void syncMenuPosition();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  unbindListeners();
});
</script>

<style scoped>
.app-select {
  position: relative;
  width: 100%;
}

.app-select--toolbar {
  width: auto;
  min-width: 176px;
}

.app-select--admin {
  width: 100%;
}

.app-select__trigger {
  width: 100%;
  border: 0;
  cursor: pointer;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease,
    transform 180ms ease;
}

.app-select__trigger:disabled {
  cursor: not-allowed;
}

.app-select--field .app-select__trigger {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 46px;
  padding: 0.86rem 1rem;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(0, 0, 0, 0.03);
  box-shadow: none;
}

.app-select--field.app-select--compact .app-select__trigger {
  min-height: 44px;
  padding: 0.72rem 0.86rem;
  border-radius: var(--radius-sm);
}

.app-select--field .app-select__trigger:hover:not(:disabled) {
  border-color: rgba(90, 200, 250, 0.3);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.app-select--field.app-select--open .app-select__trigger,
.app-select--field .app-select__trigger:focus-visible {
  border-color: rgba(90, 200, 250, 0.5);
  box-shadow:
    0 0 0 3px rgba(90, 200, 250, 0.15),
    0 10px 26px rgba(0, 0, 0, 0.2);
}

.app-select--field.app-select--disabled .app-select__trigger {
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.02);
  opacity: 0.6;
}

.app-select--toolbar .app-select__trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 13px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-strong);
}

.app-select--toolbar.app-select--open .app-select__trigger,
.app-select--toolbar .app-select__trigger:hover:not(:disabled) {
  border-color: rgba(90, 200, 250, 0.3);
  background: rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.15);
}

.app-select--admin .app-select__trigger {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 44px;
  padding: 0.78rem 0.95rem;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.7);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-strong);
}

.app-select--admin .app-select__trigger:hover:not(:disabled) {
  border-color: rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.15);
}

.app-select--admin.app-select--open .app-select__trigger,
.app-select--admin .app-select__trigger:focus-visible {
  border-color: rgba(90, 200, 250, 0.5);
  box-shadow:
    0 0 0 3px rgba(90, 200, 250, 0.12),
    0 10px 22px rgba(0, 0, 0, 0.2);
}

.app-select--admin.app-select--disabled .app-select__trigger {
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.02);
  opacity: 0.6;
}

.app-select__prefix {
  flex: 0 0 auto;
  color: var(--text-muted);
}

.app-select__label {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  color: var(--text-strong);
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-select--field .app-select__label {
  font-size: 1rem;
}

.app-select--field.app-select--compact .app-select__label {
  font-size: 0.96rem;
}

.app-select--toolbar .app-select__label {
  color: inherit;
  font-size: 0.86rem;
}

.app-select--admin .app-select__label {
  color: var(--text-strong);
  font-size: 0.92rem;
}

.app-select--admin .app-select__label-placeholder {
  color: var(--text-muted);
}

.app-select--admin .app-select__chevron {
  color: var(--text-muted);
}

.app-select__label-placeholder {
  color: var(--text-muted);
}

.app-select__chevron {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
  color: var(--text-muted);
  transition: transform 180ms ease;
}

.app-select__chevron path {
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.app-select--open .app-select__chevron {
  transform: rotate(180deg);
}

.app-select__menu {
  position: fixed;
  z-index: 1400;
  overflow: auto;
  padding: 7px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(40px) saturate(1.8);
  -webkit-backdrop-filter: blur(40px) saturate(1.8);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.app-select__backdrop {
  display: none;
}

.app-select__menu--admin {
  border-color: rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.1);
}

.app-select__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-strong);
  text-align: left;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    transform 160ms ease;
}

.app-select__option:hover:not(:disabled),
.app-select__option-highlighted {
  border-color: rgba(90, 200, 250, 0.2);
  background: rgba(90, 200, 250, 0.1);
}

.app-select__option-selected {
  border-color: rgba(90, 200, 250, 0.25);
  background: rgba(90, 200, 250, 0.15);
  color: var(--accent-blue);
}

.app-select__menu--admin .app-select__option {
  color: var(--text-strong);
}

.app-select__menu--admin .app-select__option:hover:not(:disabled),
.app-select__menu--admin .app-select__option-highlighted {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.1);
}

.app-select__menu--admin .app-select__option-selected {
  border-color: rgba(90, 200, 250, 0.3);
  background: rgba(90, 200, 250, 0.15);
}

.app-select__option-disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

.app-select__option-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
  flex: 1 1 auto;
}

.app-select__option-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-select__option-description {
  color: var(--text-muted);
  font-size: 0.78rem;
  line-height: 1.4;
  white-space: normal;
}

.app-select__menu--admin .app-select__option-description {
  color: var(--text-muted);
}

.app-select__check {
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  color: var(--accent-blue);
}

.app-select__menu--admin .app-select__check {
  color: var(--accent-blue);
}

.app-select__check path {
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.app-select-fade-enter-active,
.app-select-fade-leave-active {
  transition: opacity 140ms ease, transform 140ms ease;
}

.app-select-fade-enter-from,
.app-select-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.app-select-backdrop-fade-enter-active,
.app-select-backdrop-fade-leave-active {
  transition: opacity 140ms ease;
}

.app-select-backdrop-fade-enter-from,
.app-select-backdrop-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .app-select__backdrop {
    position: fixed;
    inset: 0;
    z-index: 1390;
    display: block;
    border: 0;
    background: rgba(10, 10, 20, 0.2);
    backdrop-filter: blur(40px) saturate(2.0) saturate(1.5);
  }

  .app-select__menu {
    z-index: 1400;
    padding: 20px 10px 10px;
    border-radius: var(--radius-lg);
    box-shadow:
      0 -18px 46px rgba(0, 0, 0, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.9);
  }

  .app-select__menu::before {
    content: "";
    display: block;
    width: 38px;
    height: 4px;
    margin: -9px auto 8px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.2);
  }

  .app-select__option {
    min-height: 46px;
    border-radius: var(--radius-sm);
  }

  .app-select-fade-enter-from,
  .app-select-fade-leave-to {
    transform: translateY(14px);
  }
}
</style>

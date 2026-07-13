import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import type { AppSelectOption, AppSelectProps } from "./app-select";

type ResolvedAppSelectProps = Readonly<AppSelectProps & {
  disabled: boolean;
  variant: "field" | "toolbar" | "admin";
}>;

export function useAppSelectInteraction(
  props: ResolvedAppSelectProps,
  emitValue: (value: unknown) => void,
) {
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

  const selectedIndex = computed(() =>
    props.options.findIndex((option) => Object.is(option.value, props.modelValue)),
  );
  const selectedOption = computed(() => props.options[selectedIndex.value] ?? null);

  function optionKey(option: AppSelectOption, index: number) {
    const primitive = typeof option.value;
    if (primitive === "string" || primitive === "number" || primitive === "boolean") {
      return `${primitive}:${String(option.value)}`;
    }
    return option.value === null ? `null:${index}` : `${option.label}:${index}`;
  }

  function isSelected(option: AppSelectOption) {
    return Object.is(option.value, props.modelValue);
  }

  function findNextEnabledIndex(start: number, direction: 1 | -1) {
    if (!props.options.length) return -1;
    let index = start;
    for (let count = 0; count < props.options.length; count += 1) {
      index = (index + direction + props.options.length) % props.options.length;
      if (!props.options[index]?.disabled) return index;
    }
    return -1;
  }

  function syncHighlightedOptionIntoView() {
    if (!menu.value || highlightedIndex.value < 0) return;
    menu.value
      .querySelector<HTMLElement>(`[data-index="${highlightedIndex.value}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }

  function positionedStyle(top: number, left: number, width: number, viewportPadding: number) {
    return {
      top: `${Math.round(top)}px`,
      left: `${Math.round(left)}px`,
      width: `${Math.round(width)}px`,
      maxHeight: `${Math.round(Math.min(340, window.innerHeight - viewportPadding * 2))}px`,
    };
  }

  async function syncMenuPosition() {
    if (!open.value || !trigger.value) return;
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
    let left = Math.min(rect.left, window.innerWidth - width - viewportPadding);
    left = Math.max(viewportPadding, left);
    let top = rect.bottom + 8;
    menuStyle.value = positionedStyle(top, left, width, viewportPadding);
    await nextTick();
    const menuHeight = menu.value?.offsetHeight ?? 0;
    if (top + menuHeight > window.innerHeight - viewportPadding) {
      top = Math.max(viewportPadding, rect.top - menuHeight - 8);
      menuStyle.value = positionedStyle(top, left, width, viewportPadding);
    }
  }

  function closeMenu() {
    open.value = false;
    highlightedIndex.value = -1;
    unbindListeners();
  }

  function handleDocumentPointer(event: MouseEvent) {
    const target = event.target as Node;
    if (root.value?.contains(target) || menu.value?.contains(target)) return;
    closeMenu();
  }

  function handleDocumentKeydown(event: KeyboardEvent) {
    if (event.key !== "Escape") return;
    closeMenu();
    trigger.value?.focus();
  }

  function bindListeners() {
    if (listenersBound) return;
    document.addEventListener("mousedown", handleDocumentPointer);
    document.addEventListener("keydown", handleDocumentKeydown);
    window.addEventListener("resize", syncMenuPosition);
    window.addEventListener("scroll", syncMenuPosition, true);
    listenersBound = true;
  }

  function unbindListeners() {
    if (!listenersBound) return;
    document.removeEventListener("mousedown", handleDocumentPointer);
    document.removeEventListener("keydown", handleDocumentKeydown);
    window.removeEventListener("resize", syncMenuPosition);
    window.removeEventListener("scroll", syncMenuPosition, true);
    listenersBound = false;
  }

  async function openMenu() {
    if (props.disabled || !props.options.length) return;
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

  function toggleOpen() {
    if (open.value) closeMenu();
    else void openMenu();
  }

  function selectOption(option: AppSelectOption) {
    if (option.disabled) return;
    emitValue(option.value);
    closeMenu();
    trigger.value?.focus();
  }

  function moveHighlight(direction: 1 | -1) {
    const nextIndex = findNextEnabledIndex(
      highlightedIndex.value >= 0 ? highlightedIndex.value : -1,
      direction,
    );
    if (nextIndex < 0) return;
    highlightedIndex.value = nextIndex;
    syncHighlightedOptionIntoView();
  }

  function handleTriggerKeydown(event: KeyboardEvent) {
    if (props.disabled) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open.value) void openMenu();
      else moveHighlight(event.key === "ArrowDown" ? 1 : -1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (!open.value) void openMenu();
      else if (highlightedIndex.value >= 0) selectOption(props.options[highlightedIndex.value]);
    } else if (event.key === "Escape") closeMenu();
  }

  function handleMenuKeydown(event: KeyboardEvent) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      moveHighlight(event.key === "ArrowDown" ? 1 : -1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (highlightedIndex.value >= 0) selectOption(props.options[highlightedIndex.value]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeMenu();
      trigger.value?.focus();
    } else if (event.key === "Tab") closeMenu();
  }

  watch(() => props.modelValue, () => {
    if (open.value) highlightedIndex.value = selectedIndex.value;
  });
  watch(() => props.options, () => {
    if (open.value) void syncMenuPosition();
  }, { deep: true });
  onBeforeUnmount(unbindListeners);

  return {
    root, trigger, menu, open, highlightedIndex, menuStyle, triggerId, menuId,
    selectedOption, optionKey, isSelected, closeMenu, toggleOpen, selectOption,
    handleTriggerKeydown, handleMenuKeydown,
  };
}

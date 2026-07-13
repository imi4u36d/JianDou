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
import type { AppSelectProps } from "./app-select";
import { useAppSelectInteraction } from "./useAppSelectInteraction";
import { IconChevronDown, IconCheck } from "@/components/icons";

const props = withDefaults(defineProps<AppSelectProps>(), {
  placeholder: "请选择",
  disabled: false,
  compact: false,
  variant: "field",
  prefix: "",
});
const emit = defineEmits<{
  (event: "update:modelValue", value: unknown): void;
}>();

const {
  root,
  trigger,
  menu,
  open,
  highlightedIndex,
  menuStyle,
  triggerId,
  menuId,
  selectedOption,
  optionKey,
  isSelected,
  closeMenu,
  toggleOpen,
  selectOption,
  handleTriggerKeydown,
  handleMenuKeydown,
} = useAppSelectInteraction(props, (value) => emit("update:modelValue", value));
</script>

<style scoped src="./app-select.css"></style>

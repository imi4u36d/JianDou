<template>
  <component
    :is="tag"
    class="jd-button"
    :class="[
      `jd-button--${variant}`,
      `jd-button--${size}`,
      {
        'jd-button--icon-only': iconOnly,
        'jd-button--loading': loading,
      },
    ]"
    :disabled="disabled || loading"
    :type="tag === 'button' ? type : undefined"
    v-bind="linkAttrs"
  >
    <span v-if="loading" class="jd-button__spinner">
      <IconLoading size="sm" />
    </span>
    <slot v-else name="icon-left" />
    <span v-if="!iconOnly" class="jd-button__label">
      <slot />
    </span>
    <slot v-if="!loading" name="icon-right" />
  </component>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { IconLoading } from "../icons";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "warning" | "accent";
type ButtonSize = "xs" | "sm" | "md" | "lg";

const props = withDefaults(
  defineProps<{
    variant?: ButtonVariant;
    size?: ButtonSize;
    iconOnly?: boolean;
    loading?: boolean;
    disabled?: boolean;
    tag?: "button" | "a" | typeof RouterLink;
    type?: "button" | "submit" | "reset";
    href?: string;
    to?: string;
  }>(),
  {
    variant: "secondary",
    size: "md",
    iconOnly: false,
    loading: false,
    disabled: false,
    tag: "button",
    type: "button",
    href: "",
    to: "",
  },
);

const linkAttrs = computed(() => {
  if (props.tag === "a") return { href: props.href };
  if (props.tag === RouterLink) return { to: props.to };
  return {};
});
</script>

<style scoped>
.jd-button__spinner {
  display: inline-flex;
  align-items: center;
}

.jd-button__label {
  display: inline-flex;
  align-items: center;
}
</style>

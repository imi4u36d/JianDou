<template>
  <AppButton
    :variant="variant"
    :size="size"
    icon-only
    :disabled="disabled"
    :loading="loading"
    :aria-label="ariaLabel"
  >
    <template #icon-left>
      <AppIcon :name="icon" :size="iconSize" />
    </template>
  </AppButton>
</template>

<script setup lang="ts">
import { computed } from "vue";
import AppButton from "./AppButton.vue";
import { AppIcon } from "../icons";
import type { IconName, IconSize } from "../icons";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "warning" | "accent";
type ButtonSize = "xs" | "sm" | "md" | "lg";

const props = withDefaults(
  defineProps<{
    icon: IconName;
    variant?: ButtonVariant;
    size?: ButtonSize;
    disabled?: boolean;
    loading?: boolean;
    ariaLabel?: string;
  }>(),
  {
    variant: "ghost",
    size: "md",
    disabled: false,
    loading: false,
    ariaLabel: "",
  },
);

const iconSizeMap: Record<ButtonSize, IconSize> = {
  xs: "xs",
  sm: "sm",
  md: "md",
  lg: "lg",
};

const iconSize = computed(() => iconSizeMap[props.size]);
</script>

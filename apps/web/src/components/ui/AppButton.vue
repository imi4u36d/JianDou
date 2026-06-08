<template>
  <component
    :is="tag"
    class="app-btn"
    :class="[
      `app-btn--${variant}`,
      `app-btn--${size}`,
      {
        'app-btn--icon-only': iconOnly,
        'app-btn--loading': loading,
      },
    ]"
    :disabled="disabled || loading"
    :type="tag === 'button' ? type : undefined"
    v-bind="linkAttrs"
  >
    <span v-if="loading" class="app-btn__spinner">
      <IconLoading size="sm" />
    </span>
    <slot v-else name="icon-left" />
    <span v-if="!iconOnly" class="app-btn__label">
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
  },
);

const linkAttrs = computed(() => {
  if (props.tag === "a") return { href: props.href };
  if (props.tag === RouterLink) return { to: props.to };
  return {};
});
</script>

<style scoped>
.app-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 14px;
  cursor: pointer;
  font-weight: 700;
  font-family: inherit;
  white-space: nowrap;
  user-select: none;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease,
    background 180ms ease,
    color 180ms ease;
}

/* ── Sizes ── */
.app-btn--xs {
  min-height: 28px;
  padding: 0 8px;
  font-size: 12px;
  border-radius: 8px;
  gap: 0.35rem;
}

.app-btn--sm {
  min-height: 34px;
  padding: 0 14px;
  font-size: 13px;
  border-radius: 10px;
  gap: 0.4rem;
}

.app-btn--md {
  min-height: 44px;
  padding: 0 16px;
  font-size: 14px;
  border-radius: 14px;
}

.app-btn--lg {
  min-height: 52px;
  padding: 0 24px;
  font-size: 16px;
  border-radius: 16px;
}

/* ── Icon-only sizes ── */
.app-btn--icon-only.app-btn--xs {
  width: 28px;
  padding: 0;
}

.app-btn--icon-only.app-btn--sm {
  width: 34px;
  padding: 0;
}

.app-btn--icon-only.app-btn--md {
  width: 44px;
  padding: 0;
}

.app-btn--icon-only.app-btn--lg {
  width: 52px;
  padding: 0;
}

/* ── Variants ── */
.app-btn--primary {
  border-color: transparent;
  background: var(--bg-accent);
  color: #fff;
  box-shadow: 0 12px 28px rgba(124, 58, 237, 0.22);
}

.app-btn--secondary {
  background: #fff;
  color: var(--text-strong);
  border-color: rgba(15, 20, 25, 0.09);
}

.app-btn--ghost {
  background: #f3f6f8;
  color: var(--text-body);
  border-color: transparent;
}

.app-btn--danger {
  background: rgba(229, 72, 101, 0.1);
  border-color: rgba(229, 72, 101, 0.24);
  color: #c5334e;
}

.app-btn--warning {
  background: rgba(255, 186, 73, 0.14);
  border-color: rgba(217, 137, 0, 0.22);
  color: #9a6100;
}

.app-btn--accent {
  border-color: transparent;
  background: linear-gradient(135deg, #43c6a7 0%, #2f8ead 100%);
  color: #fff;
  box-shadow: 0 12px 28px rgba(47, 142, 173, 0.22);
}

/* ── Hover ── */
.app-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-soft);
}

.app-btn--primary:hover:not(:disabled) {
  box-shadow: 0 14px 32px rgba(124, 58, 237, 0.3);
}

.app-btn--accent:hover:not(:disabled) {
  box-shadow: 0 14px 32px rgba(47, 142, 173, 0.3);
}

/* ── Active ── */
.app-btn:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
  box-shadow: var(--shadow-pressed);
}

/* ── Focus ── */
.app-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.3);
}

/* ── Disabled ── */
.app-btn:disabled {
  opacity: 0.52;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* ── Loading ── */
.app-btn--loading {
  position: relative;
}

.app-btn__spinner {
  display: inline-flex;
  align-items: center;
}

/* ── Label ── */
.app-btn__label {
  display: inline-flex;
  align-items: center;
}
</style>

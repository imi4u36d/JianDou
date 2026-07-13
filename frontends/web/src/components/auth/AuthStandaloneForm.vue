<template>
  <section class="auth-screen">
    <AuthCarouselBackground />
    <div class="auth-screen__panel">
      <div class="auth-screen__brand">
        <img alt="煎豆" class="auth-screen__logo" src="/brand/jiandou-mark.svg" />
        <div><h1>{{ title }}</h1><p>{{ subtitle }}</p></div>
      </div>
      <form class="auth-form" @submit.prevent="$emit('submit')">
        <label v-if="showCode" class="auth-form__field">
          <span class="auth-form__field-label">邀请码</span>
          <input :value="code" autocomplete="off" placeholder="邀请码" type="text" @input="$emit('update:code', inputValue($event))" />
        </label>
        <label class="auth-form__field">
          <span class="auth-form__field-label">用户名</span>
          <input :value="username" autocomplete="username" placeholder="用户名" type="text" @input="$emit('update:username', inputValue($event))" />
        </label>
        <label class="auth-form__field">
          <span class="auth-form__field-label">密码</span>
          <div class="auth-form__password-wrap">
            <input
              :value="password"
              :type="showPassword ? 'text' : 'password'"
              :autocomplete="passwordAutocomplete"
              placeholder="密码"
              @input="$emit('update:password', inputValue($event))"
            />
            <button
              :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              :title="showPassword ? '隐藏密码' : '显示密码'"
              class="auth-form__password-toggle"
              type="button"
              @click="showPassword = !showPassword"
            >
              <IconEyeOff v-if="showPassword" size="sm" />
              <IconEye v-else size="sm" />
            </button>
          </div>
        </label>
        <button :disabled="submitting" class="auth-form__submit" type="submit">
          <IconLoading v-if="submitting" size="sm" />
          <span>{{ submitting ? submittingLabel : submitLabel }}</span>
        </button>
        <p class="auth-form__footer"><RouterLink :to="footerTo">{{ footerLabel }}</RouterLink></p>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { RouteLocationRaw } from "vue-router";
import AuthCarouselBackground from "./AuthCarouselBackground.vue";
import { IconEye, IconEyeOff, IconLoading } from "@/components/icons";

withDefaults(defineProps<{
  title: string;
  subtitle: string;
  username: string;
  password: string;
  code?: string;
  showCode?: boolean;
  submitting: boolean;
  submitLabel: string;
  submittingLabel: string;
  footerLabel: string;
  footerTo: RouteLocationRaw;
  passwordAutocomplete?: string;
}>(), {
  code: "",
  showCode: false,
  passwordAutocomplete: "current-password",
});

defineEmits<{
  submit: [];
  "update:code": [value: string];
  "update:username": [value: string];
  "update:password": [value: string];
}>();

const showPassword = ref(false);
const inputValue = (event: Event) => (event.target as HTMLInputElement).value;
</script>

<style scoped src="./auth-standalone-form.css"></style>
